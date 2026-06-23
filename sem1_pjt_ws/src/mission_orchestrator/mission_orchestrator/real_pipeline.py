"""Hardware-oriented pipeline service.

`execute=False` is safe on a development PC and returns the exact SSH/ROS
commands that would run.  `execute=True` attempts to reach real hardware.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

try:
    from hri_interfaces.events import EventType, make_order, make_state_event
    from hri_interfaces.hardware_config import HardwareConfig, DEFAULT_CONFIG_PATH
    from conveyor_controller.real_conveyor import RealConveyorController
    from turtlebot_delivery.real_turtlebot import RealTurtleBotDelivery
    from dobot_controller.real_dobot import RealDobotController, build_real_dobot_execution_plan
    from mission_orchestrator.fsm import FactoryFSM
except ImportError:
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.events import EventType, make_order, make_state_event
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import HardwareConfig, DEFAULT_CONFIG_PATH
    from sem1_pjt_ws.src.conveyor_controller.conveyor_controller.real_conveyor import RealConveyorController
    from sem1_pjt_ws.src.turtlebot_delivery.turtlebot_delivery.real_turtlebot import RealTurtleBotDelivery
    from sem1_pjt_ws.src.dobot_controller.dobot_controller.real_dobot import RealDobotController, build_real_dobot_execution_plan
    from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.fsm import FactoryFSM


class RealHardwarePipeline:
    def __init__(self, config: HardwareConfig | None = None, *, execute: bool = False) -> None:
        self.config = config or HardwareConfig.load(DEFAULT_CONFIG_PATH)
        self.execute = execute
        self.fsm = FactoryFSM()
        self.conveyor = RealConveyorController(self.config.conveyor, execute=execute)
        self.turtlebot = RealTurtleBotDelivery(self.config.turtlebot, execute=execute)
        self.dobot = RealDobotController(self.config.dobot.ptp_action, self.config.dobot.motion_type, execute=execute)

    def status_snapshot(self) -> dict[str, Any]:
        return self.config.summary() | {"type": "hardware.status", "execute": self.execute}

    def pipeline_summary(self) -> dict[str, Any]:
        dobot = build_real_dobot_execution_plan(self.config.dobot.ptp_action, self.config.dobot.motion_type)
        return {
            "type": "hardware.pipeline",
            "execute": self.execute,
            "conveyor": self.config.summary()["conveyor"],
            "turtlebot": self.config.summary()["turtlebot"],
            "dobot": dobot.as_dashboard_payload(),
            "vision": self.config.summary()["vision"],
            "phases": self.demo_phases(),
        }

    @staticmethod
    def demo_phases() -> list[dict[str, str]]:
        """Presentation-grade checkpoints adapted from the reference project.

        The reference project is a medicine-delivery demo, so only its robust
        integration pattern is reused here: visible phases, explicit gates, and
        a return-home step after delivery.  The domain remains smart assembly.
        """
        return [
            {"id": "order", "label": "작업 오더 수신", "gate": "operator/stt order"},
            {"id": "conveyor_to_vision_gate", "label": "컨베이어 이동 및 정위치 감지", "gate": "vision.base_in_position"},
            {"id": "assembly", "label": "Dobot 2단계 자동 조립", "gate": "dobot stage results"},
            {"id": "quality_check", "label": "비전 기반 품질 확인", "gate": "vision.qc_passed"},
            {"id": "load_to_turtlebot", "label": "완성품 TurtleBot 적재", "gate": "dobot.loaded_to_turtlebot"},
            {"id": "delivery", "label": "목적지 무인 배송", "gate": "turtlebot.delivery_arrived"},
            {"id": "return_home", "label": "TurtleBot 시작 위치 복귀", "gate": "turtlebot.return_arrived", "source_reference": "project_pill_return_flow_adapted"},
        ]

    @staticmethod
    def _command_result(subsystem: str, action: str, result) -> dict[str, Any]:
        return {"type": "hardware.command_result", "subsystem": subsystem, "action": action, **asdict(result)}

    def run_order_plan(self, destination: str = "A") -> list[dict[str, Any]]:
        """Run the whole hardware command sequence.

        The sensing gates are explicit: when fully integrated, `BASE_IN_POSITION`
        and `QC_PASSED` should be triggered by the real vision node.  Until that
        callback wiring is running, this method performs the same transitions in
        order after issuing the corresponding hardware command so the full
        physical command chain can be smoke-tested.
        """
        order = make_order("real hardware order", destination, ["base", "top"])
        outputs: list[dict[str, Any]] = []

        def transition(event: EventType, payload: Any | None = None, message: str | None = None) -> None:
            result = self.fsm.handle_event(event, payload)
            outputs.append(make_state_event(result.state, message or f"handled {event.value}", {"command": result.command, **(result.payload or {})}))

        transition(EventType.ORDER_CREATED, order, "order accepted")
        outputs.append(self._command_result("conveyor", "start", self.conveyor.start()))
        transition(EventType.CONVEYOR_STARTED)
        transition(EventType.BASE_IN_POSITION, {"source": "vision_detector", "gate": "base_detected"})
        outputs.append(self._command_result("conveyor", "stop", self.conveyor.stop()))
        transition(EventType.CONVEYOR_STOPPED)

        dobot_plan = build_real_dobot_execution_plan(self.config.dobot.ptp_action, self.config.dobot.motion_type)
        half = max(1, len(dobot_plan.target_poses) // 2)
        for idx, pose in enumerate(dobot_plan.target_poses, 1):
            outputs.append(self._command_result("dobot", f"ptp_step_{idx}", self.dobot.run_pose(pose)))
            if idx == half:
                transition(EventType.ASSEMBLY_STAGE_1_DONE, {"step": idx})
        transition(EventType.ASSEMBLY_STAGE_2_DONE, {"steps": len(dobot_plan.target_poses)})
        transition(EventType.QC_PASSED, {"source": "vision_detector", "gate": "qc"})
        transition(EventType.LOADED_TO_TURTLEBOT, {"source": "dobot"})
        outputs.append(self._command_result("turtlebot", f"navigate_{destination}", self.turtlebot.navigate(destination)))
        transition(EventType.DELIVERY_ARRIVED, {"destination": destination, "source": "turtlebot"})
        outputs.append(
            self._command_result(
                "turtlebot",
                f"wait_{self.config.turtlebot.delivery_dwell_sec:g}s",
                self.turtlebot.wait_at_destination(self.config.turtlebot.delivery_dwell_sec),
            )
        )
        transition(EventType.RETURN_REQUESTED, {"destination": self.config.turtlebot.home_destination, "source": "mission_orchestrator"}, "return home requested")
        outputs.append(self._command_result("turtlebot", f"return_{self.config.turtlebot.home_destination}", self.turtlebot.return_home()))
        transition(EventType.RETURN_ARRIVED, {"destination": self.config.turtlebot.home_destination, "source": "turtlebot"}, "returned home")
        return outputs
