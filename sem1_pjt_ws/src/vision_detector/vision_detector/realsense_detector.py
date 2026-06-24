"""RealSense D435i color + depth object detector.

The ROS node follows the reference project pattern: subscribe to color image,
aligned depth image, and camera_info; detect the active target object with either
legacy HSV color thresholding or a custom YOLOv5 `best.pt`; publish a
`geometry_msgs/Point` containing camera-frame 3D coordinates in millimetres.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class RealSenseIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float


@dataclass(frozen=True)
class HsvRange:
    lower: tuple[int, int, int]
    upper: tuple[int, int, int]


@dataclass(frozen=True)
class DepthDetection:
    pixel: tuple[int, int]
    camera_point_mm: tuple[float, float, float]
    area: float
    label: str | None = None
    confidence: float | None = None

@dataclass(frozen=True)
class YoloDetection:
    label: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox_xyxy
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    @property
    def center_pixel(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.bbox_xyxy
        return int(round((x1 + x2) / 2.0)), int(round((y1 + y2) / 2.0))


HSV_RANGES = {
    "yellow": HsvRange((15, 100, 80), (45, 255, 255)),
    "blue": HsvRange((100, 150, 80), (130, 255, 255)),
    "green": HsvRange((40, 100, 80), (80, 255, 255)),
}


def deproject_pixel_to_camera_mm(u: int, v: int, depth_mm: float, intrinsics: RealSenseIntrinsics) -> tuple[float, float, float]:
    x = (float(u) - intrinsics.cx) * float(depth_mm) / intrinsics.fx
    y = (float(v) - intrinsics.cy) * float(depth_mm) / intrinsics.fy
    return x, y, float(depth_mm)


def red_mask(hsv_image: Any):
    import cv2
    import numpy as np

    mask1 = cv2.inRange(hsv_image, np.array([0, 150, 80]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv_image, np.array([170, 150, 80]), np.array([179, 255, 255]))
    return cv2.bitwise_or(mask1, mask2)


def mask_for_hsv_range(hsv_image: Any, hsv_range: HsvRange):
    import cv2
    import numpy as np

    return cv2.inRange(hsv_image, np.array(hsv_range.lower), np.array(hsv_range.upper))


def mask_for_target_color(hsv_image: Any, target_color: str):
    color = target_color.strip().lower()
    if color == "red":
        return red_mask(hsv_image)
    return mask_for_hsv_range(hsv_image, HSV_RANGES.get(color, HSV_RANGES["yellow"]))


def median_depth_near_pixel(depth_image: Any, u: int, v: int, *, radius: int = 2) -> float:
    height, width = depth_image.shape
    u_min, u_max = max(0, u - radius), min(width, u + radius + 1)
    v_min, v_max = max(0, v - radius), min(height, v + radius + 1)
    roi = depth_image[v_min:v_max, u_min:u_max]
    valid_depths = roi[roi > 0]
    if len(valid_depths) == 0:
        return 0.0
    import numpy as np

    return float(np.median(valid_depths))


def detect_largest_colored_depth_point(
    bgr_image: Any,
    depth_image: Any,
    intrinsics: RealSenseIntrinsics,
    hsv_range: HsvRange,
    *,
    min_area: float = 1000.0,
) -> DepthDetection | None:
    import cv2
    import numpy as np

    hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    mask = mask_for_hsv_range(hsv_image, hsv_range)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = [contour for contour in contours if cv2.contourArea(contour) >= min_area]
    if not candidates:
        return None
    contour = max(candidates, key=cv2.contourArea)
    rect = cv2.minAreaRect(contour)
    u, v = int(rect[0][0]), int(rect[0][1])
    depth_mm = median_depth_near_pixel(depth_image, u, v)
    if depth_mm <= 0:
        return None
    return DepthDetection(
        pixel=(u, v),
        camera_point_mm=deproject_pixel_to_camera_mm(u, v, depth_mm, intrinsics),
        area=float(cv2.contourArea(contour)),
    )


def detect_largest_colored_depth_point_by_color(
    bgr_image: Any,
    depth_image: Any,
    intrinsics: RealSenseIntrinsics,
    target_color: str,
    *,
    min_area: float = 1000.0,
) -> DepthDetection | None:
    import cv2
    import numpy as np

    hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    mask = mask_for_target_color(hsv_image, target_color)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = [contour for contour in contours if cv2.contourArea(contour) >= min_area]
    if not candidates:
        return None
    contour = max(candidates, key=cv2.contourArea)
    rect = cv2.minAreaRect(contour)
    u, v = int(rect[0][0]), int(rect[0][1])
    depth_mm = median_depth_near_pixel(depth_image, u, v)
    if depth_mm <= 0:
        return None
    return DepthDetection(
        pixel=(u, v),
        camera_point_mm=deproject_pixel_to_camera_mm(u, v, depth_mm, intrinsics),
        area=float(cv2.contourArea(contour)),
    )


def _label_from_model_names(names: Any, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
        return str(names[class_id])
    return str(class_id)


def parse_yolo_xyxy_results(results: Any, names: Any) -> list[YoloDetection]:
    """Convert YOLOv5 `results.xyxy[0]` rows into dependency-free detections."""

    detections: list[YoloDetection] = []
    rows = results.xyxy[0]
    if hasattr(rows, "detach"):
        rows = rows.detach().cpu().numpy()
    for row in rows:
        values = [float(value) for value in row[:6]]
        x1, y1, x2, y2, confidence, class_id = values
        detections.append(
            YoloDetection(
                label=_label_from_model_names(names, int(class_id)),
                confidence=float(confidence),
                bbox_xyxy=(float(x1), float(y1), float(x2), float(y2)),
            )
        )
    return detections


def select_yolo_detection(
    detections: Sequence[YoloDetection],
    target_labels: Sequence[str],
    *,
    min_confidence: float = 0.35,
    min_area: float = 1000.0,
) -> YoloDetection | None:
    normalized_targets = {label.strip().lower() for label in target_labels if label.strip()}
    candidates = [
        detection
        for detection in detections
        if detection.confidence >= min_confidence
        and detection.area >= min_area
        and (not normalized_targets or detection.label.lower() in normalized_targets)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda detection: (detection.confidence, detection.area))


def detect_largest_yolo_depth_point(
    bgr_image: Any,
    depth_image: Any,
    intrinsics: RealSenseIntrinsics,
    yolo_model: Any,
    target_labels: Sequence[str],
    *,
    min_confidence: float = 0.35,
    min_area: float = 1000.0,
) -> DepthDetection | None:
    """Run a custom YOLOv5 model and return the selected label's 3D point."""

    results = yolo_model(bgr_image)
    names = getattr(yolo_model, "names", getattr(results, "names", {}))
    detection = select_yolo_detection(
        parse_yolo_xyxy_results(results, names),
        target_labels,
        min_confidence=min_confidence,
        min_area=min_area,
    )
    if detection is None:
        return None
    u, v = detection.center_pixel
    depth_mm = median_depth_near_pixel(depth_image, u, v, radius=3)
    if depth_mm <= 0:
        return None
    return DepthDetection(
        pixel=(u, v),
        camera_point_mm=deproject_pixel_to_camera_mm(u, v, depth_mm, intrinsics),
        area=detection.area,
        label=detection.label,
        confidence=detection.confidence,
    )


