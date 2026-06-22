from pathlib import Path


DASHBOARD_HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


def test_dashboard_exposes_operator_visibility_panels():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_ids = [
        "realsensePanel",
        "cameraFeed",
        "slamMap",
        "turtlePose",
        "flowOverview",
        "sttTranscript",
        "productivityCards",
        "operationsTimeline",
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in html

    required_labels = [
        "RealSense D435i",
        "YOLO 실시간 화면",
        "SLAM / TurtleBot 위치",
        "STT 명령 확인",
        "생산성 지표",
        "전체 진행상황",
    ]
    for label in required_labels:
        assert label in html


def test_dashboard_tracks_stt_command_pose_and_productivity_in_javascript():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_state_keys = [
        "lastSttCommand",
        "completedCycles",
        "assembledCount",
        "deliveryCount",
        "emergencyStopCount",
        "turtlePose",
    ]
    for key in required_state_keys:
        assert key in html

    required_functions = [
        "renderSlamMap",
        "renderProductivity",
        "renderSttCommand",
        "renderFlowOverview",
        "updateOperationsFromEvent",
    ]
    for function_name in required_functions:
        assert f"function {function_name}" in html
