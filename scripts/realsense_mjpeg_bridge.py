#!/usr/bin/env python3
"""ROS 2 Image topic -> MJPEG HTTP bridge for the operator dashboard.

Default topic matches the RealSense D435i color stream used by the dashboard:
`/camera/camera/color/image_raw`.

This intentionally avoids cv_bridge so it can run on typical ROS 2 Humble
machines with only rclpy, sensor_msgs, numpy and OpenCV installed.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover - environment dependent
    raise SystemExit(f"Missing image dependency: {exc}. Install python3-opencv and python3-numpy.") from exc

try:
    import rclpy
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import CompressedImage, Image
except ImportError as exc:  # pragma: no cover - environment dependent
    raise SystemExit(
        "Missing ROS 2 Python packages. Run via scripts/start_realsense_stream.sh "
        "or source /opt/ros/<distro>/setup.bash before executing this bridge. "
        f"Original error: {exc}"
    ) from exc


class LatestFrame:
    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.jpeg: bytes | None = None
        self.seq = 0
        self.last_error = "waiting for first image"
        self.last_stamp = 0.0
        self.width = 0
        self.height = 0
        self.encoding = ""

    def update(self, *, jpeg: bytes, width: int, height: int, encoding: str) -> None:
        with self.condition:
            self.jpeg = jpeg
            self.seq += 1
            self.last_stamp = time.time()
            self.last_error = ""
            self.width = width
            self.height = height
            self.encoding = encoding
            self.condition.notify_all()

    def set_error(self, message: str) -> None:
        with self.condition:
            self.last_error = message
            self.condition.notify_all()

    def snapshot(self, timeout: float = 2.0) -> tuple[int, bytes | None]:
        deadline = time.time() + timeout
        with self.condition:
            start_seq = self.seq
            while self.jpeg is None and time.time() < deadline:
                self.condition.wait(deadline - time.time())
            if self.jpeg is None:
                return start_seq, None
            return self.seq, self.jpeg

    def wait_next(self, previous_seq: int, timeout: float = 2.0) -> tuple[int, bytes | None]:
        deadline = time.time() + timeout
        with self.condition:
            while self.seq == previous_seq and time.time() < deadline:
                self.condition.wait(deadline - time.time())
            return self.seq, self.jpeg

    def status(self, topic: str) -> dict[str, Any]:
        with self.condition:
            age = None if not self.last_stamp else round(time.time() - self.last_stamp, 3)
            return {
                "topic": topic,
                "frames": self.seq,
                "width": self.width,
                "height": self.height,
                "encoding": self.encoding,
                "last_frame_age_sec": age,
                "ready": self.jpeg is not None,
                "error": self.last_error,
            }


def image_to_bgr(msg: Image) -> np.ndarray:
    """Convert common ROS Image encodings to an OpenCV BGR array."""
    height, width = int(msg.height), int(msg.width)
    encoding = msg.encoding.lower()
    data = np.frombuffer(msg.data, dtype=np.uint8)

    if encoding in {"bgr8", "rgb8"}:
        channels = 3
        row = data.reshape(height, int(msg.step))[:, : width * channels]
        image = row.reshape(height, width, channels)
        if encoding == "rgb8":
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image.copy()

    if encoding in {"bgra8", "rgba8"}:
        channels = 4
        row = data.reshape(height, int(msg.step))[:, : width * channels]
        image = row.reshape(height, width, channels)
        code = cv2.COLOR_BGRA2BGR if encoding == "bgra8" else cv2.COLOR_RGBA2BGR
        return cv2.cvtColor(image, code)

    if encoding in {"mono8", "8uc1"}:
        row = data.reshape(height, int(msg.step))[:, :width]
        return cv2.cvtColor(row, cv2.COLOR_GRAY2BGR)

    raise ValueError(f"Unsupported image encoding: {msg.encoding}")


class RealsenseMjpegBridge:
    def __init__(
        self,
        topic: str,
        jpeg_quality: int,
        *,
        compressed: bool = False,
        durability: str = "transient_local",
    ) -> None:
        self.topic = topic
        self.jpeg_quality = jpeg_quality
        self.compressed = compressed
        self.latest = LatestFrame()
        self.node = rclpy.create_node("realsense_mjpeg_bridge")
        normalized_durability = durability.strip().lower().replace("-", "_")
        durability_policy = (
            DurabilityPolicy.VOLATILE
            if normalized_durability in {"volatile", "vol"}
            else DurabilityPolicy.TRANSIENT_LOCAL
        )
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=durability_policy,
        )
        if compressed:
            self.subscription = self.node.create_subscription(
                CompressedImage,
                topic,
                self._on_compressed_image,
                qos,
            )
        else:
            self.subscription = self.node.create_subscription(
                Image,
                topic,
                self._on_image,
                qos,
            )

    def _on_image(self, msg: Image) -> None:
        try:
            bgr = image_to_bgr(msg)
            ok, encoded = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
            if not ok:
                raise ValueError("cv2.imencode returned false")
            self.latest.update(
                jpeg=encoded.tobytes(),
                width=int(msg.width),
                height=int(msg.height),
                encoding=msg.encoding,
            )
        except Exception as exc:  # pragma: no cover - exercised with live ROS data
            self.latest.set_error(str(exc))
            self.node.get_logger().warning(f"Failed to encode image frame: {exc}")

    def _on_compressed_image(self, msg: CompressedImage) -> None:
        try:
            compressed = bytes(msg.data)
            image = cv2.imdecode(np.frombuffer(compressed, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"Failed to decode compressed image format={msg.format!r}")
            if "jpeg" in msg.format.lower() or "jpg" in msg.format.lower():
                jpeg = compressed
            else:
                ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
                if not ok:
                    raise ValueError("cv2.imencode returned false")
                jpeg = encoded.tobytes()
            self.latest.update(
                jpeg=jpeg,
                width=int(image.shape[1]),
                height=int(image.shape[0]),
                encoding=f"compressed:{msg.format}",
            )
        except Exception as exc:  # pragma: no cover - exercised with live ROS data
            self.latest.set_error(str(exc))
            self.node.get_logger().warning(f"Failed to encode compressed image frame: {exc}")


def make_handler(bridge: RealsenseMjpegBridge):
    class Handler(BaseHTTPRequestHandler):
        server_version = "RealsenseMjpegBridge/1.0"

        def log_message(self, format: str, *args: Any) -> None:  # keep output readable
            sys.stderr.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format % args))

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/health"}:
                self._send_json(bridge.latest.status(bridge.topic))
                return
            if parsed.path == "/snapshot.jpg":
                _, frame = bridge.latest.snapshot(timeout=2.0)
                if frame is None:
                    self._send_json(bridge.latest.status(bridge.topic), HTTPStatus.SERVICE_UNAVAILABLE)
                    return
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
                return
            if parsed.path != "/stream":
                self._send_json({"error": "not found", "paths": ["/health", "/snapshot.jpg", "/stream"]}, HTTPStatus.NOT_FOUND)
                return

            requested = parse_qs(parsed.query).get("topic", [bridge.topic])[0]
            if requested != bridge.topic:
                self._send_json(
                    {"error": "bridge is subscribed to a different topic", "requested": requested, "subscribed": bridge.topic},
                    HTTPStatus.BAD_REQUEST,
                )
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            seq = -1
            while True:
                seq, frame = bridge.latest.wait_next(seq, timeout=2.0)
                if frame is None:
                    continue
                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break

    return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream a ROS 2 sensor_msgs/Image topic as MJPEG for the dashboard")
    parser.add_argument("--topic", default="/camera/camera/color/image_raw", help="ROS 2 image topic to subscribe")
    parser.add_argument("--compressed", action="store_true", help="Subscribe as sensor_msgs/CompressedImage instead of sensor_msgs/Image")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", type=int, default=8080, help="HTTP bind port")
    parser.add_argument("--jpeg-quality", type=int, default=80, help="JPEG quality 1-100")
    parser.add_argument(
        "--durability",
        default="transient_local",
        choices=["transient_local", "volatile"],
        help=(
            "Subscriber durability. RealSense camera topics often need transient_local, "
            "but locally generated YOLO annotated topics are volatile. "
            "Can also be set with REALSENSE_DURABILITY."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rclpy.init()
    bridge = RealsenseMjpegBridge(
        args.topic,
        max(1, min(100, args.jpeg_quality)),
        compressed=args.compressed,
        durability=args.durability,
    )
    spin_thread = threading.Thread(target=rclpy.spin, args=(bridge.node,), daemon=True)
    spin_thread.start()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(bridge))
    print(f"RealSense MJPEG bridge listening on http://{args.host}:{args.port}/stream?topic={args.topic}", flush=True)
    print(f"Health endpoint: http://{args.host}:{args.port}/health", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        bridge.node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
