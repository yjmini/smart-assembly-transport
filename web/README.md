# Web Dashboard Placeholder

Local WebSocket dashboard will connect to `ws://127.0.0.1:8765` and send:

```json
{"type":"order.create","command":"assemble and deliver","destination":"A","parts":["base","top"]}
```

Hardware-free MVP uses `server/app.py` and `mission_orchestrator/mock_runner.py` first.
