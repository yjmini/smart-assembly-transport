"""Run the end-to-end mock mission without ROS/hardware."""
from __future__ import annotations

import json

try:  # colcon-installed package import
    from hri_interfaces.events import EventType, make_order, make_state_event
    from mission_orchestrator.fsm import FactoryFSM
except ImportError:  # repository-root test/import path
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.events import EventType, make_order, make_state_event
    from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.fsm import FactoryFSM


def run_mock_mission(destination: str = "A") -> list[dict]:
    fsm = FactoryFSM()
    order = make_order("assemble and deliver", destination, ["base", "top"])
    events = [(EventType.ORDER_CREATED, order)] + [(event, None) for event in [
        EventType.CONVEYOR_STARTED,
        EventType.BASE_IN_POSITION,
        EventType.CONVEYOR_STOPPED,
        EventType.ASSEMBLY_STAGE_1_DONE,
        EventType.ASSEMBLY_STAGE_2_DONE,
        EventType.QC_PASSED,
        EventType.LOADED_TO_TURTLEBOT,
        EventType.DELIVERY_ARRIVED,
    ]]
    output = []
    for event, payload in events:
        result = fsm.handle_event(event, payload)
        output.append(make_state_event(result.state, f"handled {event.value}", {"command": result.command, **(result.payload or {})}))
    return output


def main() -> None:
    print(json.dumps(run_mock_mission(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
