"""Mission FSM for the mock-first smart factory flow."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

try:  # colcon-installed package import
    from hri_interfaces.events import EventType, WorkOrder, serialize_order
except ImportError:  # repository-root test/import path
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.events import EventType, WorkOrder, serialize_order


class MissionState(Enum):
    IDLE = auto()
    ORDER_RECEIVED = auto()
    CONVEYOR_MOVING = auto()
    BASE_DETECTED_STOPPING = auto()
    ASSEMBLY_STAGE_1 = auto()
    ASSEMBLY_STAGE_2 = auto()
    QC_CHECK = auto()
    LOADING_TO_TURTLEBOT = auto()
    DELIVERY_NAVIGATING = auto()
    DELIVERED = auto()
    EMERGENCY_STOP = auto()
    WAIT_ADMIN_UNLOCK = auto()


class EmergencyStopRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class TransitionRecord:
    event_type: EventType
    from_state: MissionState
    to_state: MissionState
    payload: dict[str, Any]


@dataclass(frozen=True)
class FSMResult:
    state: MissionState
    command: str | None = None
    payload: dict[str, Any] | None = None


class FactoryFSM:
    """Small deterministic FSM that can be driven by ROS callbacks or tests."""

    emergency_events = {EventType.HAND_DETECTED, EventType.DASHBOARD_STOP, EventType.CRITICAL_ERROR}

    def __init__(self) -> None:
        self.state = MissionState.IDLE
        self.current_order: WorkOrder | None = None
        self.previous_active_state: MissionState | None = None
        self.history: list[TransitionRecord] = []

    def handle_event(self, event_type: EventType, payload: Any | None = None) -> FSMResult:
        payload_dict = self._payload_to_dict(payload)
        if event_type in self.emergency_events:
            return self._emergency(event_type, payload_dict)
        if self.state == MissionState.WAIT_ADMIN_UNLOCK and event_type != EventType.ADMIN_UNLOCKED:
            raise EmergencyStopRequired("Admin unlock is required before mission events can resume")

        prev = self.state
        command: str | None = None
        if event_type == EventType.ORDER_CREATED and self.state in {MissionState.IDLE, MissionState.DELIVERED}:
            if isinstance(payload, WorkOrder):
                self.current_order = payload
            else:
                self.current_order = WorkOrder(**payload_dict)
            self.state = MissionState.ORDER_RECEIVED
            command = "conveyor.start"
        elif event_type == EventType.CONVEYOR_STARTED and self.state == MissionState.ORDER_RECEIVED:
            self.state = MissionState.CONVEYOR_MOVING
        elif event_type == EventType.BASE_IN_POSITION and self.state == MissionState.CONVEYOR_MOVING:
            self.state = MissionState.BASE_DETECTED_STOPPING
            command = "conveyor.stop"
        elif event_type == EventType.CONVEYOR_STOPPED and self.state == MissionState.BASE_DETECTED_STOPPING:
            self.state = MissionState.ASSEMBLY_STAGE_1
            command = "dobot.assembly_stage_1"
        elif event_type == EventType.ASSEMBLY_STAGE_1_DONE and self.state == MissionState.ASSEMBLY_STAGE_1:
            self.state = MissionState.ASSEMBLY_STAGE_2
            command = "dobot.assembly_stage_2"
        elif event_type == EventType.ASSEMBLY_STAGE_2_DONE and self.state == MissionState.ASSEMBLY_STAGE_2:
            self.state = MissionState.QC_CHECK
            command = "vision.qc_check"
        elif event_type == EventType.QC_PASSED and self.state == MissionState.QC_CHECK:
            self.state = MissionState.LOADING_TO_TURTLEBOT
            command = "dobot.load_to_turtlebot"
        elif event_type == EventType.LOADED_TO_TURTLEBOT and self.state == MissionState.LOADING_TO_TURTLEBOT:
            self.state = MissionState.DELIVERY_NAVIGATING
            command = "turtlebot.navigate"
        elif event_type == EventType.DELIVERY_ARRIVED and self.state == MissionState.DELIVERY_NAVIGATING:
            self.state = MissionState.DELIVERED
            command = "tts.say_complete"
        elif event_type == EventType.ADMIN_UNLOCKED and self.state == MissionState.WAIT_ADMIN_UNLOCK:
            self.state = self.previous_active_state or MissionState.IDLE
            command = "factory.resume"
        else:
            raise ValueError(f"Invalid transition: {self.state.name} + {event_type.value}")

        self.history.append(TransitionRecord(event_type, prev, self.state, payload_dict))
        return FSMResult(self.state, command=command, payload=payload_dict)

    def _emergency(self, event_type: EventType, payload: dict[str, Any]) -> FSMResult:
        prev = self.state
        if self.state not in {MissionState.IDLE, MissionState.DELIVERED, MissionState.WAIT_ADMIN_UNLOCK}:
            self.previous_active_state = self.state
        self.state = MissionState.WAIT_ADMIN_UNLOCK
        self.history.append(TransitionRecord(event_type, prev, self.state, payload))
        return FSMResult(self.state, command="factory.emergency_stop", payload=payload)

    @staticmethod
    def _payload_to_dict(payload: Any | None) -> dict[str, Any]:
        if payload is None:
            return {}
        if isinstance(payload, WorkOrder):
            return serialize_order(payload)
        if isinstance(payload, dict):
            return dict(payload)
        return {"value": payload}
