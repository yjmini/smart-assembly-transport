import time
from dataclasses import replace

import pytest

from sem1_pjt_ws.src.dobot_controller.dobot_controller.realsense_pick_place import (
    CameraPoint,
    ObjectPickPlaceCoordinator,
    PickPlaceConfig,
    TwoObjectPickPlaceNode,
    build_conveyor_command,
    build_two_object_pick_place_plan,
    sort_action_for_quality,
)


def test_two_object_pick_place_plan_places_each_object_then_moves_conveyor():
    config = PickPlaceConfig.reference_from_project_pill()
    plan = build_two_object_pick_place_plan(
        [CameraPoint(x=10.0, y=20.0, z=300.0), CameraPoint(x=30.0, y=40.0, z=310.0)],
        config,
    )

    names = [step.name for step in plan.steps]

    assert names == [
        "object_1_move_above_pick",
        "object_1_descend_to_pick",
        "object_1_suction_on",
        "object_1_lift_after_pick",
        "object_1_move_above_conveyor",
        "object_1_descend_to_conveyor",
        "object_1_release_on_conveyor",
        "object_1_retreat_from_conveyor",
        "object_2_move_above_pick",
        "object_2_descend_to_pick",
        "object_2_suction_on",
        "object_2_lift_after_pick",
        "object_2_move_above_conveyor",
        "object_2_descend_to_conveyor",
        "object_2_release_on_conveyor",
        "object_2_retreat_from_conveyor",
        "sort_conveyor_left_after_quality_pass",
    ]
    assert [step.kind for step in plan.steps].count("dobot_pose") == 12
    assert [step.kind for step in plan.steps].count("suction") == 4
    assert plan.steps[5].pose == config.conveyor_pose_for_index(1)
    assert plan.steps[13].pose == config.conveyor_pose_for_index(2)
    first_place_pose = plan.steps[5].pose
    second_place_pose = plan.steps[13].pose
    assert first_place_pose is not None
    assert second_place_pose is not None
    assert second_place_pose.x == pytest.approx(first_place_pose.x)
    assert second_place_pose.y == pytest.approx(first_place_pose.y)
    assert plan.steps[6].suction_enabled is False
    assert plan.steps[7].pose is not None
    assert plan.steps[7].pose.z == config.conveyor_retreat_z_mm
    assert plan.steps[-1].kind == "conveyor"
    assert plan.steps[-1].conveyor_action == "sort-left"


def test_project_pill_reference_transform_maps_camera_point_to_robot_xy():
    config = PickPlaceConfig.reference_from_project_pill()

    x, y = config.camera_to_robot_xy(CameraPoint(x=0.0, y=0.0, z=300.0))

    assert x == pytest.approx(253.013, abs=0.01)
    assert y == pytest.approx(-7.593, abs=0.01)


def test_reference_pick_and_place_z_values_are_lowered_for_hardware_smoke_test():
    config = PickPlaceConfig.reference_from_project_pill()

    assert config.pick_z_mm == pytest.approx(-52.0)
    assert config.conveyor_pose_mm.z == pytest.approx(6.8)


def test_car_upper_uses_same_fixed_xy_and_higher_z_for_stack():
    config = PickPlaceConfig.reference_from_project_pill()

    lower_pose = config.conveyor_pose_for_index(1)
    upper_pose = config.conveyor_pose_for_index(2)

    assert lower_pose.z == pytest.approx(6.8)
    assert upper_pose.z == pytest.approx(14.8)
    assert upper_pose.x == pytest.approx(lower_pose.x)
    assert upper_pose.y == pytest.approx(lower_pose.y)
    assert config.object_place_spacing_y_mm == pytest.approx(0.0)


def test_pick_place_plan_requires_exactly_two_objects():
    config = PickPlaceConfig.reference_from_project_pill()

    with pytest.raises(ValueError, match="exactly 2"):
        build_two_object_pick_place_plan([CameraPoint(0, 0, 300)], config)


def test_target_callback_work_is_dispatched_off_executor_thread():
    config = PickPlaceConfig.reference_from_project_pill()
    statuses: list[str] = []
    target_colors: list[str] = []
    executed_batches: list[list[str]] = []

    def execute_steps(steps):
        executed_batches.append([step.name for step in steps])
        time.sleep(0.05)

    coordinator = ObjectPickPlaceCoordinator(
        config,
        execute_steps,
        statuses.append,
        set_target_color=target_colors.append,
        target_colors=("car_lower", "car_upper"),
    )

    started = time.monotonic()
    accepted = coordinator.accept_target(CameraPoint(20.0, -109.0, 384.0))
    elapsed = time.monotonic() - started

    assert accepted is True
    assert elapsed < 0.03
    assert coordinator.accept_target(CameraPoint(21.0, -110.0, 384.0)) is False

    coordinator.wait_for_idle(timeout_sec=1.0)

    assert coordinator.completed_count == 1
    assert statuses == ["COMPLETED_OBJECT_1_WAITING_FOR_OBJECT_2"]
    assert target_colors == ["car_lower", "car_upper"]
    assert executed_batches[0][0] == "object_1_move_above_pick"


