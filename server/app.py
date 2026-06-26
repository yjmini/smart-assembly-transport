"""WebSocket bridge for dashboard/STT clients and real hardware adapters.

Run locally with:
    python -m server.app
Then connect a WebSocket client to ws://127.0.0.1:8765.

By default hardware commands are DRY-RUN.  Set `execute: true` in selected
messages only after the conveyor Pi and TurtleBot are reachable and safe.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for package_dir in (PROJECT_ROOT / "sem1_pjt_ws" / "src").iterdir():
    if package_dir.is_dir():
        sys.path.insert(0, str(package_dir))

from hri_interfaces.events import EventType, make_order, make_state_event
from hri_interfaces.hardware_config import HardwareConfig, DEFAULT_CONFIG_PATH
from mission_orchestrator.fsm import FactoryFSM
from mission_orchestrator.real_pipeline import RealHardwarePipeline

REPO_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "hardware.json"

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None


class WebSocketMissionServer:
    def __init__(self) -> None:
        self.fsm = FactoryFSM()
        config_path = DEFAULT_CONFIG_PATH if Path(DEFAULT_CONFIG_PATH).exists() else REPO_CONFIG_PATH
        self.hardware_config = HardwareConfig.load(config_path)
        self.pipeline = RealHardwarePipeline(self.hardware_config, execute=False)
        self.clients: set[Any] = set()
        self.active_turtlebot_destination: str | None = None
        self.arrival_tolerance_m = 0.35

    def hardware_status_snapshot(self) -> dict[str, Any]:
        return self.pipeline.status_snapshot()

    def real_pipeline_summary(self) -> dict[str, Any]:
        return self.pipeline.pipeline_summary()

    @staticmethod
    def parse_whisper_command(transcript: str) -> dict[str, Any]:
        """Map a Whisper transcript into the dashboard/order command schema.

        Safety words intentionally bypass complex parsing so a voice stop command
        can be surfaced to the FSM immediately.
        """
        text = (transcript or "").strip()
        lowered = text.lower()
        if any(word in lowered for word in ("정지", "멈춰", "중지", "stop", "emergency")):
            return {"intent": "emergency_stop", "command": text, "destination": None, "parts": []}
        destination = "HOME" if any(token in lowered for token in ("home", "홈", "복귀", "시작 위치", "원래 위치", "처음 위치", "제자리")) else "B" if any(token in lowered for token in ("b구역", "b 구역", "비구역", "비 구역", "zone b")) else "A"
        parts = [] if destination == "HOME" else ["base", "top"]
        return {"intent": "create_order", "command": text or f"{destination} 구역으로 조립품 배송 시작", "destination": destination, "parts": parts}

    def handle_whisper_transcript(self, msg: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
        transcript = msg.get("transcript") or msg.get("text") or msg.get("command") or ""
        parsed = self.parse_whisper_command(transcript)
        if msg.get("destination"):
            parsed["destination"] = str(msg["destination"]).upper()
        if parsed["intent"] == "emergency_stop":
            result = self.fsm.handle_event(EventType.HAND_DETECTED, {"source": "whisper", "transcript": transcript})
            return make_state_event(result.state, "handled whisper emergency_stop", {"command": result.command, "speech": parsed, **(result.payload or {})})
        return self.navigate_turtlebot_from_speech(parsed, transcript, execute=bool(msg.get("execute", False)))

    def navigate_turtlebot_from_speech(self, parsed: dict[str, Any], transcript: str, *, execute: bool) -> list[dict[str, Any]]:
        """Execute a direct Nav2 delivery command from a final STT transcript.

        This intentionally moves only the TurtleBot, not the full conveyor/Dobot
        pipeline, so an operator can say "A/B 구역으로 가" and watch the live
        pose arrow move on the dashboard.
        """
        destination = parsed.get("destination") or "A"
        pipeline = RealHardwarePipeline(self.hardware_config, execute=execute)
        result = pipeline.turtlebot.navigate(destination)
        self.active_turtlebot_destination = destination
        target = self.hardware_config.turtlebot.pose_for(destination)
        nav_state = "RETURNING_HOME" if destination.upper() == self.hardware_config.turtlebot.home_destination.upper() else "DELIVERY_NAVIGATING"
        return [
            {
                "type": "speech.stt.final",
                "transcript": transcript,
                "execute": execute,
                "speech": parsed,
            },
            {
                "type": "factory.state",
                "state": nav_state,
                "message": "STT requested direct TurtleBot navigation",
                "payload": {"speech": parsed, "destination": destination, "command": transcript},
            },
            {
                "type": "hardware.command_result",
                "subsystem": "turtlebot",
                "action": f"navigate_{destination}",
                "destination": destination,
                "target_pose": {"x": target.x, "y": target.y, "yaw": target.yaw},
                **asdict(result),
            },
        ]

    def turtlebot_arrival_events(self, msg: dict[str, Any]) -> list[dict[str, Any]]:
        destination = self.active_turtlebot_destination
        if not destination:
            return []
        pose = msg.get("pose") or msg
        try:
            x = float(pose["x"])
            y = float(pose["y"])
            target = self.hardware_config.turtlebot.pose_for(destination)
        except Exception:
            return []
        distance = math.hypot(x - target.x, y - target.y)
        if distance > self.arrival_tolerance_m:
            return []
        self.active_turtlebot_destination = None
        is_home = destination.upper() == self.hardware_config.turtlebot.home_destination.upper()
        state = "RETURNING_HOME" if is_home else "DELIVERED"
        message = "TurtleBot arrived home" if is_home else "TurtleBot delivery arrived"
        return [
            {
                "type": "factory.state",
                "state": state,
                "message": message,
                "payload": {"destination": destination, "arrived": True, "distance_m": round(distance, 3)},
            }
        ]

    def passthrough_broadcast(self, msg: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
        if msg.get("type") in {"turtlebot.pose", "nav.pose"}:
            events = self.turtlebot_arrival_events(msg)
            return [msg, *events] if events else msg
        return msg

    async def handle_message(self, raw: str) -> dict[str, Any] | list[dict[str, Any]]:
        msg = json.loads(raw)
        msg_type = msg.get("type")
        if msg_type == "order.create":
            order = make_order(msg.get("command", "assemble and deliver"), msg.get("destination", "A"), msg.get("parts", ["base", "top"]))
            result = self.fsm.handle_event(EventType.ORDER_CREATED, order)
            return make_state_event(result.state, f"handled {msg_type}", {"command": result.command, **(result.payload or {})})
        if msg_type in {"speech.stt.final", "whisper.transcript", "whisper.command"}:
            return self.handle_whisper_transcript(msg)
        if msg_type == "turtlebot.navigate":
            parsed = {"intent": "create_order", "command": msg.get("command", "dashboard navigate"), "destination": msg.get("destination", "A"), "parts": []}
            return self.navigate_turtlebot_from_speech(parsed, parsed["command"], execute=bool(msg.get("execute", False)))
        if msg_type in {"turtlebot.pose", "nav.pose", "vision.detections", "vision.detection", "speech.stt.partial", "task.status", "task_status"}:
            return self.passthrough_broadcast(msg)
        if msg_type == "speech.tts.done":
            return {"type": "speech.tts.ack", "text": msg.get("text", ""), "voice": msg.get("voice", "whisper-tts"), "status": "done"}
        if msg_type == "event":
            result = self.fsm.handle_event(EventType(msg["event"]), msg.get("payload"))
            return make_state_event(result.state, f"handled {msg_type}", {"command": result.command, **(result.payload or {})})
        if msg_type == "admin.unlock":
            result = self.fsm.handle_event(EventType.ADMIN_UNLOCKED, {"admin": msg.get("admin", "dashboard")})
            return make_state_event(result.state, f"handled {msg_type}", {"command": result.command, **(result.payload or {})})
        if msg_type == "hardware.status":
            return self.hardware_status_snapshot()
        if msg_type == "hardware.pipeline":
            return self.real_pipeline_summary()
        if msg_type == "hardware.run_order_plan":
            execute = bool(msg.get("execute", False))
            pipeline = RealHardwarePipeline(self.hardware_config, execute=execute)
            return {"type": "hardware.run_order_plan.result", "execute": execute, "events": pipeline.run_order_plan(msg.get("destination", "A"))}
        raise ValueError(f"Unsupported message type: {msg_type}")

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self.clients:
            return
        encoded = json.dumps(payload, ensure_ascii=False)
        stale = []
        for client in list(self.clients):
            try:
                await client.send(encoded)
            except Exception:
                stale.append(client)
        for client in stale:
            self.clients.discard(client)

    async def websocket_handler(self, websocket):
        self.clients.add(websocket)
        try:
            async for raw in websocket:
                try:
                    response = await self.handle_message(raw)
                    responses = response if isinstance(response, list) else [response]
                except Exception as exc:  # noqa: BLE001 - surface to local dashboard
                    responses = [{"type": "factory.error", "message": str(exc)}]
                for payload in responses:
                    await self.broadcast(payload)
        finally:
            self.clients.discard(websocket)


async def serve(host: str = "0.0.0.0", port: int = 8765) -> None:
    if websockets is None:
        raise RuntimeError("Install websockets: python -m pip install websockets")
    server = WebSocketMissionServer()
    async with websockets.serve(server.websocket_handler, host, port):
        print(f"WebSocket mission server listening on ws://{host}:{port}")
        await asyncio.Future()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
