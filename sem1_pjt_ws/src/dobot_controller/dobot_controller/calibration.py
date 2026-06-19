"""Pixel-to-Dobot calibration helpers.

Default homography is copied from the provided picking_dobot reference code and
must be recalibrated on the real camera/Dobot rig:
https://github.com/binedwin/pill-sorting-delivery/tree/main/src/picking_dobot/picking_dobot
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PixelToRobotCalibrator:
    homography: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]

    @classmethod
    def reference_default(cls) -> "PixelToRobotCalibrator":
        return cls(((0.061468, 0.724471, -76.627215), (0.624325, -0.172503, -317.373288), (0.000275, 0.001297, 1.0)))

    def pixel_to_robot(self, u: float, v: float) -> tuple[float, float]:
        h = self.homography
        x = h[0][0] * u + h[0][1] * v + h[0][2]
        y = h[1][0] * u + h[1][1] * v + h[1][2]
        w = h[2][0] * u + h[2][1] * v + h[2][2]
        if abs(w) < 1e-9:
            raise ZeroDivisionError("Invalid homography produced w=0")
        return x / w, y / w

    def batch_pixel_to_robot(self, pixels: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
        return [self.pixel_to_robot(u, v) for u, v in pixels]
