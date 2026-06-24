import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_vue_dashboard_declares_required_frontend_stack_and_routes():
    package = json.loads(read("web/package.json"))
    deps = package["dependencies"]

    assert "vue" in deps
    assert "vue-router" in deps
    assert "chart.js" in deps

    router = read("web/src/router.js")
    assert "createRouter" in router
    assert "createWebHashHistory" in router
    for route in ["/", "/progress", "/results"]:
        assert f"path: '{route}'" in router or f'path: "{route}"' in router


def test_vue_dashboard_preserves_existing_operator_controls_and_live_panels():
    app = read("web/src/App.vue")
    main = read("web/src/main.js")

    for snippet in [
        "RealSense D435i · YOLO 실시간 화면",
        "SLAM / TurtleBot 위치",
        "Whisper STT / TTS 음성 연동",
        "WebSocket 연결",
        "STT/Mock 작업 시작",
        "다음 mock 이벤트",
        "손 감지 / 비상정지",
        "관리자 Unlock",
        "실제 order plan 실행",
        "speech.stt.final",
        "hardware.run_order_plan",
        "turtlebot.pose",
        "vision.detections",
        "mapWorldToPixel",
        "parseWhisperIntent",
        "shouldAcceptTurtlePose",
    ]:
        assert snippet in app

    assert "new Chart" in app
    assert "Chart" in main


def test_django_mysql_backend_is_configured_for_dashboard_logs():
    settings = read("dashboard_backend/settings.py")
    models = read("dashboard_backend/operations/models.py")
    urls = read("dashboard_backend/operations/urls.py")
    views = read("dashboard_backend/operations/views.py")
    manage = read("manage.py")

    assert "django.db.backends.mysql" in settings
    assert "SMART_ASSEMBLY_DB_NAME" in settings
    assert "operations" in settings
    assert "DJANGO_SETTINGS_MODULE" in manage

    for model_name in ["Order", "FactoryEvent", "VisionDetection", "DeliveryResult", "EmergencyStopLog"]:
        assert f"class {model_name}" in models

    for endpoint in ["api/health", "api/orders", "api/events", "api/metrics"]:
        assert endpoint in urls or endpoint.split("api/")[1] in urls

    for view_name in ["health", "create_order", "record_event", "metrics"]:
        assert f"def {view_name}" in views
