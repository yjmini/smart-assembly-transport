"""WebSocket bridge for dashboard/STT clients and real hardware adapters.

Run locally with:
    python -m server.app
Then connect a WebSocket client to ws://127.0.0.1:8765.

By default hardware commands are DRY-RUN.  Set `execute: true` in selected
messages only after the conveyor Pi and TurtleBot are reachable and safe.
"""
from __future__ import annotations

import asyncio
import json
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
        destination = "B" if any(token in lowered for token in ("b구역", "b 구역", "비구역", "비 구역", "zone b")) else "A"
        return {"intent": "create_order", "command": text or f"{destination} 구역으로 조립품 배송 시작", "destination": destination, "parts": ["base", "top"]}

    def handle_whisper_transcript(self, msg: dict[str, Any]) -> dict[str, Any]:
        transcript = msg.get("transcript") or msg.get("text") or msg.get("command") or ""
        parsed = self.parse_whisper_command(transcript)
        if parsed["intent"] == "emergency_stop":
            result = self.fsm.handle_event(EventType.HAND_DETECTED, {"source": "whisper", "transcript": transcript})
            return make_state_event(result.state, "handled whisper emergency_stop", {"command": result.command, "speech": parsed, **(result.payload or {})})
        order = make_order(parsed["command"], parsed["destination"], parsed["parts"])
        result = self.fsm.handle_event(EventType.ORDER_CREATED, order)
        return make_state_event(result.state, "handled whisper create_order", {"command": result.command, "speech": parsed, **(result.payload or {})})

    async def handle_message(self, raw: str) -> dict[str, Any]:
        msg = json.loads(raw)
        msg_type = msg.get("type")
        if msg_type == "order.create":
            order = make_order(msg.get("command", "assemble and deliver"), msg.get("destination", "A"), msg.get("parts", ["base", "top"]))
            result = self.fsm.handle_event(EventType.ORDER_CREATED, order)
            return make_state_event(result.state, f"handled {msg_type}", {"command": result.command, **(result.payload or {})})
        if msg_type in {"speech.stt.final", "whisper.transcript", "whisper.command"}:
            return self.handle_whisper_transcript(msg)
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

    async def websocket_handler(self, websocket):
        async for raw in websocket:
            try:
                response = await self.handle_message(raw)
            except Exception as exc:  # noqa: BLE001 - surface to local dashboard
                response = {"type": "factory.error", "message": str(exc)}
            await websocket.send(json.dumps(response, ensure_ascii=False))


async def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
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
