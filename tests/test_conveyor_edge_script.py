import importlib.util
import json
import sys
import types
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "edge" / "conveyor_control.py"


class FakeOutputDevice:
    events = []

    def __init__(self, pin, active_high=True, initial_value=False):
        self.pin = pin
        self.active_high = active_high
        self.value = initial_value
        FakeOutputDevice.events.append(("init", pin, active_high, initial_value))

    def on(self):
        self.value = True
        FakeOutputDevice.events.append(("on", self.pin))

    def off(self):
        self.value = False
        FakeOutputDevice.events.append(("off", self.pin))


class FakeSleep:
    calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


def load_edge_module(monkeypatch, tmp_path, env=None):
    FakeOutputDevice.events = []
    fake_gpiozero = types.ModuleType("gpiozero")
    fake_gpiozero.DigitalOutputDevice = FakeOutputDevice
    monkeypatch.setitem(sys.modules, "gpiozero", fake_gpiozero)
    monkeypatch.setenv("CONVEYOR_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv("CONVEYOR_STOP_FILE", str(tmp_path / "stop.json"))
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, str(value))

    spec = importlib.util.spec_from_file_location("edge_conveyor_control_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sleeper = FakeSleep()
    monkeypatch.setattr(module.time, "sleep", sleeper)
    return module, sleeper


def test_stepper_start_pulses_step_pin_and_records_configuration(monkeypatch, tmp_path):
    module, sleeper = load_edge_module(
        monkeypatch,
        tmp_path,
        {
            "CONVEYOR_MODE": "stepper",
            "CONVEYOR_STEP_PIN": 20,
            "CONVEYOR_DIR_PIN": 21,
            "CONVEYOR_ENABLE_PIN": 16,
            "CONVEYOR_STEPS": 3,
            "CONVEYOR_STEP_DELAY_SEC": "0.0005",
        },
    )

    result = module.run_action("start")

    assert result["state"] == "MOVED"
    assert result["gpio_available"] is True
    assert result["mode"] == "stepper"
    assert result["step_pin"] == 20
    assert result["dir_pin"] == 21
    assert result["enable_pin"] == 16
    assert result["steps"] == 3
    assert FakeOutputDevice.events.count(("on", 20)) == 3
    assert FakeOutputDevice.events.count(("off", 20)) >= 3
    assert ("off", 21) in FakeOutputDevice.events
    assert ("on", 16) in FakeOutputDevice.events
    assert ("off", 16) in FakeOutputDevice.events
    assert sleeper.calls == [0.0005] * 6


def test_stepper_start_stops_early_when_stop_file_is_requested(monkeypatch, tmp_path):
    module, _ = load_edge_module(
        monkeypatch,
        tmp_path,
        {
            "CONVEYOR_MODE": "stepper",
            "CONVEYOR_STEP_PIN": 20,
            "CONVEYOR_DIR_PIN": 21,
            "CONVEYOR_ENABLE_PIN": 16,
            "CONVEYOR_STEPS": 100,
            "CONVEYOR_STEP_DELAY_SEC": "0.0005",
        },
    )
    calls = []

    def request_stop_after_first_pulse(seconds):
        calls.append(seconds)
        if len(calls) == 2:
            module.request_stop("stop")

    monkeypatch.setattr(module.time, "sleep", request_stop_after_first_pulse)

    result = module.run_action("start")

    assert result["state"] == "STOPPED_BY_REQUEST"
    assert result["completed_steps"] < 100
    assert result["stop_reason"] == "stop"
    assert ("off", 16) in FakeOutputDevice.events


def test_stepper_stop_and_emergency_stop_disable_enable_pin(monkeypatch, tmp_path):
    module, _ = load_edge_module(
        monkeypatch,
        tmp_path,
        {
            "CONVEYOR_MODE": "stepper",
            "CONVEYOR_STEP_PIN": 20,
            "CONVEYOR_DIR_PIN": 21,
            "CONVEYOR_ENABLE_PIN": 16,
        },
    )

    stop = module.run_action("stop")
    emergency = module.run_action("emergency-stop")

    assert stop["state"] == "STOPPED"
    assert emergency["state"] == "EMERGENCY_STOPPED"
    assert FakeOutputDevice.events.count(("off", 16)) == 2


def test_status_reads_previous_stepper_state(monkeypatch, tmp_path):
    module, _ = load_edge_module(
        monkeypatch,
        tmp_path,
        {
            "CONVEYOR_MODE": "stepper",
            "CONVEYOR_STEP_PIN": 20,
            "CONVEYOR_DIR_PIN": 21,
            "CONVEYOR_ENABLE_PIN": 16,
            "CONVEYOR_STEPS": 2,
        },
    )

    moved = module.run_action("start")
    status = module.run_action("status")

    assert status == json.loads(Path(moved["state_file"]).read_text(encoding="utf-8"))
    assert status["state"] == "MOVED"
    assert status["mode"] == "stepper"


def test_stepper_sort_left_positions_servo_then_moves_longer(monkeypatch, tmp_path):
    module, sleeper = load_edge_module(
        monkeypatch,
        tmp_path,
        {
            "CONVEYOR_MODE": "stepper",
            "CONVEYOR_STEP_PIN": 20,
            "CONVEYOR_DIR_PIN": 21,
            "CONVEYOR_ENABLE_PIN": 16,
            "CONVEYOR_STEPS": 4,
            "CONVEYOR_STEP_DELAY_SEC": "0.0005",
            "SORTER_SERVO_PIN": 18,
            "SORTER_SERVO_HOLD_SEC": "0.04",
            "SORTER_SERVO_PERIOD_SEC": "0.0005",
        },
    )

    result = module.run_action("sort-left")

    assert result["state"] == "SORTED_LEFT"
    assert result["sort_direction"] == "left"
    assert result["completed_steps"] == 4
    assert result["sorter_servo_pin"] == 18
    # A single servo device is opened for the whole sort operation: it positions
    # the flap, holds it during the belt run, then returns it to neutral.
    assert FakeOutputDevice.events.count(("init", 18, True, False)) == 1
    assert ("on", 18) in FakeOutputDevice.events
    assert ("off", 18) in FakeOutputDevice.events
    assert FakeOutputDevice.events.count(("on", 20)) == 4
    # The servo is refreshed at least once while the belt is still moving so the
    # flap stays engaged for the entire run (not just before it starts).
    last_step_on = len(FakeOutputDevice.events) - 1 - FakeOutputDevice.events[::-1].index(("on", 20))
    first_step_on = FakeOutputDevice.events.index(("on", 20))
    servo_ons_during_run = [
        i for i, ev in enumerate(FakeOutputDevice.events)
        if ev == ("on", 18) and first_step_on <= i <= last_step_on
    ]
    assert servo_ons_during_run
    assert 0.001 in sleeper.calls
    assert 0.0015 in sleeper.calls
