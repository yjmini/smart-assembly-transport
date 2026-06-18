# 자동 조립 공정 및 무인 배송 시스템

자동 조립 공정 및 무인 배송 시스템은 음성 명령을 기반으로 컨베이어, 비전, 로봇팔, 모바일 로봇을 연동하여 제품 조립부터 목적지 배송까지의 스마트팩토리 공정을 구현하기 위한 프로젝트입니다.

## Structure

```text
server/             Backend API and WebSocket server for order/status events
web/                Dashboard for process monitoring and emergency recovery
ros2_ws/            ROS 2 workspace for orchestration and robot integration
  src/
    mission_orchestrator/   Process FSM and subsystem coordination
    vision_detector/        YOLO/OpenCV based object, hand, and QC detection
    conveyor_controller/    Conveyor start/stop control node
    dobot_controller/       Dobot assembly and loading control node
    turtlebot_delivery/     TurtleBot Nav2 delivery goal node
    hri_interfaces/         STT/TTS and dashboard bridge interfaces
docs/               Architecture, WBS, and project planning documents
sample-data/        Sample images, videos, maps, and test inputs
```

## Workflow

```text
Voice command
  → STT order creation
  → Dashboard / backend order registration
  → ROS 2 mission orchestration
  → Conveyor transport
  → Vision-based base-part detection
  → Dobot assembly
  → Vision QC
  → Dobot loading to TurtleBot
  → TurtleBot autonomous delivery
  → TTS and dashboard completion report
```

## Core Features

- 작업자 음성 명령 기반 작업 오더 생성
- 컨베이어 위 부품 감지 및 정위치 정지
- 사람 손 감지 시 비상 정지 및 관리자 비밀번호 기반 복구
- Dobot 로봇팔 기반 다단계 조립 및 적재
- YOLO/OpenCV 기반 부품 인식과 품질 검사
- TurtleBot3 SLAM/Nav2 기반 목적지 배송
- WebSocket 기반 실시간 공정 상태 모니터링
- TTS 기반 작업 완료 안내

## Quick Start

### 1. ROS 2 Workspace

```bash
cd ros2_ws
colcon build
source install/setup.bash
ros2 launch mission_orchestrator mock_demo.launch.py
```

### 2. Backend Server

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

### 3. Web Dashboard

```bash
cd web
npm install
npm run dev -- --host 0.0.0.0
```

Open:

```text
http://localhost:5173
```

## Development Direction

- `ros2_ws/src/mission_orchestrator` defines the process FSM and should remain the center of integration.
- Hardware nodes should expose the same interface in mock and real modes so the demo can fall back safely when equipment is unavailable.
- Safety handling has priority over throughput: emergency stop must interrupt conveyor, Dobot, and delivery actions immediately.
- Vision, conveyor, Dobot, TurtleBot, backend, and dashboard modules should be developed independently and integrated through documented ROS 2 and WebSocket interfaces.

## Documents

- [Architecture](docs/ARCHITECTURE.md)
- [Week 1 Plan](docs/WEEK1_PLAN.md)
- [WBS / Kanban](docs/WBS.md)
