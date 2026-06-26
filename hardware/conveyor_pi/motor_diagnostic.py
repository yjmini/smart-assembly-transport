#!/usr/bin/env python3
"""Standalone motor diagnostics for the conveyor Raspberry Pi.

This script intentionally bypasses the full mission pipeline.  It is for proving
that the known-good 0520_conveyor wiring still drives the expected actuators:

- Servo signal: BCM 18
- Stepper DIR: BCM 17
- Stepper STEP: BCM 27
- Stepper ENABLE: BCM 22, active-low

Examples on the Pi:
    python3 motor_diagnostic.py servo
    python3 motor_diagnostic.py stepper --duration-sec 3
    python3 motor_diagnostic.py all
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

import gpiod


@dataclass(frozen=True)
class Pins:
    servo: int = 18
    stepper_dir: int = 17
    stepper_step: int = 27
    stepper_enable: int = 22


LEFT_ANGLE = 95
CENTER_ANGLE = 135
RIGHT_ANGLE = 175


class GpioLines:
    def __init__(self, pins: Pins) -> None:
        self.chip = gpiod.Chip("gpiochip0")
        self.servo = self.chip.get_line(pins.servo)
        self.direction = self.chip.get_line(pins.stepper_dir)
        self.step = self.chip.get_line(pins.stepper_step)
        self.enable = self.chip.get_line(pins.stepper_enable)
        self.servo.request(consumer="diag-servo", type=gpiod.LINE_REQ_DIR_OUT)
        self.direction.request(consumer="diag-dir", type=gpiod.LINE_REQ_DIR_OUT)
        self.step.request(consumer="diag-step", type=gpiod.LINE_REQ_DIR_OUT)
        self.enable.request(consumer="diag-enable", type=gpiod.LINE_REQ_DIR_OUT)
        self.disable_stepper()
        self.step.set_value(0)

    def enable_stepper(self) -> None:
        # Proven 0520_conveyor code used enable_line.set_value(0) to run.
        self.enable.set_value(0)

    def disable_stepper(self) -> None:
        # Proven 0520_conveyor code used enable_line.set_value(1) to stop.
        self.enable.set_value(1)

    def close(self) -> None:
        try:
            self.disable_stepper()
            self.step.set_value(0)
        finally:
            for line in (self.servo, self.direction, self.step, self.enable):
                try:
                    line.release()
                except Exception:  # noqa: BLE001 - cleanup best effort
                    pass
            close = getattr(self.chip, "close", None)
            if close:
                close()


def servo_pulse_width(angle: float) -> float:
    # Copied from proven 0520_conveyor code: 270-degree servo pulse mapping.
    return (angle / 270.0) * (0.0025 - 0.0005) + 0.0005


def set_servo(line, angle: float, *, pulses: int = 18) -> None:
    pulse_width = servo_pulse_width(angle)
    print(f"[servo] angle={angle} pulse_width={pulse_width:.6f}s pulses={pulses}", flush=True)
    for _ in range(pulses):
        line.set_value(1)
        time.sleep(pulse_width)
        line.set_value(0)
        time.sleep(max(0.0, 0.02 - pulse_width))


def run_servo(lines: GpioLines, *, cycles: int, hold_sec: float) -> None:
    print("[servo] start left/center/right diagnostic", flush=True)
    print(f"[servo] BCM pin=18, angles: left={LEFT_ANGLE}, center={CENTER_ANGLE}, right={RIGHT_ANGLE}", flush=True)
    set_servo(lines.servo, CENTER_ANGLE)
    time.sleep(hold_sec)
    for index in range(1, cycles + 1):
        print(f"[servo] cycle {index}/{cycles}: LEFT", flush=True)
        set_servo(lines.servo, LEFT_ANGLE)
        time.sleep(hold_sec)
        print(f"[servo] cycle {index}/{cycles}: RIGHT", flush=True)
        set_servo(lines.servo, RIGHT_ANGLE)
        time.sleep(hold_sec)
        print(f"[servo] cycle {index}/{cycles}: CENTER", flush=True)
        set_servo(lines.servo, CENTER_ANGLE)
        time.sleep(hold_sec)
    print("[servo] done", flush=True)


def pulse_stepper_for_duration(lines: GpioLines, *, direction_value: int, duration_sec: float, delay_sec: float) -> int:
    lines.direction.set_value(direction_value)
    lines.enable_stepper()
    start = time.monotonic()
    pulses = 0
    while time.monotonic() - start < duration_sec:
        lines.step.set_value(1)
        time.sleep(delay_sec)
        lines.step.set_value(0)
        time.sleep(delay_sec)
        pulses += 1
    lines.disable_stepper()
    return pulses


def run_stepper(lines: GpioLines, *, duration_sec: float, delay_sec: float, pause_sec: float) -> None:
    print("[stepper] start forward/reverse diagnostic", flush=True)
    print("[stepper] BCM pins: DIR=17, STEP=27, ENABLE=22(active-low)", flush=True)
    print(f"[stepper] each direction duration={duration_sec}s, half-pulse delay={delay_sec}s", flush=True)

    print("[stepper] FORWARD: dir=0, enable=0", flush=True)
    forward_pulses = pulse_stepper_for_duration(
        lines,
        direction_value=0,
        duration_sec=duration_sec,
        delay_sec=delay_sec,
    )
    print(f"[stepper] FORWARD complete, pulses={forward_pulses}", flush=True)
    time.sleep(pause_sec)

    print("[stepper] REVERSE: dir=1, enable=0", flush=True)
    reverse_pulses = pulse_stepper_for_duration(
        lines,
        direction_value=1,
        duration_sec=duration_sec,
        delay_sec=delay_sec,
    )
    print(f"[stepper] REVERSE complete, pulses={reverse_pulses}", flush=True)
    time.sleep(pause_sec)

    lines.disable_stepper()
    lines.step.set_value(0)
    print("[stepper] done; enable set to 1/off", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servo and stepper standalone diagnostics")
    parser.add_argument("mode", choices=["servo", "stepper", "all"], help="diagnostic to run")
    parser.add_argument("--servo-cycles", type=int, default=3, help="left/right servo repetitions")
    parser.add_argument("--hold-sec", type=float, default=0.8, help="pause between servo positions")
    parser.add_argument("--duration-sec", type=float, default=3.0, help="stepper run time per direction")
    parser.add_argument("--delay-sec", type=float, default=0.0002, help="stepper half-pulse delay")
    parser.add_argument("--pause-sec", type=float, default=1.0, help="pause between stepper directions")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lines = GpioLines(Pins())
    try:
        if args.mode in {"servo", "all"}:
            run_servo(lines, cycles=args.servo_cycles, hold_sec=args.hold_sec)
        if args.mode in {"stepper", "all"}:
            run_stepper(
                lines,
                duration_sec=args.duration_sec,
                delay_sec=args.delay_sec,
                pause_sec=args.pause_sec,
            )
    except KeyboardInterrupt:
        print("\n[diag] interrupted; disabling stepper and releasing GPIO", flush=True)
    finally:
        lines.close()
        print("[diag] cleanup complete", flush=True)


if __name__ == "__main__":
    main()

