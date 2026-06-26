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
- CONVEYOR_STOP_FILE: cooperative stop request path, default ~/.smart_assembly_conveyor_stop.json

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

Sorter servo mode:
- SORTER_SERVO_PIN: BCM PWM/control pin for the diverter servo, default 18
- SORTER_LEFT_PULSE_SEC: pulse width for normal/left sort, default 0.0010
- SORTER_RIGHT_PULSE_SEC: pulse width for abnormal/right sort, default 0.0020
- SORTER_NEUTRAL_PULSE_SEC: pulse width for neutral, default 0.0015
- SORTER_SERVO_HOLD_SEC: how long to hold each servo command, default 0.7
- SORTER_SERVO_PERIOD_SEC: software PWM period, default 0.02
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
STOP_FILE = Path(os.environ.get("CONVEYOR_STOP_FILE", str(Path.home() / ".smart_assembly_conveyor_stop.json")))

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

SORTER_SERVO_PIN = int(os.environ.get("SORTER_SERVO_PIN", "18"))
SORTER_LEFT_PULSE_SEC = max(0.0005, float(os.environ.get("SORTER_LEFT_PULSE_SEC", "0.0010")))
SORTER_RIGHT_PULSE_SEC = max(0.0005, float(os.environ.get("SORTER_RIGHT_PULSE_SEC", "0.0020")))
SORTER_NEUTRAL_PULSE_SEC = max(0.0005, float(os.environ.get("SORTER_NEUTRAL_PULSE_SEC", "0.0015")))
SORTER_SERVO_HOLD_SEC = max(0.0, float(os.environ.get("SORTER_SERVO_HOLD_SEC", "0.7")))
SORTER_SERVO_PERIOD_SEC = max(0.003, float(os.environ.get("SORTER_SERVO_PERIOD_SEC", "0.02")))


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


