"""Shared JSON/event helpers for WebSocket and ROS bridge code.

This module deliberately has no ROS dependency so it can be tested on a laptop
before hardware and a ROS 2 installation are available.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


class EventType(str, Enum):
    ORDER_CREATED = "order.created"
    CONVEYOR_STARTED = "conveyor.started"
    CONVEYOR_STOPPED = "conveyor.stopped"
    BASE_IN_POSITION = "vision.base_in_position"
    HAND_DETECTED = "safety.hand_detected"
    DASHBOARD_STOP = "safety.dashboard_stop"
    CRITICAL_ERROR = "safety.critical_error"
    ADMIN_UNLOCKED = "safety.admin_unlocked"
    ASSEMBLY_STAGE_1_DONE = "dobot.assembly_stage_1_done"
    ASSEMBLY_STAGE_2_DONE = "dobot.assembly_stage_2_done"
    QC_PASSED = "vision.qc_passed"
    QC_FAILED = "vision.qc_failed"
    LOADED_TO_TURTLEBOT = "dobot.loaded_to_turtlebot"
    DELIVERY_ARRIVED = "turtlebot.delivery_arrived"
    RETURN_REQUESTED = "turtlebot.return_requested"
    RETURN_ARRIVED = "turtlebot.return_arrived"


@dataclass(frozen=True)
class WorkOrder:
    command: str
    destination: str
    parts: list[str]
    order_id: str = field(default_factory=lambda: f"order-{uuid4().hex[:8]}")
    priority: str = "normal"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_order(command: str, destination: str, parts: list[str] | None = None, priority: str = "normal") -> WorkOrder:
    return WorkOrder(command=command, destination=destination, parts=parts or ["base", "top"], priority=priority)


def serialize_order(order: WorkOrder | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(order, WorkOrder):
        return asdict(order)
    return dict(order)


def make_state_event(state: Any, message: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state_name = getattr(state, "name", str(state))
    return {
        "type": "factory.state",
        "state": state_name,
        "message": message,
        "payload": dict(payload or {}),
        "timestamp": utc_now_iso(),
    }


def make_command_event(command: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "factory.command", "command": command, "payload": dict(payload or {}), "timestamp": utc_now_iso()}
