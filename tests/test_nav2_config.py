from pathlib import Path

import yaml


NAV2_CONFIG = Path(__file__).resolve().parents[1] / "config" / "nav2" / "pjt_waffle_pi.yaml"


def test_real_nav2_config_uses_wall_clock_time_for_all_nodes():
    data = yaml.safe_load(NAV2_CONFIG.read_text(encoding="utf-8"))

    assert data["amcl"]["ros__parameters"]["use_sim_time"] is False
    assert data["global_costmap"]["global_costmap"]["ros__parameters"]["use_sim_time"] is False
    assert data["recoveries_server"]["ros__parameters"]["use_sim_time"] is False


def test_nav2_inflation_is_tightened_for_ab_route():
    data = yaml.safe_load(NAV2_CONFIG.read_text(encoding="utf-8"))

    local_inflation = data["local_costmap"]["local_costmap"]["ros__parameters"]["inflation_layer"]
    global_inflation = data["global_costmap"]["global_costmap"]["ros__parameters"]["inflation_layer"]

    assert local_inflation["inflation_radius"] == 0.20
    assert global_inflation["inflation_radius"] == 0.20
    assert local_inflation["cost_scaling_factor"] == 5.0
    assert global_inflation["cost_scaling_factor"] == 5.0


def test_nav2_amcl_updates_more_frequently_and_reduces_random_pose_jumps():
    data = yaml.safe_load(NAV2_CONFIG.read_text(encoding="utf-8"))
    amcl = data["amcl"]["ros__parameters"]

    assert amcl["min_particles"] == 1000
    assert amcl["max_particles"] == 3000
    assert amcl["update_min_d"] == 0.05
    assert amcl["update_min_a"] == 0.1
    assert amcl["z_hit"] == 0.7
    assert amcl["z_rand"] == 0.2


def test_nav2_goal_checker_is_relaxed_to_prevent_final_pose_dithering():
    data = yaml.safe_load(NAV2_CONFIG.read_text(encoding="utf-8"))
    controller = data["controller_server"]["ros__parameters"]
    goal_checker = controller["general_goal_checker"]
    follow_path = controller["FollowPath"]

    assert goal_checker["xy_goal_tolerance"] == 0.20
    assert goal_checker["yaw_goal_tolerance"] == 0.50
    assert follow_path["xy_goal_tolerance"] == 0.20
    assert follow_path["RotateToGoal.scale"] == 16.0
    assert follow_path["RotateToGoal.slowing_factor"] == 3.0
