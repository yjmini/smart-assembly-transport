from pathlib import Path


BRIDGE = Path(__file__).resolve().parents[1] / "scripts" / "realsense_mjpeg_bridge.py"
STARTER = Path(__file__).resolve().parents[1] / "scripts" / "start_realsense_stream.sh"


def test_realsense_bridge_exposes_mjpeg_stream_endpoints():
    script = BRIDGE.read_text(encoding="utf-8")

    required_snippets = [
        "sensor_msgs.msg import Image",
        "qos_profile_sensor_data",
        "ThreadingHTTPServer",
        "multipart/x-mixed-replace; boundary=frame",
        "/camera/camera/color/image_raw",
        "/snapshot.jpg",
        "/health",
        "cv2.imencode",
        "rgb8",
        "bgr8",
    ]
    for snippet in required_snippets:
        assert snippet in script


def test_realsense_starter_sources_ros_and_uses_system_python():
    starter = STARTER.read_text(encoding="utf-8")

    required_snippets = [
        "/opt/ros/${ROS_DISTRO_NAME}/setup.bash",
        "sem1_pjt_ws/install/setup.bash",
        "exec /usr/bin/python3 scripts/realsense_mjpeg_bridge.py",
        "REALSENSE_COLOR_TOPIC:-/camera/camera/color/image_raw",
        "REALSENSE_STREAM_PORT:-8080",
    ]
    for snippet in required_snippets:
        assert snippet in starter
