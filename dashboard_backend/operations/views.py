import json
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
