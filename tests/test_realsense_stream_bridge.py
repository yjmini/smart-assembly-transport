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
        "YOLO_ROI:-0.161,0.0,0.611,0.599",
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
    assert "grid-template-columns:repeat(12" in progress
    assert "white-space:nowrap" in progress
    assert ".pose-list.compact-pose-grid{display:grid;grid-template-columns:repeat(6" in progress
    assert ".progress-page #slamMap{display:block;width:min(100%,calc(180px * 620 / 360));height:auto;aspect-ratio:620/360" in progress
    assert ".progress-page .pose-wide{grid-column:span 3}" in progress
    assert ".progress-page .pose-third{grid-column:span 2}" in progress


def test_yolo_annotated_stream_uses_volatile_qos_to_match_detector_publisher():
    script = BRIDGE.read_text(encoding="utf-8")
    starter = ANNOTATED_STARTER.read_text(encoding="utf-8")

    assert "REALSENSE_DURABILITY" in script
    assert "DurabilityPolicy.VOLATILE" in script
    assert "DurabilityPolicy.TRANSIENT_LOCAL" in script
    assert "REALSENSE_DURABILITY:-volatile" in starter


def test_progress_yolo_camera_crops_bottom_slightly_so_detection_status_stays_visible():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert ".progress-page .camera-shell{height:clamp(170px,21vh,190px)" in progress
    assert ".progress-page #cameraFeed" in progress
    assert "object-fit:cover" in progress
    assert "object-position:center top" in progress
    assert ".progress-page #detectionOverlay" in progress


def test_progress_slam_card_hides_verbose_map_metadata_to_keep_pose_inside_card():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert 'id="mapMeta"' not in progress
    assert 'user-cropped · resolution' not in progress
    assert "$('mapMeta')" not in progress


def test_progress_dashboard_uses_real_pick_place_stage_order_and_status_mapping():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    expected_labels = [
        "작업 명령 수신",
        "YOLO 물체 인식",
        "1차 조립",
        "2차 조립",
        "컨베이어 이동",
        "품질 확인",
        "분류 완료",
        "TurtleBot 적재",
        "SLAM/Nav2 배송",
        "배송 완료",
        "시작 위치 복귀",
        "다음 작업 대기",
    ]
    positions = [progress.index(label) for label in expected_labels]
    assert positions == sorted(positions)
    for state in [
        "OBJECT_DETECTED",
        "SORTING_COMPLETE",
        "COMPLETED_OBJECT_1_WAITING_FOR_OBJECT_2",
        "SORTING_NORMAL",
        "SORTING_ABNORMAL",
        "COMPLETED_TWO_OBJECT_PICK_PLACE",
    ]:
        assert state in progress
    assert "startConveyorSortLoop" in progress
    assert "setProgressState(sequence[i++]" in progress


def test_operator_stack_forwards_task_status_to_dashboard_progress():
    root = Path(__file__).resolve().parents[1]
    bridge = (root / "scripts" / "task_status_ws_bridge.py").read_text(encoding="utf-8")
    starter = (root / "scripts" / "start_operator_ui.sh").read_text(encoding="utf-8")

    assert "/task_status" in bridge
    assert "std_msgs.msg import String" in bridge
    assert '"type": "task.status"' in bridge
    assert "websockets.connect" in bridge
    assert "task_status" in starter
    assert "scripts/task_status_ws_bridge.py" in starter


def test_progress_task_status_uses_real_conveyor_states_without_rewinding_after_sorting():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert "status==='CONVEYOR_MOVING'" in progress
    assert "status==='QC_CHECK'" in progress
    assert "status==='SORTING_COMPLETE'" in progress
    assert "stateIndexFor('SORTING_COMPLETE')" in progress
    assert "stateIndex()<stateIndexFor('SORTING_COMPLETE'))setProgressState('ASSEMBLY_STAGE_2',status)" in progress


def test_progress_task_status_accepts_order_received_and_object_detected_before_assembly():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert "status==='ORDER_RECEIVED'" in progress
    assert "status.includes('OBJECT_DETECTED')" in progress
    assert "setProgressState('ORDER_RECEIVED',status)" in progress
    assert "setProgressState('OBJECT_DETECTED',status)" in progress


def test_progress_dashboard_delays_next_work_wait_after_return_home_state():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert "returnHomeWaitTimer" in progress
    assert "normalized==='RETURNING_HOME'" in progress
    assert "setProgressState('RETURNED_HOME'" in progress
    assert "1500" in progress


def test_progress_dashboard_uses_page_hostname_for_websocket_url_on_network_access():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert "defaultWebSocketUrl" in progress
    assert "window.location.hostname" in progress
    assert "serverUrl').value=defaultWebSocketUrl()" in progress


def test_start_mock_button_seeds_progress_and_timeline_through_sorting_complete():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert "function seedProgressThroughSortingComplete" in progress
    assert "setProgressState('SORTING_COMPLETE'" in progress
    assert "addTimeline(label,'STT/Mock 시작 전 완료 처리')" in progress
    assert "seedProgressThroughSortingComplete();state.lastSttCommand" in progress
    assert "state.turtlePose.destination=$('destination').value" in progress


def test_progress_connect_awaits_websocket_open_before_start_button_seeds_mock_state():
    progress = PROGRESS_VIEW.read_text(encoding="utf-8")

    assert "return new Promise" in progress
    assert "resolve(ws)" in progress
    assert "reject(new Error('websocket error'))" in progress
