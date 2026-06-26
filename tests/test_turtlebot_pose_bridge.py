from pathlib import Path


BRIDGE = Path(__file__).resolve().parents[1] / "scripts" / "turtlebot_pose_ws_bridge.py"
STARTER = Path(__file__).resolve().parents[1] / "scripts" / "start_turtlebot_pose_bridge.sh"


def test_turtlebot_pose_bridge_forwards_amcl_pose_to_dashboard_websocket():
    script = BRIDGE.read_text(encoding="utf-8")

    required_snippets = [
        "PoseWithCovarianceStamped",
        "Odometry",
        "quaternion_to_yaw",
        "turtlebot.pose",
        "websockets.connect",
        "ws://127.0.0.1:8765",
        "실시간 pose 수신",
        "/amcl_pose",
    ]
    for snippet in required_snippets:
        assert snippet in script


def test_turtlebot_pose_bridge_starter_uses_ros_domain_34_and_system_python():
    starter = STARTER.read_text(encoding="utf-8")

    required_snippets = [
        "ROS_DOMAIN_ID:-34",
        "source \"$ROS_SETUP\"",
        "sem1_pjt_ws/install/setup.bash",
        "exec /usr/bin/python3 scripts/turtlebot_pose_ws_bridge.py",
        "TURTLEBOT_POSE_TOPIC:-/amcl_pose",
        "DASHBOARD_WS_URL:-ws://127.0.0.1:8765",
    ]
    for snippet in required_snippets:
        assert snippet in starter


def test_turtlebot_pose_bridge_spins_ros_in_background_thread_not_websocket_loop():
    script = BRIDGE.read_text(encoding="utf-8")

    assert "threading.Thread" in script
    assert "rclpy.spin(bridge.node)" in script
    assert "rclpy.spin_once(bridge.node" not in script
