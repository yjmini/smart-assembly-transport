#!/usr/bin/env python3
"""Raspberry Pi conveyor control entrypoint.

Install on `ssafy@192.168.110.142:~/smart-assembly-transport-edge/`.

The original implementation was a single digital output, which is only suitable
for a relay/DC motor enable line.  The real conveyor can also be driven like the
project_pill conveyor concept: command a positive belt motion for a deterministic
amount of movement, then stop.  For physical hardware that maps to a stepper
motor driver by pulsing STEP while DIR/ENABLE are held in the requested state.

Configure with environment variables:

Common:
- CONVEYOR_MODE: digital or stepper, default digital
- CONVEYOR_STATE_FILE: state JSON path, default ~/.smart_assembly_conveyor_state.json

Digital mode:
- CONVEYOR_MOTOR_PIN: BCM pin for relay/motor enable, default 18
- CONVEYOR_ACTIVE_HIGH: 1 for active-high relay, 0 for active-low, default 1

Stepper mode:
- CONVEYOR_STEP_PIN: BCM STEP/PUL pin, default 27 (proven 0520_conveyor wiring)
- CONVEYOR_DIR_PIN: BCM DIR pin, default 17 (proven 0520_conveyor wiring)
- CONVEYOR_ENABLE_PIN: BCM ENA pin, default 22 (proven 0520_conveyor wiring)
- CONVEYOR_STEPS: number of pulses for one start command, default 800
- CONVEYOR_STEP_DELAY_SEC: high/low delay per half pulse, default 0.0001
- CONVEYOR_DIRECTION: forward or reverse, default forward
- CONVEYOR_ENABLE_ACTIVE_HIGH: 1 if ENA is active-high, 0 if active-low, default 0
- CONVEYOR_DIR_ACTIVE_HIGH: output level for forward direction, default 0
- CONVEYOR_GPIO_BACKEND: auto, gpiod, or gpiozero, default auto
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Any

MODE = os.environ.get("CONVEYOR_MODE", "digital").strip().lower()
STATE_FILE = Path(os.environ.get("CONVEYOR_STATE_FILE", str(Path.home() / ".smart_assembly_conveyor_state.json")))

MOTOR_PIN = int(os.environ.get("CONVEYOR_MOTOR_PIN", "18"))
ACTIVE_HIGH = os.environ.get("CONVEYOR_ACTIVE_HIGH", "1") != "0"

STEP_PIN = int(os.environ.get("CONVEYOR_STEP_PIN", "27"))
DIR_PIN = int(os.environ.get("CONVEYOR_DIR_PIN", "17"))
ENABLE_PIN = int(os.environ.get("CONVEYOR_ENABLE_PIN", "22"))
STEPS = max(0, int(os.environ.get("CONVEYOR_STEPS", "800")))
STEP_DELAY_SEC = max(0.0, float(os.environ.get("CONVEYOR_STEP_DELAY_SEC", "0.0001")))
DIRECTION = os.environ.get("CONVEYOR_DIRECTION", "forward").strip().lower()
ENABLE_ACTIVE_HIGH = os.environ.get("CONVEYOR_ENABLE_ACTIVE_HIGH", "0") != "0"
DIR_ACTIVE_HIGH = os.environ.get("CONVEYOR_DIR_ACTIVE_HIGH", "0") != "0"
GPIO_BACKEND = os.environ.get("CONVEYOR_GPIO_BACKEND", "auto").strip().lower()


class GpiodOutputDevice:
    def __init__(self, pin: int, *, active_high: bool = True, initial_value: bool = False):
        import gpiod

        self.pin = pin
        self.active_high = active_high
        self.chip = gpiod.Chip("gpiochip0")
        self.line = self.chip.get_line(pin)
        self.line.request(consumer=f"conveyor-{pin}", type=gpiod.LINE_REQ_DIR_OUT)
        self.set_value(initial_value)

    def set_value(self, logical_value: bool) -> None:
        physical_value = bool(logical_value) if self.active_high else not bool(logical_value)
        self.line.set_value(1 if physical_value else 0)

    def on(self) -> None:
        self.set_value(True)

    def off(self) -> None:
        self.set_value(False)

    def close(self) -> None:
        self.line.release()
        close = getattr(self.chip, "close", None)
        if close:
            close()


def _gpiozero_output_device(pin: int, *, active_high: bool = True, initial_value: bool = False):
    from gpiozero import DigitalOutputDevice

    return DigitalOutputDevice(pin, active_high=active_high, initial_value=initial_value)


def _output_device(pin: int, *, active_high: bool = True, initial_value: bool = False):
    backends = [GPIO_BACKEND] if GPIO_BACKEND in {"gpiod", "gpiozero"} else ["gpiod", "gpiozero"]
    for backend in backends:
        try:
            if backend == "gpiod":
                return GpiodOutputDevice(pin, active_high=active_high, initial_value=initial_value)
            if backend == "gpiozero":
                return _gpiozero_output_device(pin, active_high=active_high, initial_value=initial_value)
        except Exception:  # noqa: BLE001 - try fallback or report gpio_available=false
            continue
    return None


def _digital_motor():
    return _output_device(MOTOR_PIN, active_high=ACTIVE_HIGH, initial_value=False)


def _stepper_devices() -> tuple[Any, Any, Any] | None:
    step = _output_device(STEP_PIN, active_high=True, initial_value=False)
    direction = _output_device(DIR_PIN, active_high=True, initial_value=False)
    enable = _output_device(ENABLE_PIN, active_high=ENABLE_ACTIVE_HIGH, initial_value=False)
    if not step or not direction or not enable:
        for device in (step, direction, enable):
            if device:
                device.off()
        return None
    return step, direction, enable


def state_payload(state: str, gpio_available: bool, **extra: Any) -> dict[str, Any]:
    payload = {
        "state": state,
        "gpio_available": gpio_available,
        "mode": MODE,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "state_file": str(STATE_FILE),
    }
    payload.update(extra)
    return payload


def write_state(state: str, gpio_available: bool, **extra: Any) -> dict[str, Any]:
    payload = state_payload(state, gpio_available, **extra)
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        if MODE == "stepper":
            return state_payload(
                "UNKNOWN",
                False,
                step_pin=STEP_PIN,
                dir_pin=DIR_PIN,
                enable_pin=ENABLE_PIN,
                steps=STEPS,
                step_delay_sec=STEP_DELAY_SEC,
                direction=DIRECTION,
            )
        return state_payload("UNKNOWN", False, pin=MOTOR_PIN)
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if MODE == "stepper":
        current_config = {
            "step_pin": STEP_PIN,
            "dir_pin": DIR_PIN,
            "enable_pin": ENABLE_PIN,
            "steps": STEPS,
            "step_delay_sec": STEP_DELAY_SEC,
            "direction": DIRECTION,
        }
        if data.get("mode") == MODE and all(data.get(key) == value for key, value in current_config.items()):
            return data
        return state_payload(
            data.get("state", "UNKNOWN"),
            False,
            previous_mode=data.get("mode"),
            previous_step_pin=data.get("step_pin"),
            previous_dir_pin=data.get("dir_pin"),
            previous_enable_pin=data.get("enable_pin"),
            **current_config,
        )
    if data.get("mode") == MODE and data.get("pin") == MOTOR_PIN:
        return data
    return state_payload(data.get("state", "UNKNOWN"), False, previous_mode=data.get("mode"), pin=MOTOR_PIN)


def _set_forward_direction(direction_device) -> None:
    forward_level = DIR_ACTIVE_HIGH if DIRECTION != "reverse" else not DIR_ACTIVE_HIGH
    if forward_level:
        direction_device.on()
    else:
        direction_device.off()


def _pulse_stepper(step_device, count: int, delay_sec: float) -> None:
    for _ in range(count):
        step_device.on()
        time.sleep(delay_sec)
        step_device.off()
        time.sleep(delay_sec)


def run_digital_action(action: str) -> dict[str, Any]:
    motor = _digital_motor()
    gpio_available = motor is not None
    if action == "start":
        if motor:
            motor.on()
        return write_state("MOVING", gpio_available, pin=MOTOR_PIN)
    if action == "stop":
        if motor:
            motor.off()
        return write_state("STOPPED", gpio_available, pin=MOTOR_PIN)
    if action == "emergency-stop":
        if motor:
            motor.off()
        return write_state("EMERGENCY_STOPPED", gpio_available, pin=MOTOR_PIN)
    return read_state()


def run_stepper_action(action: str) -> dict[str, Any]:
    devices = _stepper_devices()
    gpio_available = devices is not None
    common = {
        "step_pin": STEP_PIN,
        "dir_pin": DIR_PIN,
        "enable_pin": ENABLE_PIN,
        "steps": STEPS,
        "step_delay_sec": STEP_DELAY_SEC,
        "direction": DIRECTION,
    }

    if action == "status":
        status = read_state()
        status["gpio_available"] = gpio_available
        return status

    if not devices:
        state = "GPIO_UNAVAILABLE" if action == "start" else "STOPPED"
        if action == "emergency-stop":
            state = "EMERGENCY_STOPPED"
        return write_state(state, False, **common)

    step, direction, enable = devices
    if action == "start":
        _set_forward_direction(direction)
        enable.on()
        _pulse_stepper(step, STEPS, STEP_DELAY_SEC)
        enable.off()
        return write_state("MOVED", True, **common)
    if action == "stop":
        enable.off()
        return write_state("STOPPED", True, **common)
    if action == "emergency-stop":
        enable.off()
        step.off()
        return write_state("EMERGENCY_STOPPED", True, **common)
    raise ValueError(f"Unsupported action: {action}")


def run_action(action: str) -> dict[str, Any]:
    if MODE == "stepper":
        return run_stepper_action(action)
    if MODE == "digital":
        return run_digital_action(action)
    return write_state("ERROR", False, error=f"Unsupported CONVEYOR_MODE={MODE!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "emergency-stop", "status"])
    args = parser.parse_args()
    print(json.dumps(run_action(args.action), ensure_ascii=False))


if __name__ == "__main__":
    main()
