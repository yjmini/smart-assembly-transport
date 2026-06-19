import pytest

from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.fsm import (
    EmergencyStopRequired,
    FactoryFSM,
    MissionState,
)
from sem1_pjt_ws.src.dobot_controller.dobot_controller.calibration import PixelToRobotCalibrator
from sem1_pjt_ws.src.dobot_controller.dobot_controller.sequence import AssemblyPoseConfig, build_two_part_assembly_plan
from sem1_pjt_ws.src.vision_detector.vision_detector.color_detector import detect_colored_objects
from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.events import (
    EventType,
    make_order,
    make_state_event,
)


def test_factory_fsm_runs_nominal_mission_and_records_events():
    fsm = FactoryFSM()
    order = make_order(command="assemble and deliver to A", destination="A", parts=["base", "top"])

    states = [fsm.handle_event(EventType.ORDER_CREATED, order).state]
    for event in [
        EventType.CONVEYOR_STARTED,
        EventType.BASE_IN_POSITION,
        EventType.CONVEYOR_STOPPED,
        EventType.ASSEMBLY_STAGE_1_DONE,
        EventType.ASSEMBLY_STAGE_2_DONE,
        EventType.QC_PASSED,
        EventType.LOADED_TO_TURTLEBOT,
        EventType.DELIVERY_ARRIVED,
    ]:
        states.append(fsm.handle_event(event).state)

    assert states == [
        MissionState.ORDER_RECEIVED,
        MissionState.CONVEYOR_MOVING,
        MissionState.BASE_DETECTED_STOPPING,
        MissionState.ASSEMBLY_STAGE_1,
        MissionState.ASSEMBLY_STAGE_2,
        MissionState.QC_CHECK,
        MissionState.LOADING_TO_TURTLEBOT,
        MissionState.DELIVERY_NAVIGATING,
        MissionState.DELIVERED,
    ]
    assert fsm.current_order.destination == "A"
    assert fsm.history[-1].event_type == EventType.DELIVERY_ARRIVED


def test_factory_fsm_interrupts_on_hand_detection_and_requires_admin_unlock():
    fsm = FactoryFSM()
    fsm.handle_event(EventType.ORDER_CREATED, make_order("start", "B", ["base"]))
    fsm.handle_event(EventType.CONVEYOR_STARTED)

    state = fsm.handle_event(EventType.HAND_DETECTED, {"source": "vision"})

    assert state.state == MissionState.WAIT_ADMIN_UNLOCK
    assert fsm.previous_active_state == MissionState.CONVEYOR_MOVING
    with pytest.raises(EmergencyStopRequired):
        fsm.handle_event(EventType.BASE_IN_POSITION)

    resumed = fsm.handle_event(EventType.ADMIN_UNLOCKED, {"admin": "operator"})
    assert resumed.state == MissionState.CONVEYOR_MOVING


def test_pixel_to_robot_calibrator_matches_reference_homography():
    calibrator = PixelToRobotCalibrator.reference_default()

    x, y = calibrator.pixel_to_robot(320, 240)

    assert x == pytest.approx(83.55, abs=0.1)
    assert y == pytest.approx(-113.62, abs=0.1)


def test_two_part_assembly_plan_documents_placeholder_hardware_values():
    config = AssemblyPoseConfig.reference_default()
    plan = build_two_part_assembly_plan(config)

    names = [step.name for step in plan.steps]
    assert names == [
        "move_above_part_a",
        "pick_part_a",
        "lift_part_a",
        "place_part_a_on_conveyor",
        "move_above_part_b",
        "pick_part_b",
        "lift_part_b",
        "stack_part_b_on_part_a",
        "retreat_safe_home",
    ]
    assert plan.placeholder_fields == [
        "safe_z_mm",
        "pick_z_mm",
        "part_a_pixel",
        "part_b_pixel",
        "conveyor_place_pose_mm",
        "stack_offset_mm",
    ]


def test_color_detector_finds_largest_yellow_blob_without_ros_dependencies():
    import cv2
    import numpy as np

    image = np.zeros((120, 160, 3), dtype=np.uint8)
    cv2.rectangle(image, (40, 30), (90, 80), (0, 255, 255), -1)

    detections = detect_colored_objects(image, color="yellow", min_area=500)

    assert len(detections) == 1
    det = detections[0]
    assert det.label == "yellow_part"
    assert det.center == pytest.approx((65, 55), abs=1)
    assert det.area > 2000


def test_state_event_schema_is_websocket_friendly():
    event = make_state_event(
        state=MissionState.ASSEMBLY_STAGE_1,
        message="stage 1 started",
        payload={"order_id": "order-1"},
    )

    assert event["type"] == "factory.state"
    assert event["state"] == "ASSEMBLY_STAGE_1"
    assert event["message"] == "stage 1 started"
    assert event["payload"]["order_id"] == "order-1"
    assert "timestamp" in event
