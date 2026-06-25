from pathlib import Path


BRIDGE = Path(__file__).resolve().parents[1] / "scripts" / "realsense_mjpeg_bridge.py"
STARTER = Path(__file__).resolve().parents[1] / "scripts" / "start_realsense_stream.sh"
YOLO_STARTER = Path(__file__).resolve().parents[1] / "scripts" / "start_yolo_detector.sh"
ANNOTATED_STARTER = Path(__file__).resolve().parents[1] / "scripts" / "start_yolo_annotated_stream.sh"
PROGRESS_VIEW = Path(__file__).resolve().parents[1] / "web" / "src" / "views" / "ProgressView.vue"


def test_realsense_bridge_exposes_mjpeg_stream_endpoints():
    script = BRIDGE.read_text(encoding="utf-8")

    required_snippets = [
        "sensor_msgs.msg import CompressedImage, Image",
        "QoSProfile",
        "ReliabilityPolicy.RELIABLE",
        "DurabilityPolicy.TRANSIENT_LOCAL",
        "ThreadingHTTPServer",
        "multipart/x-mixed-replace; boundary=frame",
        "/camera/camera/color/image_raw",
        "/snapshot.jpg",
        "/health",
        "cv2.imencode",
        "cv2.imdecode",
        "--compressed",
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
        "REALSENSE_COMPRESSED:-0",
        "USE_FASTDDS_NO_SHM:-0",
        "ROS_DOMAIN_ID:-34",
        "FASTRTPS_DEFAULT_PROFILES_FILE",
        "config/fastdds_no_shm.xml",
        "REALSENSE_STREAM_PORT:-8080",
    ]
    for snippet in required_snippets:
        assert snippet in starter


def test_yolo_detector_publishes_annotated_topic_and_dashboard_uses_it_by_default():
    detector = YOLO_STARTER.read_text(encoding="utf-8")
    annotated = ANNOTATED_STARTER.read_text(encoding="utf-8")
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")
    node = (Path(__file__).resolve().parents[1] / "sem1_pjt_ws" / "src" / "vision_detector" / "vision_detector" / "realsense_detector.py").read_text(encoding="utf-8")

    for snippet in [
        "ros2 run vision_detector realsense_object_detector",
        "YOLO_MODEL_PATH",
        "YOLO_TARGET_LABELS",
        "ROS_DOMAIN_ID:-34",
    ]:
        assert snippet in detector

    assert "REALSENSE_COLOR_TOPIC:-/vision/yolo/annotated_image" in annotated
    assert "http://127.0.0.1:8080/stream?topic=/vision/yolo/annotated_image" in progress
    assert 'create_publisher(Image, "/vision/yolo/annotated_image"' in node
    assert 'create_publisher(String, "/vision/detections"' in node


def test_slam_pose_compacts_destination_status_and_xyz_rows():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert "compact-pose-grid" in progress
    assert 'pose-wide"><span>destination' in progress
    assert 'pose-wide"><span>status' in progress
    assert 'pose-third"><span>x' in progress
    assert 'pose-third"><span>y' in progress
    assert 'pose-third"><span>yaw' in progress
    assert "grid-template-columns:repeat(6" in progress
    assert ".progress-page #slamMap{width:100%;height:auto;aspect-ratio:620/360" in progress
    assert ".progress-page .pose-wide{grid-column:span 3}" in progress
    assert ".progress-page .pose-third{grid-column:span 2}" in progress
