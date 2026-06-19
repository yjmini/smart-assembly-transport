# 13. 로컬 Mock 실행 가이드

하드웨어 없이 현재 작성된 코드를 검증하는 순서입니다.

## 1. 테스트 실행

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m pytest -q
```

## 2. mock 공정 흐름 실행

```bash
python3 -m sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.mock_runner
```

출력은 WebSocket으로 대시보드에 보낼 수 있는 `factory.state` JSON 이벤트 배열입니다.

## 3. WebSocket 서버 실행

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m server.app
```

클라이언트 메시지 예시:

```json
{"type":"order.create","command":"assemble and deliver","destination":"A","parts":["base","top"]}
```

## 4. ROS 2 workspace

워크스페이스 이름은 요청대로 `sem1_pjt_ws`입니다.

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
colcon build
source install/setup.bash
```

현재는 mock-first Python package scaffold이며, 실제 ROS node/action wiring은 하드웨어 연결 단계에서 동일 인터페이스로 확장합니다.
