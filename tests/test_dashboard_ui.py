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
        "micSttBtn",
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
        "connectCameraStream",
        "loadSlamMap",
        "mapWorldToPixel",
        "parseWhisperIntent",
        "applyWhisperTranscript",
        "initBrowserStt",
        "toggleBrowserStt",
        "announceTts",
        "ttsForState",
        "updateOperationsFromEvent",
        "applyTurtlePoseMessage",
        "shouldAcceptTurtlePose",
        "mapWorldYawToCanvasYaw",
    ]
    for function_name in required_functions:
        assert f"function {function_name}" in html


def test_dashboard_uses_live_pose_only_and_filters_pose_jumps():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_snippets = [
        "applyTurtlePoseMessage(d)",
        "pose jump ignored",
        "maxStep=Math.max(0.25,dt*0.8)",
        "max_step_m",
        "state.turtlePose.status='배송 이동 중'",
        "state.turtlePose.status='복귀 완료'",
        "mapWorldYawToCanvasYaw(state.turtlePose",
    ]
    for snippet in required_snippets:
        assert snippet in html

    forbidden_snippets = [
        "state.turtlePose={...state.turtlePose,...target,status:'배송 이동 중'}",
        "state.turtlePose={...state.turtlePose,x:0,y:0,yaw:0,status:'복귀 완료'}",
        "drawTurtle(ctx,p.x,p.y,state.turtlePose.yaw)",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in html


def test_dashboard_loads_real_slam_png_and_live_vision_messages():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_snippets = [
        "../map/pjt_map_view_crop.png",
        "viewCrop:{x:7,y:12,w:41,h:28}",
        "displayTargets:{HOME:{pixel:{x:8,y:20}",
        "A:{pixel:{x:34.8,y:6},color:'#ef4444'",
        "B:{pixel:{x:34.5,y:21.2},color:'#3b82f6'",
        "rotation:'ccw'",
        "fit:'cover'",
        "resolution:0.05",
        "origin:{x:-1.11,y:-3.59",
        "vision.detections",
        "turtlebot.pose",
        "execute",
        "STT FINAL · REAL NAV",
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
        "SpeechRecognition",
        "webkitSpeechRecognition",
        "마이크 STT 시작",
        "BROWSER STT READY",
        "WHISPER READY",
        "TTS 안내",
        "A구역으로 조립품 배송 시작",
    ]
    for snippet in required_snippets:
        assert snippet in html


def test_dashboard_parses_home_stt_commands_for_direct_navigation():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    required_snippets = [
        "'원래 위치'",
        "'처음 위치'",
        "'제자리'",
        "destination=isHome?'HOME'",
        "parts:isHome?[]:['base','top']",
        "send({type:'speech.stt.final',transcript:text,destination:parsed.destination",
    ]
    for snippet in required_snippets:
        assert snippet in html
