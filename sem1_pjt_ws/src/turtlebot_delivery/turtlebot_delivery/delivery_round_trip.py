"""CLI entry point for TurtleBot Nav2 delivery round trips.

Default mode is a dry-run that prints the exact SSH/ROS commands. Pass
``--execute`` only after the TurtleBot has localization/Nav2 running on the
configured map and the path is physically safe.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

try:
    from hri_interfaces.hardware_config import DEFAULT_CONFIG_PATH, HardwareConfig
    from turtlebot_delivery.real_turtlebot import RealTurtleBotDelivery
except ImportError:
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import DEFAULT_CONFIG_PATH, HardwareConfig
    from sem1_pjt_ws.src.turtlebot_delivery.turtlebot_delivery.real_turtlebot import RealTurtleBotDelivery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Navigate TurtleBot to a map destination, dwell, then return HOME via Nav2.")
    parser.add_argument("destination", nargs="?", default="A", help="Configured destination key in config/hardware.json, e.g. A or B")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to hardware.json")
    parser.add_argument("--dwell-sec", type=float, default=None, help="Seconds to wait at destination before returning home; default from config")
    parser.add_argument("--execute", action="store_true", help="Actually SSH to the TurtleBot and run Nav2 commands. Omit for dry-run.")
    parser.add_argument(
        "--single-command",
        action="store_true",
        help="Emit/run one chained SSH command: navigate -> sleep -> return. Default emits/runs separate steps for clearer status.",
    )
    return parser


def run_delivery_round_trip(args: argparse.Namespace) -> dict[str, Any]:
    config = HardwareConfig.load(Path(args.config))
    dwell_sec = config.turtlebot.delivery_dwell_sec if args.dwell_sec is None else args.dwell_sec
    turtlebot = RealTurtleBotDelivery(config.turtlebot, execute=args.execute)

    if args.single_command:
        result = turtlebot.delivery_round_trip(args.destination, dwell_sec)
        steps = [{"step": "round_trip", **asdict(result)}]
    else:
        steps = [
            {"step": f"navigate_{args.destination}", **asdict(turtlebot.navigate(args.destination))},
            {"step": f"wait_{dwell_sec:g}s", **asdict(turtlebot.wait_at_destination(dwell_sec))},
            {"step": f"return_{config.turtlebot.home_destination}", **asdict(turtlebot.return_home())},
        ]

    return {
        "type": "turtlebot.delivery_round_trip.result",
        "execute": args.execute,
        "destination": args.destination,
        "home_destination": config.turtlebot.home_destination,
        "dwell_sec": dwell_sec,
        "steps": steps,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = run_delivery_round_trip(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all(step["returncode"] == 0 for step in payload["steps"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
