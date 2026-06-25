import json
import os
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError
from pathlib import Path
from django.http import FileResponse, HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import connection

from .models import DeliveryResult, EmergencyStopLog, FactoryEvent, Order, VisionDetection


def _json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def dashboard_index(request: HttpRequest):
    index = settings.BASE_DIR / "web" / "dist" / "index.html"
    if not index.exists():
        index = settings.BASE_DIR / "web" / "index.html"
    return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")


def dashboard_file_from(root_name: str, path: str):
    root = (settings.BASE_DIR / root_name).resolve()
    file_path = (root / path).resolve()
    if root not in file_path.parents or not file_path.exists():
        return JsonResponse({"error": "file not found"}, status=404)
    content_type = "image/png" if file_path.suffix == ".png" else "image/x-portable-graymap" if file_path.suffix == ".pgm" else "application/x-yaml" if file_path.suffix in {".yaml", ".yml"} else "application/octet-stream"
    return FileResponse(file_path.open("rb"), content_type=content_type)


def dashboard_map_asset(request: HttpRequest, path: str):
    return dashboard_file_from("map", path)


def dashboard_asset(request: HttpRequest, path: str):
    asset = (settings.BASE_DIR / "web" / "dist" / "assets" / path).resolve()
    assets_root = (settings.BASE_DIR / "web" / "dist" / "assets").resolve()
    if assets_root not in asset.parents or not asset.exists():
        return JsonResponse({"error": "asset not found"}, status=404)
    content_type = "text/javascript" if asset.suffix == ".js" else "text/css" if asset.suffix == ".css" else "application/octet-stream"
    return FileResponse(asset.open("rb"), content_type=content_type)



