#!/usr/bin/env python3
"""Forward Dobot `/task_status` ROS messages to the dashboard WebSocket.

The two-object pick/place node publishes status strings such as
`COMPLETED_OBJECT_1_WAITING_FOR_OBJECT_2`, `SORTING_NORMAL`, and
`COMPLETED_TWO_OBJECT_PICK_PLACE`.  The Vue progress dashboard maps those to the
operator-facing stages so early Dobot/conveyor work advances before TurtleBot
Nav2 events start.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Any

try:
    import rclpy
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String
except ImportError as exc:  # pragma: no cover - depends on ROS environment
    raise SystemExit(
        "Missing ROS 2 Python packages. Source /opt/ros/humble/setup.bash and "
        "sem1_pjt_ws/install/setup.bash before running this bridge. "
        f"Original error: {exc}"
    ) from exc

try:
    import websockets
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing websockets package. Install with: python3 -m pip install --user websockets") from exc


class LatestTaskStatus:
    def __init__(self) -> None:
        self.seq = 0
        self.payload: dict[str, Any] | None = None

    def update(self, status: str, topic: str) -> None:
        self.seq += 1
        self.payload = {
            "type": "task.status",
            "topic": topic,
            "status": status,
            "data": status,
            "seq": self.seq,
            "stamp": time.time(),
        }


class TaskStatusBridge:
    def __init__(self, topic: str) -> None:
        self.topic = topic
        self.latest = LatestTaskStatus()
        self.node = rclpy.create_node("task_status_ws_bridge")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.subscription = self.node.create_subscription(String, topic, self._on_status, qos)

    def _on_status(self, msg: String) -> None:
        self.latest.update(str(msg.data), self.topic)


async def websocket_sender(bridge: TaskStatusBridge, ws_url: str, rate_hz: float) -> None:
    period = 1.0 / max(rate_hz, 0.1)
    last_sent_seq = -1
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                print(f"Task status bridge connected to {ws_url}", flush=True)
                while True:
                    rclpy.spin_once(bridge.node, timeout_sec=0.01)
                    payload = bridge.latest.payload
                    if payload and payload["seq"] != last_sent_seq:
                        await ws.send(json.dumps(payload, ensure_ascii=False))
                        last_sent_seq = payload["seq"]
                    await asyncio.sleep(period)
        except Exception as exc:  # noqa: BLE001 - keep bridge alive during server restarts
            print(f"Task status bridge reconnecting after error: {exc}", flush=True)
            await asyncio.sleep(1.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forward /task_status updates to the dashboard WebSocket server")
    parser.add_argument("--topic", default="/task_status", help="std_msgs/String task status topic")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8765", help="server.app WebSocket URL")
    parser.add_argument("--rate-hz", type=float, default=20.0, help="Maximum WebSocket publish rate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rclpy.init()
    bridge = TaskStatusBridge(args.topic)
    print(f"Task status bridge subscribed to {args.topic}", flush=True)
    try:
        asyncio.run(websocket_sender(bridge, args.ws_url, args.rate_hz))
    except KeyboardInterrupt:
        pass
    finally:
        bridge.node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
