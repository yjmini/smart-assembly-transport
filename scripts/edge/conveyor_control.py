#!/usr/bin/env python3
"""Raspberry Pi conveyor control entrypoint.

Install on `ssafy@192.168.110.142:~/smart-assembly-transport-edge/`.
It uses gpiozero when available and falls back to state-file-only mode on dev
machines.  Configure pins via environment variables:

- CONVEYOR_MOTOR_PIN: BCM pin for relay/motor enable, default 18
- CONVEYOR_ACTIVE_HIGH: 1 for active-high relay, 0 for active-low, default 1
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime

STATE_FILE = Path.home() / ".smart_assembly_conveyor_state.json"
MOTOR_PIN = int(os.environ.get("CONVEYOR_MOTOR_PIN", "18"))
ACTIVE_HIGH = os.environ.get("CONVEYOR_ACTIVE_HIGH", "1") != "0"


def _motor():
    try:
        from gpiozero import DigitalOutputDevice
        return DigitalOutputDevice(MOTOR_PIN, active_high=ACTIVE_HIGH, initial_value=False)
    except Exception as exc:  # noqa: BLE001 - development fallback
        return None


def write_state(state: str, gpio_available: bool) -> None:
    STATE_FILE.write_text(json.dumps({"state": state, "gpio_available": gpio_available, "pin": MOTOR_PIN, "updated_at": datetime.utcnow().isoformat() + "Z"}), encoding="utf-8")


def read_state() -> dict:
    if not STATE_FILE.exists():
        return {"state": "UNKNOWN", "gpio_available": False, "pin": MOTOR_PIN}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "emergency-stop", "status"])
    args = parser.parse_args()
    motor = _motor()
    gpio_available = motor is not None
    if args.action == "start":
        if motor: motor.on()
        write_state("MOVING", gpio_available)
    elif args.action == "stop":
        if motor: motor.off()
        write_state("STOPPED", gpio_available)
    elif args.action == "emergency-stop":
        if motor: motor.off()
        write_state("EMERGENCY_STOPPED", gpio_available)
    print(json.dumps(read_state(), ensure_ascii=False))


if __name__ == "__main__":
    main()
