#!/usr/bin/env python3
"""Send an STT-style TurtleBot navigation command through the dashboard backend.

Usage examples:

    # Safe dry-run: verifies WebSocket/STT parsing and prints the SSH/Nav2 command
    python3 scripts/test_stt_turtlebot_navigation.py --destination A

    # Real robot test: sends the Nav2 goal to the TurtleBot over SSH
    python3 scripts/test_stt_turtlebot_navigation.py --destination B --execute

Prerequisites for --execute:
- server is running: python3 -m server.app
- TurtleBot bringup and navigation2 are running
- SSH target from config/hardware.json is reachable
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test STT -> TurtleBot Nav2 command through server.app WebSocket")
    parser.add_argument("--url", default="ws://127.0.0.1:8765", help="server.app WebSocket URL")
    parser.add_argument("--destination", choices=["A", "B", "HOME"], default="A", help="TurtleBot target from config/hardware.json")
    parser.add_argument("--text", default=None, help="Override STT transcript text")
    parser.add_argument("--execute", action="store_true", help="Actually execute the SSH/ROS Nav2 command on the TurtleBot")
    parser.add_argument("--timeout", type=float, default=180.0, help="Seconds to wait for command_result")
    return parser


def transcript_for(destination: str) -> str:
    if destination == "HOME":
        return "홈 위치로 복귀"
    return f"{destination}구역으로 이동"


async def run_probe(args: argparse.Namespace) -> int:
    if websockets is None:
        raise RuntimeError("Install websockets first: python3 -m pip install websockets")

    message = {
        "type": "speech.stt.final",
        "transcript": args.text or transcript_for(args.destination),
        "destination": args.destination,
        "execute": args.execute,
    }

    print(f"[stt-turtlebot-test] connecting {args.url}")
    print(f"[stt-turtlebot-test] sending: {json.dumps(message, ensure_ascii=False)}")
    if args.execute:
        print("[stt-turtlebot-test] REAL EXECUTION ENABLED: TurtleBot Nav2 goal will be sent over SSH")
    else:
        print("[stt-turtlebot-test] dry-run mode: command will be printed but not executed")

    async with websockets.connect(args.url) as ws:
        await ws.send(json.dumps(message, ensure_ascii=False))
        seen: list[dict[str, Any]] = []
        deadline = asyncio.get_running_loop().time() + args.timeout
        while asyncio.get_running_loop().time() < deadline:
            remaining = max(0.1, deadline - asyncio.get_running_loop().time())
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            payload = json.loads(raw)
            seen.append(payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))

            if payload.get("type") == "factory.error":
                print(f"[stt-turtlebot-test] ERROR from server: {payload.get('message')}", file=sys.stderr)
                return 2

            if payload.get("type") == "hardware.command_result" and payload.get("subsystem") == "turtlebot":
                if payload.get("returncode", 0) not in (0, None):
                    print(f"[stt-turtlebot-test] TurtleBot command failed: rc={payload.get('returncode')}", file=sys.stderr)
                    return int(payload.get("returncode") or 1)
                print("[stt-turtlebot-test] TurtleBot command result received successfully")
                return 0

        print(f"[stt-turtlebot-test] timed out after {args.timeout}s without turtlebot command_result", file=sys.stderr)
        print(f"[stt-turtlebot-test] received {len(seen)} messages", file=sys.stderr)
        return 124


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run_probe(args)))


if __name__ == "__main__":
    main()