OLLAMA_MODEL = os.environ.get("SMART_ASSEMBLY_OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_CHAT_URL = os.environ.get("SMART_ASSEMBLY_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")

def _chatbot_context() -> dict:
    recent_orders = list(Order.objects.order_by("-created_at").values("id", "command", "destination", "parts", "status", "created_at")[:5])
    recent_events = list(FactoryEvent.objects.order_by("-created_at").values("id", "event_type", "state", "payload", "created_at")[:8])
    return {
        "metrics": {
            "orders": Order.objects.count(),
            "events": FactoryEvent.objects.count(),
            "vision_detections": VisionDetection.objects.count(),
            "deliveries": DeliveryResult.objects.filter(success=True).count(),
            "emergency_stops": EmergencyStopLog.objects.count(),
        },
        "recent_orders": recent_orders,
        "recent_events": recent_events,
    }

def _ask_ollama(question: str, context: dict) -> str:
    system = (
        "너는 자동 조립 공정 및 무인 배송 시스템 대시보드의 한국어 운영 보조 챗봇이다. "
        "주어진 DB 지표, 최근 주문, 최근 이벤트만 근거로 작업 상태와 결과를 간결하게 설명해라. "
        "확실하지 않은 실제 하드웨어 상태는 추측하지 말고 대시보드에 기록된 정보 기준이라고 밝혀라."
    )
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"프로젝트 상태 컨텍스트 JSON:\n{json.dumps(context, ensure_ascii=False, default=str)}\n\n질문: {question}"},
        ],
        "options": {"temperature": 0.2},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(OLLAMA_CHAT_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlrequest.urlopen(req, timeout=25) as res:  # noqa: S310 - local operator Ollama endpoint only
        data = json.loads(res.read().decode("utf-8"))
    return (data.get("message") or {}).get("content") or data.get("response") or "응답이 비어 있습니다."

def health(request: HttpRequest) -> JsonResponse:
    engine = connection.settings_dict.get("ENGINE", "").rsplit(".", 1)[-1]
    return JsonResponse({"ok": True, "service": "smart-assembly-dashboard", "database": engine})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def create_order(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        orders = list(Order.objects.order_by("-created_at").values("id", "command", "destination", "parts", "status", "created_at")[:50])
        return JsonResponse({"orders": orders})
    body = _json_body(request)
    order = Order.objects.create(command=body.get("command", "assemble and deliver"), destination=body.get("destination", "A"), parts=body.get("parts", ["base", "top"]))
    return JsonResponse({"id": order.id, "status": order.status, "destination": order.destination})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def record_event(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        events = list(FactoryEvent.objects.order_by("-created_at").values("id", "event_type", "state", "payload", "created_at")[:100])
        return JsonResponse({"events": events})
    body = _json_body(request)
    event = FactoryEvent.objects.create(event_type=body.get("type", body.get("event", "event")), state=body.get("state", ""), payload=body)
    if body.get("type") in {"vision.detections", "vision.detection"}:
        detections = body.get("detections") or [body.get("detection", body)]
        for detection in detections:
            VisionDetection.objects.create(label=detection.get("label") or detection.get("class", "object"), confidence=detection.get("confidence") or detection.get("score"), bbox=detection.get("bbox") or detection.get("box") or {}, camera_point_mm=detection.get("camera_point_mm") or [])
    if body.get("event") == "safety.hand_detected" or body.get("state") in {"EMERGENCY_STOP", "WAIT_ADMIN_UNLOCK"}:
        EmergencyStopLog.objects.create(source=body.get("payload", {}).get("source", "dashboard"), reason=body.get("message", "safety event"), payload=body)
    if body.get("state") == "DELIVERED":
        DeliveryResult.objects.create(destination=body.get("payload", {}).get("destination", "A"), target_pose=body.get("target_pose", {}), success=True, raw_result=body)
    return JsonResponse({"id": event.id, "stored": True})


def metrics(request: HttpRequest) -> JsonResponse:
    return JsonResponse({
        "orders": Order.objects.count(),
        "events": FactoryEvent.objects.count(),
        "vision_detections": VisionDetection.objects.count(),
        "deliveries": DeliveryResult.objects.filter(success=True).count(),
        "emergency_stops": EmergencyStopLog.objects.count(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def seed_demo_data(request: HttpRequest) -> JsonResponse:
    """Populate deterministic dashboard demo rows for Vue/API connection checks."""
    order_a = Order.objects.create(
        command="A구역으로 조립품 배송 시작",
        destination="A",
        parts=["base", "top"],
        status="DELIVERED",
    )
    order_b = Order.objects.create(
        command="B구역 긴급 배송 dry-run",
        destination="B",
        parts=["base", "top", "cover"],
        status="ORDER_RECEIVED",
    )
    demo_events = [
        ("order.created", "ORDER_RECEIVED", {"order_id": order_a.id, "destination": "A"}),
        ("vision.base_in_position", "BASE_DETECTED_STOPPING", {"confidence": 0.96}),
        ("dobot.assembly_stage_2_done", "QC_CHECK", {"step": "stage_2"}),
        ("turtlebot.delivery_arrived", "DELIVERED", {"destination": "A"}),
        ("safety.hand_detected", "WAIT_ADMIN_UNLOCK", {"source": "dashboard-demo"}),
    ]
    for event_type, state, payload in demo_events:
        FactoryEvent.objects.create(event_type=event_type, state=state, payload=payload)
    VisionDetection.objects.create(
        label="yellow_base",
        confidence=0.94,
        bbox={"x": 128, "y": 96, "w": 180, "h": 120},
        camera_point_mm=[142, -38, 612],
    )
    VisionDetection.objects.create(
        label="operator_hand",
        confidence=0.88,
        bbox={"x": 320, "y": 118, "w": 92, "h": 74},
        camera_point_mm=[280, 42, 550],
    )
    DeliveryResult.objects.create(
        destination="A",
        target_pose={"x": 1.2, "y": 0.0, "yaw": 0.0},
        success=True,
        raw_result={"mode": "demo", "order_id": order_a.id},
    )
    EmergencyStopLog.objects.create(
        source="dashboard-demo",
        reason="dummy safety event for UI verification",
        payload={"order_id": order_b.id, "state": "WAIT_ADMIN_UNLOCK"},
    )
    return JsonResponse({
        "seeded": True,
        "orders": [order_a.id, order_b.id],
        "metrics": {
            "orders": Order.objects.count(),
            "events": FactoryEvent.objects.count(),
            "vision_detections": VisionDetection.objects.count(),
            "deliveries": DeliveryResult.objects.filter(success=True).count(),
            "emergency_stops": EmergencyStopLog.objects.count(),
        },
    })


@csrf_exempt
@require_http_methods(["POST"])
def project_chatbot(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    question = (body.get("message") or body.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "message is required"}, status=400)
    context = _chatbot_context()
    try:
        answer = _ask_ollama(question, context)
        return JsonResponse({"answer": answer, "model": OLLAMA_MODEL, "context": context})
    except (URLError, HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        fallback = (
            "Ollama 로컬 모델에 연결하지 못했습니다. "
            f"현재 DB 기준 주문 {context['metrics']['orders']}건, 이벤트 {context['metrics']['events']}건, "
            f"배송 완료 {context['metrics']['deliveries']}건, 비상정지 {context['metrics']['emergency_stops']}건이 기록되어 있습니다."
        )
        return JsonResponse({"answer": fallback, "model": OLLAMA_MODEL, "context": context, "ollama_error": str(exc)}, status=200)
