from pathlib import Path


DASHBOARD_HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


def test_dashboard_exposes_operator_visibility_panels():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_ids = [
        "realsensePanel",
        "cameraFeed",
        "detectionOverlay",
        "visionDetections",
        "slamMap",
        "mapUrl",
        "mapLoadBtn",
        "mapMeta",
        "turtlePose",
        "flowOverview",
        "sttTranscript",
        "whisperMockText",
        "whisperMockBtn",
        "ttsPanel",
        "ttsMessage",
        "ttsReplayBtn",
        "productivityCards",
        "operationsTimeline",
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in html

    required_labels = [
        "RealSense D435i",
        "YOLO 실시간 화면",
        "SLAM / TurtleBot 위치",
        "Whisper STT / TTS 음성 연동",
        "생산성 지표",
        "전체 진행상황",
    ]
    for label in required_labels:
        assert label in html


def test_dashboard_tracks_stt_command_pose_and_productivity_in_javascript():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_state_keys = [
        "lastSttCommand",
        "sttIntent",
        "lastTtsMessage",
        "ttsStatus",
        "completedCycles",
        "assembledCount",
        "deliveryCount",
        "emergencyStopCount",
        "turtlePose",
        "visionDetections",
        "mapConfig",
    ]
    for key in required_state_keys:
        assert key in html

    required_functions = [
        "renderSlamMap",
        "renderProductivity",
        "renderSttCommand",
        "renderFlowOverview",
        "renderVisionDetections",
        "loadSlamMap",
        "mapWorldToPixel",
        "parseWhisperIntent",
        "applyWhisperTranscript",
        "announceTts",
        "ttsForState",
        "updateOperationsFromEvent",
    ]
    for function_name in required_functions:
        assert f"function {function_name}" in html


def test_dashboard_loads_real_slam_png_and_live_vision_messages():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_snippets = [
        "../map/pjt_map_view_crop.png",
        "viewCrop:{x:7,y:12,w:41,h:28}",
        "rotation:'ccw'",
        "fit:'cover'",
        "resolution:0.05",
        "origin:{x:-1.11,y:-3.59",
        "vision.detections",
        "turtlebot.pose",
        "detectionOverlay",
        "YOLO detection JSON 수신 대기",
    ]
    for snippet in required_snippets:
        assert snippet in html

    slam_png = DASHBOARD_HTML.parents[1] / "map" / "pjt_map_view_crop.png"
    assert slam_png.exists()
    assert slam_png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_dashboard_integrates_whisper_stt_and_tts_events():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_snippets = [
        "speech.stt.final",
        "whisper.transcript",
        "speech.tts.done",
        "speechSynthesis",
        "WHISPER READY",
        "TTS 안내",
        "A구역으로 조립품 배송 시작",
    ]
    for snippet in required_snippets:
        assert snippet in html
