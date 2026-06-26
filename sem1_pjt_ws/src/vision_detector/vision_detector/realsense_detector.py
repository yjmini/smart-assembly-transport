"""RealSense D435i color + depth object detector.

The ROS node follows the reference project pattern: subscribe to color image,
aligned depth image, and camera_info; detect the active target object with either
legacy HSV color thresholding or a custom YOLOv5 `best.pt`; publish a
`geometry_msgs/Point` containing camera-frame 3D coordinates in millimetres.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
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
    bbox_xyxy: tuple[float, float, float, float] | None = None

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
    x, y, w, h = cv2.boundingRect(contour)
    return DepthDetection(
        pixel=(u, v),
        camera_point_mm=deproject_pixel_to_camera_mm(u, v, depth_mm, intrinsics),
        area=float(cv2.contourArea(contour)),
        bbox_xyxy=(float(x), float(y), float(x + w), float(y + h)),
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
    x, y, w, h = cv2.boundingRect(contour)
    return DepthDetection(
        pixel=(u, v),
        camera_point_mm=deproject_pixel_to_camera_mm(u, v, depth_mm, intrinsics),
        area=float(cv2.contourArea(contour)),
        bbox_xyxy=(float(x), float(y), float(x + w), float(y + h)),
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


def _roi_to_xyxy(roi: Sequence[float] | None, image_shape: tuple[int, int] | None) -> tuple[float, float, float, float] | None:
    if not roi or len(roi) != 4 or image_shape is None:
        return None
    height, width = image_shape[:2]
    x, y, w, h = [float(value) for value in roi]
    if max(abs(x), abs(y), abs(w), abs(h)) <= 1.0:
        x, w = x * width, w * width
        y, h = y * height, h * height
    x1 = max(0.0, min(float(width), x))
    y1 = max(0.0, min(float(height), y))
    x2 = max(0.0, min(float(width), x + w))
    y2 = max(0.0, min(float(height), y + h))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def filter_yolo_detections_by_roi(
    detections: Sequence[YoloDetection],
    roi: Sequence[float] | None,
    *,
    image_shape: tuple[int, int] | None,
) -> list[YoloDetection]:
    roi_xyxy = _roi_to_xyxy(roi, image_shape)
    if roi_xyxy is None:
        return list(detections)
    rx1, ry1, rx2, ry2 = roi_xyxy
    return [
        detection
        for detection in detections
        if rx1 <= detection.center_pixel[0] <= rx2 and ry1 <= detection.center_pixel[1] <= ry2
    ]


def parse_roi(value: str) -> tuple[float, float, float, float] | None:
    text = (value or "").strip()
    if not text or text.lower() in {"none", "off", "disabled", "full"}:
        return None
    parts = [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]
    if len(parts) != 4:
        raise ValueError(f"ROI must be four comma-separated numbers x,y,w,h; got: {value!r}")
    return tuple(float(part) for part in parts)  # type: ignore[return-value]


def draw_roi_boundary(bgr_image: Any, roi: Sequence[float] | None) -> Any:
    import cv2

    roi_xyxy = _roi_to_xyxy(roi, bgr_image.shape[:2])
    if roi_xyxy is None:
        return bgr_image
    x1, y1, x2, y2 = [int(round(v)) for v in roi_xyxy]
    cv2.rectangle(bgr_image, (x1, y1), (x2, y2), (255, 0, 255), 3)
    return bgr_image


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
        bbox_xyxy=detection.bbox_xyxy,
    )


def yolo_detection_to_dashboard_dict(detection: YoloDetection, *, depth_mm: float | None = None, image_shape: tuple[int, int] | None = None) -> dict[str, Any]:
    x1, y1, x2, y2 = detection.bbox_xyxy
    payload: dict[str, Any] = {
        "label": detection.label,
        "confidence": round(float(detection.confidence), 4),
        "bbox": {"x": float(x1), "y": float(y1), "w": float(x2 - x1), "h": float(y2 - y1)},
        "bbox_xyxy": [float(x1), float(y1), float(x2), float(y2)],
    }
    if depth_mm is not None and depth_mm > 0:
        payload["depth_mm"] = float(depth_mm)
    if image_shape is not None:
        height, width = image_shape[:2]
        payload["image_width"] = int(width)
        payload["image_height"] = int(height)
    return payload


def build_vision_detections_message(
    detections: Sequence[YoloDetection],
    *,
    image_shape: tuple[int, int] | None = None,
    frame_id: str = "camera_color_optical_frame",
    stamp: float | None = None,
) -> dict[str, Any]:
    return {
        "type": "vision.detections",
        "frame_id": frame_id,
        "stamp": stamp,
        "detections": [yolo_detection_to_dashboard_dict(d, image_shape=image_shape) for d in detections],
    }


def draw_yolo_detections(bgr_image: Any, detections: Sequence[YoloDetection], *, target_label: str = "") -> Any:
    import cv2

    annotated = bgr_image.copy()
    for index, detection in enumerate(detections):
        x1, y1, x2, y2 = [int(round(v)) for v in detection.bbox_xyxy]
        color = [(56, 189, 248), (16, 185, 129), (245, 158, 11), (239, 68, 68)][index % 4]
        # RGB design tokens converted approximately to BGR for OpenCV drawing.
        bgr_color = (color[2], color[1], color[0])
        thickness = 3 if detection.label.lower() == target_label.lower() else 2
        cv2.rectangle(annotated, (x1, y1), (x2, y2), bgr_color, thickness)
        label = f"{detection.label} {detection.confidence:.2f}"
        (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
        y_text = max(text_h + 8, y1)
        cv2.rectangle(annotated, (x1, y_text - text_h - 8), (x1 + text_w + 8, y_text + baseline), (0, 0, 0), -1)
        cv2.putText(annotated, label, (x1 + 4, y_text - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.58, bgr_color, 2, cv2.LINE_AA)
    if not detections:
        cv2.putText(annotated, "YOLO: no detections", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 215, 255), 2, cv2.LINE_AA)
    return annotated


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
        self.yolo_roi = parse_roi(str(self.node.declare_parameter("yolo_roi", "0.161,0.0,0.611,0.599").value))
        self.depth_image = None
        self.intrinsics: RealSenseIntrinsics | None = None
        self.yolo_model = None
        if self.detector_mode == "yolo":
            import importlib

            self.yolo_model = self._load_yolo_model(importlib.import_module("torch"))
        self.publisher = self.node.create_publisher(Point, "/target_pixel", 10)
        self.label_pub = self.node.create_publisher(String, "/target_label", 10)
        self.annotated_image_pub = self.node.create_publisher(Image, "/vision/yolo/annotated_image", 10)
        self.detections_pub = self.node.create_publisher(String, "/vision/detections", 10)
        self.color_sub = self.node.create_subscription(String, "/target_color", self.target_callback, 10)
        self.label_sub = self.node.create_subscription(String, "/target_label_cmd", self.target_callback, 10)
        self.image_sub = self.node.create_subscription(Image, "/camera/camera/color/image_raw", self.image_callback, qos_profile_sensor_data)
        self.depth_sub = self.node.create_subscription(Image, "/camera/camera/aligned_depth_to_color/image_raw", self.depth_callback, qos_profile_sensor_data)
        self.info_sub = self.node.create_subscription(CameraInfo, "/camera/camera/color/camera_info", self.info_callback, qos_profile_sensor_data)
        self.node.get_logger().info(
            "RealSense D435i detector ready; "
            f"mode={self.detector_mode}, target={self.target_label}, model={self.yolo_model_path}, roi={self.yolo_roi}; "
            "publishing /target_pixel, /vision/yolo/annotated_image, /vision/detections"
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

    def _publish_annotated_image(self, bgr: Any, detections: Sequence[YoloDetection]) -> None:
        annotated = draw_yolo_detections(bgr, detections, target_label=self.target_label)
        annotated = draw_roi_boundary(annotated, self.yolo_roi if self.detector_mode == "yolo" else None)
        try:
            image_msg = self.bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
            image_msg.header.frame_id = "camera_color_optical_frame"
            self.annotated_image_pub.publish(image_msg)
        except Exception as exc:  # noqa: BLE001
            self.node.get_logger().error(f"Annotated image publish failed: {exc}")

    def _publish_detection_json(self, detections: Sequence[YoloDetection], image_shape: tuple[int, int]) -> None:
        payload = build_vision_detections_message(detections, image_shape=image_shape, frame_id="camera_color_optical_frame", stamp=self.node.get_clock().now().nanoseconds / 1e9)
        msg = self.String()
        msg.data = json.dumps(payload, ensure_ascii=False)
        self.detections_pub.publish(msg)

    def image_callback(self, msg: Any) -> None:
        if self.detector_mode == "yolo" and self.target_label == "none":
            return
        if self.detector_mode != "yolo" and self.target_color == "none":
            return
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:  # noqa: BLE001
            self.node.get_logger().error(f"Color conversion failed: {exc}")
            return

        detections: list[YoloDetection] = []
        detection: DepthDetection | None = None
        if self.detector_mode == "yolo":
            if self.yolo_model is None:
                self.node.get_logger().error("YOLO detector mode selected but model is not loaded")
                self._publish_annotated_image(bgr, [])
                return
            results = self.yolo_model(bgr)
            names = getattr(self.yolo_model, "names", getattr(results, "names", {}))
            detections = [
                d
                for d in parse_yolo_xyxy_results(results, names)
                if d.confidence >= self.min_confidence and d.area >= self.min_area
            ]
            detections = filter_yolo_detections_by_roi(detections, self.yolo_roi, image_shape=bgr.shape[:2])
            selected = select_yolo_detection(detections, [self.target_label], min_confidence=self.min_confidence, min_area=self.min_area)
            if selected is not None and self.depth_image is not None and self.intrinsics is not None:
                u, v = selected.center_pixel
                depth_mm = median_depth_near_pixel(self.depth_image, u, v, radius=3)
                if depth_mm > 0:
                    detection = DepthDetection(
                        pixel=(u, v),
                        camera_point_mm=deproject_pixel_to_camera_mm(u, v, depth_mm, self.intrinsics),
                        area=selected.area,
                        label=selected.label,
                        confidence=selected.confidence,
                        bbox_xyxy=selected.bbox_xyxy,
                    )
            self._publish_annotated_image(bgr, detections)
            self._publish_detection_json(detections, bgr.shape[:2])
        else:
            if self.depth_image is None or self.intrinsics is None:
                return
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