def request_stop(reason: str) -> None:
    STOP_FILE.write_text(
        json.dumps({"requested": True, "reason": reason, "updated_at": datetime.utcnow().isoformat() + "Z"}, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_stop_request() -> None:
    try:
        STOP_FILE.unlink()
    except FileNotFoundError:
        pass


def stop_requested() -> bool:
    return STOP_FILE.exists()


def stop_request_payload() -> dict[str, Any]:
    if not STOP_FILE.exists():
        return {}
    try:
        return json.loads(STOP_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - malformed stop file still means stop
        return {"requested": True, "reason": "malformed_stop_file"}


def close_devices(*devices: Any) -> None:
    for device in devices:
        close = getattr(device, "close", None)
        if close:
            close()


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


def _pulse_stepper(step_device, count: int, delay_sec: float) -> tuple[int, bool]:
    completed = 0
    for _ in range(count):
        if stop_requested():
            return completed, True
        step_device.on()
        time.sleep(delay_sec)
        step_device.off()
        completed += 1
        time.sleep(delay_sec)
    return completed, False


def _servo_device():
    return _output_device(SORTER_SERVO_PIN, active_high=True, initial_value=False)


def _drive_servo_pulse(servo_device, pulse_width_sec: float, hold_sec: float) -> None:
    if hold_sec <= 0:
        return
    low_time = max(0.0, SORTER_SERVO_PERIOD_SEC - pulse_width_sec)
    cycles = max(1, int(hold_sec / SORTER_SERVO_PERIOD_SEC))
    for _ in range(cycles):
        servo_device.on()
        time.sleep(pulse_width_sec)
        servo_device.off()
        time.sleep(low_time)


def _pulse_stepper_holding_servo(
    step_device,
    servo_device,
    hold_pulse_sec: float,
    count: int,
    delay_sec: float,
) -> tuple[int, bool]:
    """Run the conveyor stepper while keeping the sorter flap engaged.

    The diverter servo is refreshed with a short pulse roughly every servo PWM
    period so it physically holds the sort position for the *entire* belt
    movement instead of drifting back as soon as the initial pulse train ends.
    Returns (completed_steps, stopped_by_request)."""
    low_time = max(0.0, SORTER_SERVO_PERIOD_SEC - hold_pulse_sec)
    step_period = max(delay_sec * 2.0, 1e-9)
    refresh_every = max(1, int(SORTER_SERVO_PERIOD_SEC / step_period))
    completed = 0
    for index in range(count):
        if stop_requested():
            return completed, True
        if servo_device is not None and index % refresh_every == 0:
            servo_device.on()
            time.sleep(hold_pulse_sec)
            servo_device.off()
            time.sleep(low_time)
        step_device.on()
        time.sleep(delay_sec)
        step_device.off()
        completed += 1
        time.sleep(delay_sec)
    return completed, False


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
    if action in {"stop", "emergency-stop"}:
        request_stop(action)

    devices = _stepper_devices()
    gpio_available = devices is not None
    common = {
        "step_pin": STEP_PIN,
        "dir_pin": DIR_PIN,
        "enable_pin": ENABLE_PIN,
        "steps": STEPS,
        "step_delay_sec": STEP_DELAY_SEC,
        "direction": DIRECTION,
        "sorter_servo_pin": SORTER_SERVO_PIN,
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
    try:
        if action in {"start", "sort-left", "sort-right"}:
            clear_stop_request()
            sort_direction = None
            sorter_gpio_available = False
            servo = None
            hold_pulse = None
            if action in {"sort-left", "sort-right"}:
                sort_direction = "left" if action == "sort-left" else "right"
                servo = _servo_device()
                sorter_gpio_available = servo is not None
                if servo is not None:
                    hold_pulse = SORTER_LEFT_PULSE_SEC if sort_direction == "left" else SORTER_RIGHT_PULSE_SEC
                    # Drive the flap to the sort position and let it settle there
                    # before the belt starts moving.
                    _drive_servo_pulse(servo, hold_pulse, SORTER_SERVO_HOLD_SEC)
            _set_forward_direction(direction)
            enable.on()
            if servo is not None:
                # Keep the flap engaged for the whole belt run.
                completed_steps, stopped_by_request = _pulse_stepper_holding_servo(
                    step, servo, hold_pulse, STEPS, STEP_DELAY_SEC
                )
            else:
                completed_steps, stopped_by_request = _pulse_stepper(step, STEPS, STEP_DELAY_SEC)
            enable.off()
            step.off()
            if servo is not None:
                # Belt finished: return the flap to neutral, then release the servo.
                _drive_servo_pulse(servo, SORTER_NEUTRAL_PULSE_SEC, SORTER_SERVO_HOLD_SEC)
                servo.off()
                close_devices(servo)
            if stopped_by_request:
                request = stop_request_payload()
                return write_state(
                    "STOPPED_BY_REQUEST",
                    True,
                    **common,
                    completed_steps=completed_steps,
                    stop_reason=request.get("reason", "stop"),
                    stop_file=str(STOP_FILE),
                    sort_direction=sort_direction,
                    sorter_gpio_available=sorter_gpio_available,
                )
            if sort_direction:
                return write_state(
                    "SORTED_LEFT" if sort_direction == "left" else "SORTED_RIGHT",
                    True,
                    **common,
                    completed_steps=completed_steps,
                    stop_file=str(STOP_FILE),
                    sort_direction=sort_direction,
                    sorter_gpio_available=sorter_gpio_available,
                )
            return write_state("MOVED", True, **common, completed_steps=completed_steps, stop_file=str(STOP_FILE))
        if action == "stop":
            enable.off()
            step.off()
            return write_state("STOPPED", True, **common, stop_file=str(STOP_FILE))
        if action == "emergency-stop":
            enable.off()
            step.off()
            return write_state("EMERGENCY_STOPPED", True, **common, stop_file=str(STOP_FILE))
        raise ValueError(f"Unsupported action: {action}")
    finally:
        close_devices(step, direction, enable)


def run_action(action: str) -> dict[str, Any]:
    if MODE == "stepper":
        return run_stepper_action(action)
    if MODE == "digital":
        return run_digital_action(action)
    return write_state("ERROR", False, error=f"Unsupported CONVEYOR_MODE={MODE!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "sort-left", "sort-right", "stop", "emergency-stop", "status"])
    args = parser.parse_args()
    print(json.dumps(run_action(args.action), ensure_ascii=False))


if __name__ == "__main__":
    main()

