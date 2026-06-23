#!/usr/bin/env python3
"""ROS 2 TurtleBot pose -> dashboard WebSocket bridge.

Subscribes to a pose topic such as `/amcl_pose` and forwards lightweight
`turtlebot.pose` JSON messages to `server.app`, which broadcasts them to every
open dashboard client. The dashboard then moves the cyan TurtleBot arrow in the
SLAM panel in real time.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from typing import Any

try:
    import rclpy
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from nav_msgs.msg import Odometry
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
except ImportError as exc:  # pragma: no cover - depends on ROS environment
    raise SystemExit(
        "Missing ROS 2 Python packages. Run scripts/start_turtlebot_pose_bridge.sh "
        "or source /opt/ros/humble/setup.bash before executing this bridge. "
        f"Original error: {exc}"
    ) from exc

try:
    import websockets
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing websockets package. Install with: python3 -m pip install --user websockets") from exc


def quaternion_to_yaw(z: float, w: float, x: float = 0.0, y: float = 0.0) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class LatestPose:
    def __init__(self) -> None:
        self.seq = 0
        self.payload: dict[str, Any] | None = None

    def update_from_pose(self, *, x: float, y: float, yaw: float, frame_id: str, topic: str) -> None:
        self.seq += 1
        self.payload = {
            "type": "turtlebot.pose",
            "pose": {"x": x, "y": y, "yaw": yaw},
            "frame_id": frame_id or "map",
            "topic": topic,
            "status": "실시간 pose 수신",
            "seq": self.seq,
            "stamp": time.time(),
        }


class TurtleBotPoseBridge:
    def __init__(self, topic: str, message_type: str) -> None:
        self.topic = topic
        self.message_type = message_type
        self.latest = LatestPose()
        self.node = rclpy.create_node("turtlebot_pose_ws_bridge")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        if message_type == "odom":
            self.subscription = self.node.create_subscription(Odometry, topic, self._on_odom, qos)
        else:
            self.subscription = self.node.create_subscription(PoseWithCovarianceStamped, topic, self._on_amcl_pose, qos)

    def _on_amcl_pose(self, msg: PoseWithCovarianceStamped) -> None:
        pose = msg.pose.pose
        yaw = quaternion_to_yaw(pose.orientation.z, pose.orientation.w, pose.orientation.x, pose.orientation.y)
        self.latest.update_from_pose(
            x=float(pose.position.x),
            y=float(pose.position.y),
            yaw=float(yaw),
            frame_id=msg.header.frame_id,
            topic=self.topic,
        )

    def _on_odom(self, msg: Odometry) -> None:
        pose = msg.pose.pose
        yaw = quaternion_to_yaw(pose.orientation.z, pose.orientation.w, pose.orientation.x, pose.orientation.y)
        self.latest.update_from_pose(
            x=float(pose.position.x),
            y=float(pose.position.y),
            yaw=float(yaw),
            frame_id=msg.header.frame_id,
            topic=self.topic,
        )


async def websocket_sender(bridge: TurtleBotPoseBridge, ws_url: str, rate_hz: float) -> None:
    period = 1.0 / max(rate_hz, 0.1)
    last_sent_seq = -1
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                print(f"TurtleBot pose bridge connected to {ws_url}", flush=True)
                while True:
                    rclpy.spin_once(bridge.node, timeout_sec=0.01)
                    payload = bridge.latest.payload
                    if payload and payload["seq"] != last_sent_seq:
                        await ws.send(json.dumps(payload, ensure_ascii=False))
                        last_sent_seq = payload["seq"]
                    await asyncio.sleep(period)
        except Exception as exc:  # noqa: BLE001 - keep bridge alive during server restarts
            print(f"TurtleBot pose bridge reconnecting after error: {exc}", flush=True)
            await asyncio.sleep(1.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forward TurtleBot pose updates to the dashboard WebSocket server")
    parser.add_argument("--topic", default="/amcl_pose", help="Pose topic to subscribe, usually /amcl_pose")
    parser.add_argument("--message-type", choices=["amcl", "odom"], default="amcl", help="Subscribe message type: geometry_msgs/PoseWithCovarianceStamped or nav_msgs/Odometry")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8765", help="server.app WebSocket URL")
    parser.add_argument("--rate-hz", type=float, default=10.0, help="Maximum WebSocket publish rate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rclpy.init()
    bridge = TurtleBotPoseBridge(args.topic, args.message_type)
    print(f"TurtleBot pose bridge subscribed to {args.topic} ({args.message_type})", flush=True)
    try:
        asyncio.run(websocket_sender(bridge, args.ws_url, args.rate_hz))
    except KeyboardInterrupt:
        pass
    finally:
        bridge.node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