class RealSenseObjectDetectorNode:
    def __init__(self) -> None:
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Image, CameraInfo
        from geometry_msgs.msg import Point
        from std_msgs.msg import String
        from cv_bridge import CvBridge

        class _Node(Node):
            pass

        self.node = _Node("realsense_object_detector")
        self.bridge = CvBridge()
        self.Point = Point
        self.String = String
        self.detector_mode = str(self.node.declare_parameter("detector_mode", "yolo").value).strip().lower()
        self.yolo_model_path = str(
            self.node.declare_parameter(
                "yolo_model_path",
                "/home/ssafy/smart-assembly-transport/models/yolo/car_parts_best.pt",
            ).value
        )
        target_labels_param = str(self.node.declare_parameter("target_labels", "car_lower,car_upper").value)
        self.target_labels = self._parse_labels(target_labels_param)
        self.target_label = self.target_labels[0] if self.target_labels else "car_lower"
        # Backward-compatible color path for older demos/tests.
        self.target_color = str(self.node.declare_parameter("target_color", "yellow").value)
        self.min_area = float(self.node.declare_parameter("min_area", 1000.0).value)
        self.min_confidence = float(self.node.declare_parameter("min_confidence", 0.35).value)
        self.depth_image = None
        self.intrinsics: RealSenseIntrinsics | None = None
        self.yolo_model = None
        if self.detector_mode == "yolo":
            import importlib

            self.yolo_model = self._load_yolo_model(importlib.import_module("torch"))
        self.publisher = self.node.create_publisher(Point, "/target_pixel", 10)
        self.label_pub = self.node.create_publisher(String, "/target_label", 10)
        self.color_sub = self.node.create_subscription(String, "/target_color", self.target_callback, 10)
        self.label_sub = self.node.create_subscription(String, "/target_label_cmd", self.target_callback, 10)
        self.image_sub = self.node.create_subscription(Image, "/camera/camera/color/image_raw", self.image_callback, qos_profile_sensor_data)
        self.depth_sub = self.node.create_subscription(Image, "/camera/camera/aligned_depth_to_color/image_raw", self.depth_callback, qos_profile_sensor_data)
        self.info_sub = self.node.create_subscription(CameraInfo, "/camera/camera/color/camera_info", self.info_callback, qos_profile_sensor_data)
        self.node.get_logger().info(
            "RealSense D435i detector ready; "
            f"mode={self.detector_mode}, target={self.target_label}, model={self.yolo_model_path}; publishing /target_pixel"
        )

    @staticmethod
    def _parse_labels(value: str) -> tuple[str, ...]:
        return tuple(label.strip().lower() for label in value.split(",") if label.strip())

    def _load_yolo_model(self, torch: Any) -> Any:
        model_path = Path(self.yolo_model_path).expanduser()
        if not model_path.exists():
            raise FileNotFoundError(f"YOLO model not found: {model_path}")
        model = torch.hub.load("ultralytics/yolov5", "custom", path=str(model_path), trust_repo=True)
        model.conf = self.min_confidence
        self.node.get_logger().info(f"Loaded YOLOv5 custom model labels={getattr(model, 'names', {})}")
        return model

    def target_callback(self, msg: Any) -> None:
        target = msg.data.strip().lower()
        if self.detector_mode == "yolo":
            self.target_label = target
            self.node.get_logger().info(f"Target YOLO label changed to {self.target_label}")
        else:
            self.target_color = target
            self.node.get_logger().info(f"Target color changed to {self.target_color}")

    # Backward-compatible name for older launch files/tests that call color_callback directly.
    color_callback = target_callback

    def info_callback(self, msg: Any) -> None:
        self.intrinsics = RealSenseIntrinsics(fx=msg.k[0], fy=msg.k[4], cx=msg.k[2], cy=msg.k[5])

    def depth_callback(self, msg: Any) -> None:
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as exc:  # noqa: BLE001
            self.node.get_logger().error(f"Depth conversion failed: {exc}")

    def image_callback(self, msg: Any) -> None:
        if self.depth_image is None or self.intrinsics is None:
            return
        if self.detector_mode == "yolo" and self.target_label == "none":
            return
        if self.detector_mode != "yolo" and self.target_color == "none":
            return
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:  # noqa: BLE001
            self.node.get_logger().error(f"Color conversion failed: {exc}")
            return
        if self.detector_mode == "yolo":
            if self.yolo_model is None:
                self.node.get_logger().error("YOLO detector mode selected but model is not loaded")
                return
            detection = detect_largest_yolo_depth_point(
                bgr,
                self.depth_image,
                self.intrinsics,
                self.yolo_model,
                [self.target_label],
                min_confidence=self.min_confidence,
                min_area=self.min_area,
            )
        else:
            detection = detect_largest_colored_depth_point_by_color(
                bgr,
                self.depth_image,
                self.intrinsics,
                self.target_color,
                min_area=self.min_area,
            )
        if not detection:
            return
        point_msg = self.Point()
        point_msg.x, point_msg.y, point_msg.z = detection.camera_point_mm
        self.publisher.publish(point_msg)
        if detection.label:
            label_msg = self.String()
            label_msg.data = detection.label
            self.label_pub.publish(label_msg)

    def destroy_node(self) -> None:
        self.node.destroy_node()

def main(args=None) -> None:
    import rclpy

    rclpy.init(args=args)
    wrapper = RealSenseObjectDetectorNode()
    try:
        rclpy.spin(wrapper.node)
    except KeyboardInterrupt:
        pass
    finally:
        wrapper.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
