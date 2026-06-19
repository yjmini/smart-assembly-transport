"""Fast local WebSocket bridge for dashboard/STT clients.

Run locally with:
    python -m server.app
Then connect a WebSocket client to ws://127.0.0.1:8765.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

try:  # works after `source sem1_pjt_ws/install/setup.bash`
    from hri_interfaces.events import EventType, make_order, make_state_event
    from mission_orchestrator.fsm import FactoryFSM
except ImportError:  # works from repository root without colcon install
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.events import EventType, make_order, make_state_event
    from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.fsm import FactoryFSM

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None


class WebSocketMissionServer:
    def __init__(self) -> None:
        self.fsm = FactoryFSM()

    async def handle_message(self, raw: str) -> dict[str, Any]:
        msg = json.loads(raw)
        msg_type = msg.get("type")
        if msg_type == "order.create":
            order = make_order(msg.get("command", "assemble and deliver"), msg.get("destination", "A"), msg.get("parts", ["base", "top"]))
            result = self.fsm.handle_event(EventType.ORDER_CREATED, order)
        elif msg_type == "event":
            result = self.fsm.handle_event(EventType(msg["event"]), msg.get("payload"))
        elif msg_type == "admin.unlock":
            result = self.fsm.handle_event(EventType.ADMIN_UNLOCKED, {"admin": msg.get("admin", "dashboard")})
        else:
            raise ValueError(f"Unsupported message type: {msg_type}")
        return make_state_event(result.state, f"handled {msg_type}", {"command": result.command, **(result.payload or {})})

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
