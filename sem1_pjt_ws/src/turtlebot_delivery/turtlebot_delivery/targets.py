"""Delivery target configuration for TurtleBot/Nav2 mock and real nodes."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryTarget:
    name: str
    x: float
    y: float
    yaw: float


DEFAULT_TARGETS = {
    "A": DeliveryTarget("A", x=1.2, y=0.0, yaw=0.0),
    "B": DeliveryTarget("B", x=0.0, y=1.2, yaw=1.5708),
}


def get_target(name: str) -> DeliveryTarget:
    try:
        return DEFAULT_TARGETS[name.upper()]
    except KeyError as exc:
        raise ValueError(f"Unknown delivery target {name!r}; expected one of {sorted(DEFAULT_TARGETS)}") from exc
