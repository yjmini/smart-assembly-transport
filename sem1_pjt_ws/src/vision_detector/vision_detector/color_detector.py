"""OpenCV color detector adapted from the provided picking_dobot reference.

The reference detects yellow objects and publishes the target pixel:
https://github.com/binedwin/pill-sorting-delivery/tree/main/src/picking_dobot/picking_dobot

This file keeps the detection as a pure function so tests and mock integration
can run without ROS 2 or a physical camera.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    label: str
    center: tuple[float, float]
    bbox: tuple[int, int, int, int]
    area: float
    confidence: float


HSV_RANGES = {
    "yellow": ((20, 150, 80), (35, 255, 255), "yellow_part"),
    "skin": ((0, 30, 60), (25, 180, 255), "hand_candidate"),
}


def detect_colored_objects(image_bgr, color: str = "yellow", min_area: float = 1000.0) -> list[Detection]:
    import cv2
    import numpy as np

    if color not in HSV_RANGES:
        raise ValueError(f"Unsupported color {color!r}; supported={sorted(HSV_RANGES)}")
    lower, upper, label = HSV_RANGES[color]
    hsv_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_image, np.array(lower), np.array(upper))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections: list[Detection] = []
    image_area = float(image_bgr.shape[0] * image_bgr.shape[1])
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        detections.append(Detection(label=label, center=(x + w / 2.0, y + h / 2.0), bbox=(x, y, w, h), area=area, confidence=min(1.0, area / max(image_area, 1.0) * 10.0)))
    return sorted(detections, key=lambda d: d.area, reverse=True)
