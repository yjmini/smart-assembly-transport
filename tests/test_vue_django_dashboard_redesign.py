from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dashboard_uses_cal_style_tokens_and_exact_three_route_shell():
    app = read("web/src/App.vue")
    dashboard = read("web/src/views/DashboardView.vue")
    router = read("web/src/router.js")

    for token in ["#ffffff", "#111111", "#f5f5f5", "#101010", "--font-display", "--section-spacing"]:
        assert token in app or token in dashboard

    for route in ["/", "/progress", "/results"]:
        assert f"path: '{route}'" in router or f'path: "{route}"' in router

    for retired_route in ["/operations", "/vision", "/map", "/voice", "/data", "/logs", "/settings"]:
        assert f"path: '{retired_route}'" not in router
        assert f'path: "{retired_route}"' not in router

    for label in ["홈", "작업 진행", "작업 결과"]:
        assert label in app or label in dashboard


def test_home_is_summary_and_routes_ctas_to_progress_and_results():
    dashboard = read("web/src/views/DashboardView.vue")

    assert "현재 상태 요약" in dashboard
    assert "사용 방법" in dashboard
    assert "to=\"/progress\"" in dashboard
    assert "to=\"/results\"" in dashboard
    assert "공정 시작하기" in dashboard
    assert "작업 결과 확인" in dashboard

    # Home should not carry the full operator controls anymore.
    for control in ["nextBtn", "stopBtn", "unlockBtn", "cameraConnectBtn", "whisperMockBtn"]:
        assert control not in dashboard


def test_progress_page_keeps_all_operator_work_controls_and_live_panels():
    progress = read("web/src/views/ProgressView.vue")

    for snippet in [
        "WebSocket 연결",
        "STT/Mock 작업 시작",
        "다음 mock 이벤트",
        "손 감지 / 비상정지",
        "관리자 Unlock",
        "실제 order plan 실행",
        "RealSense D435i · YOLO 실시간 화면",
        "SLAM / TurtleBot 위치",
        "Whisper STT / TTS 음성 연동",
        "작업 타임라인",
        "speech.stt.final",
        "hardware.run_order_plan",
        "turtlebot.pose",
        "vision.detections",
    ]:
        assert snippet in progress

    assert "operator-workspace" in progress
    assert "results-admin" not in progress


def test_results_page_contains_admin_result_surfaces_and_dummy_db_connection():
    results = read("web/src/views/ResultsView.vue")

    for snippet in [
        "생산성 Chart.js",
        "이벤트 로그",
        "하드웨어 구성 요약",
        "더미데이터 채우기",
        "/api/seed-demo",
        "/api/metrics",
        "/api/orders",
        "/api/events",
    ]:
        assert snippet in results

    assert "results-admin" in results
    assert "WebSocket 연결" not in results


def test_django_declares_seed_demo_endpoint_for_dummy_db_data():
    urls = read("dashboard_backend/operations/urls.py")
    views = read("dashboard_backend/operations/views.py")

    assert "api/seed-demo" in urls
    assert "seed_demo_data" in views
    for model_name in ["Order", "FactoryEvent", "VisionDetection", "DeliveryResult", "EmergencyStopLog"]:
        assert model_name in views
