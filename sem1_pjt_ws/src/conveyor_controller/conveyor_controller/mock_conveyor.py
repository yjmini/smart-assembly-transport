"""Mock conveyor controller used before real hardware is available."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConveyorState(str, Enum):
    STOPPED = "STOPPED"
    MOVING = "MOVING"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"


@dataclass
class MockConveyorController:
    state: ConveyorState = ConveyorState.STOPPED

    def start(self) -> ConveyorState:
        if self.state == ConveyorState.EMERGENCY_STOPPED:
            raise RuntimeError("Cannot start conveyor while emergency stopped")
        self.state = ConveyorState.MOVING
        return self.state

    def stop(self) -> ConveyorState:
        self.state = ConveyorState.STOPPED
        return self.state

    def emergency_stop(self) -> ConveyorState:
        self.state = ConveyorState.EMERGENCY_STOPPED
        return self.state

    def admin_unlock(self) -> ConveyorState:
        self.state = ConveyorState.STOPPED
        return self.state
