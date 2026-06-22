import pytest

from sem1_pjt_ws.src.dobot_controller.dobot_controller.realsense_pick_place import (
    CameraPoint,
    PickPlaceConfig,
    build_two_object_pick_place_plan,
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
        "object_1_move_to_conveyor",
        "object_1_release_on_conveyor",
        "object_1_retreat_from_conveyor",
        "object_2_move_above_pick",
        "object_2_descend_to_pick",
        "object_2_suction_on",
        "object_2_lift_after_pick",
        "object_2_move_to_conveyor",
        "object_2_release_on_conveyor",
        "object_2_retreat_from_conveyor",
        "start_conveyor_after_two_objects",
    ]
    assert [step.kind for step in plan.steps].count("dobot_pose") == 10
    assert [step.kind for step in plan.steps].count("suction") == 4
    assert plan.steps[-1].kind == "conveyor"
    assert plan.steps[-1].conveyor_action == "start"


def test_project_pill_reference_transform_maps_camera_point_to_robot_xy():
    config = PickPlaceConfig.reference_from_project_pill()

    x, y = config.camera_to_robot_xy(CameraPoint(x=0.0, y=0.0, z=300.0))

    assert x == pytest.approx(253.013, abs=0.01)
    assert y == pytest.approx(-7.593, abs=0.01)


def test_pick_place_plan_requires_exactly_two_objects():
    config = PickPlaceConfig.reference_from_project_pill()

    with pytest.raises(ValueError, match="exactly 2"):
        build_two_object_pick_place_plan([CameraPoint(0, 0, 300)], config)
