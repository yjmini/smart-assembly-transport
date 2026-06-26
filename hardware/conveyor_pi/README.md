# Conveyor Raspberry Pi Scripts

This folder keeps the standalone Raspberry Pi conveyor files that can be copied to the edge controller at `ssafy@192.168.110.142:~/smart-assembly-transport-edge/`.

## Files

- `conveyor_control.py` — conveyor control entrypoint supporting digital, stepper, and sorter actions.
- `motor_diagnostic.py` — standalone GPIO diagnostic for the known-good 0520 conveyor wiring.

## Example

```bash
python3 motor_diagnostic.py all
CONVEYOR_MODE=stepper python3 conveyor_control.py start
CONVEYOR_MODE=stepper python3 conveyor_control.py sort-left
CONVEYOR_MODE=stepper python3 conveyor_control.py sort-right
```