def test_second_object_starts_conveyor_after_color_switch():
    config = replace(PickPlaceConfig.reference_from_project_pill(), color_switch_settle_sec=0.0)
    statuses: list[str] = []
    target_colors: list[str] = []
    executed_batches: list[list[str]] = []

    def execute_steps(steps):
        executed_batches.append([step.name for step in steps])

    coordinator = ObjectPickPlaceCoordinator(
        config,
        execute_steps,
        statuses.append,
        set_target_color=target_colors.append,
        target_colors=("car_lower", "car_upper"),
    )

    assert coordinator.accept_target(CameraPoint(20.0, -109.0, 384.0)) is True
    coordinator.wait_for_idle(timeout_sec=1.0)
    assert coordinator.accept_target(CameraPoint(-30.0, 42.0, 410.0)) is True
    coordinator.wait_for_idle(timeout_sec=1.0)

    # After the second object the cycle finishes: Dobot returns home, the
    # conveyor sorts, then the coordinator resets so the next cycle can begin.
    assert coordinator.cycle_count == 1
    assert coordinator.completed_count == 0
    assert statuses == [
        "COMPLETED_OBJECT_1_WAITING_FOR_OBJECT_2",
        "CONVEYOR_MOVING",
        "QC_CHECK",
        "SORTING_NORMAL_run=fixed",
        "SORTING_COMPLETE",
        "COMPLETED_TWO_OBJECT_PICK_PLACE",
    ]
    assert target_colors == ["car_lower", "car_upper", "car_lower"]
    assert executed_batches[-2] == ["return_to_home"]
    assert executed_batches[-1] == ["sort_conveyor_left_after_quality_pass"]


def test_max_cycles_stops_after_configured_cycles():
    config = replace(
        PickPlaceConfig.reference_from_project_pill(),
        color_switch_settle_sec=0.0,
        max_cycles=1,
    )
    statuses: list[str] = []

    coordinator = ObjectPickPlaceCoordinator(
        config,
        lambda steps: None,
        statuses.append,
        set_target_color=lambda _color: None,
        target_colors=("car_lower", "car_upper"),
    )

    # Complete one full cycle (two objects).
    assert coordinator.accept_target(CameraPoint(20.0, -109.0, 384.0)) is True
    coordinator.wait_for_idle(timeout_sec=1.0)
    assert coordinator.accept_target(CameraPoint(-30.0, 42.0, 410.0)) is True
    coordinator.wait_for_idle(timeout_sec=1.0)

    assert coordinator.cycle_count == 1
    assert any(s.startswith("ALL_CYCLES_DONE") for s in statuses)
    # Further targets are rejected once the cycle cap is reached.
    assert coordinator.accept_target(CameraPoint(10.0, -100.0, 390.0)) is False


def test_quality_result_maps_normal_left_and_abnormal_right():
    assert sort_action_for_quality("normal") == ("sort-left", "sort_conveyor_left_after_quality_pass")
    assert sort_action_for_quality("pass") == ("sort-left", "sort_conveyor_left_after_quality_pass")
    assert sort_action_for_quality("abnormal") == ("sort-right", "sort_conveyor_right_after_quality_fail")
    assert sort_action_for_quality("fail") == ("sort-right", "sort_conveyor_right_after_quality_fail")


def test_conveyor_command_uses_sort_action_and_longer_step_count():
    command = build_conveyor_command(
        action="sort-right",
        steps=3200,
        step_delay_sec=0.0001,
        host="192.168.110.142",
        user="ssafy",
    )

    assert "CONVEYOR_STEPS=3200" in command
    assert "conveyor_control.py sort-right" in command


def test_conveyor_failure_stops_false_quality_progress(monkeypatch):
    import subprocess

    from sem1_pjt_ws.src.dobot_controller.dobot_controller import realsense_pick_place as module

    class FakeCompletedProcess:
        returncode = 23
        stdout = ""
        stderr = "ssh failed"

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: FakeCompletedProcess())

    node = object.__new__(module.TwoObjectPickPlaceNode)
    node.config = module.PickPlaceConfig.reference_from_project_pill()
    node.conveyor_command_template = ""
    node.node = type("FakeNode", (), {"get_logger": lambda self: type("Logger", (), {"info": lambda *a, **k: None, "error": lambda *a, **k: None})()})()

    with pytest.raises(RuntimeError, match="Conveyor command failed"):
        node.run_conveyor_step(module.PickPlaceStep("sort_conveyor_left_after_quality_pass", "conveyor", conveyor_action="sort-left"))


def test_node_startup_publishes_order_received_then_object_detected_before_first_pick():
    statuses: list[str] = []
    node = object.__new__(TwoObjectPickPlaceNode)
    node.publish_status = statuses.append

    node.publish_startup_order_status()
    node.publish_object_detected_status(1, CameraPoint(20.0, -109.0, 384.0))

    assert statuses == [
        "ORDER_RECEIVED",
        "OBJECT_DETECTED_index=1",
    ]
