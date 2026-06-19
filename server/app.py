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
from typing import Any

try:  # works after `source sem1_pjt_ws/install/setup.bash`
    from hri_interfaces.events import EventType, make_order, make_state_event
    from hri_interfaces.hardware_config import HardwareConfig, DEFAULT_CONFIG_PATH
    from mission_orchestrator.fsm import FactoryFSM
    from mission_orchestrator.real_pipeline import RealHardwarePipeline
except ImportError:  # works from repository root without colcon install
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.events import EventType, make_order, make_state_event
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import HardwareConfig, DEFAULT_CONFIG_PATH
    from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.fsm import FactoryFSM
    from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.real_pipeline import RealHardwarePipeline

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None


class WebSocketMissionServer:
    def __init__(self) -> None:
        self.fsm = FactoryFSM()
        self.hardware_config = HardwareConfig.load(DEFAULT_CONFIG_PATH)
        self.pipeline = RealHardwarePipeline(self.hardware_config, execute=False)

    def hardware_status_snapshot(self) -> dict[str, Any]:
        return self.pipeline.status_snapshot()

    def real_pipeline_summary(self) -> dict[str, Any]:
        return self.pipeline.pipeline_summary()

    async def handle_message(self, raw: str) -> dict[str, Any]:
        msg = json.loads(raw)
        msg_type = msg.get("type")
        if msg_type == "order.create":
            order = make_order(msg.get("command", "assemble and deliver"), msg.get("destination", "A"), msg.get("parts", ["base", "top"]))
            result = self.fsm.handle_event(EventType.ORDER_CREATED, order)
            return make_state_event(result.state, f"handled {msg_type}", {"command": result.command, **(result.payload or {})})
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
