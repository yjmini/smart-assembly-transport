# 자동 조립 공정 및 무인 배송 시스템

음성 명령을 시작점으로 컨베이어, 비전, Dobot 로봇팔, TurtleBot, 웹 대시보드를 연결해 **제품 조립 → 품질 확인 → 무인 배송** 흐름을 수행하는 스마트팩토리 통합 프로젝트입니다.

## 프로젝트 개요

이 프로젝트는 단일 로봇 제어보다 여러 모듈을 하나의 공정 상태로 묶는 데 초점을 둡니다. ROS 2 기반 공정 FSM, Django/Vue 대시보드, WebSocket bridge, Raspberry Pi conveyor script, Dobot/TurtleBot 제어 패키지를 함께 구성했습니다.

## 핵심 시나리오

```text
작업자 음성 명령
  → 작업 오더 생성
  → 컨베이어 구동
  → 비전 기반 베이스 부품 정위치 감지
  → Dobot 로봇팔 조립
  → 비전 기반 품질 확인
  → TurtleBot 적재 및 목적지 배송
  → TTS / 대시보드 완료 보고
```

## 주요 기능

- STT 기반 작업 명령 입력과 작업 오더 생성
- 컨베이어 구동, 정지, 분류 명령 처리
- YOLO/OpenCV 기반 부품·손·완성품 인식 흐름
- 손 감지 시 비상 정지 및 관리자 승인 후 복구
- Dobot 조립 및 TurtleBot 배송 단계 제어
- Django API + Vue 대시보드 기반 상태 모니터링
- WebSocket bridge 기반 공정 이벤트 전달
- 실제 장비 전환 전 로컬 mock runner와 테스트 코드 제공

## 기술 스택

- **Robotics**: ROS 2, rclpy, TurtleBot3/Nav2, Dobot
- **Vision**: OpenCV, YOLO-style detector interface
- **Backend**: Django, Python WebSocket server
- **Frontend**: Vue, Chart.js
- **Edge**: Raspberry Pi conveyor scripts
- **Test**: pytest, mock scenario runner

## Repository Structure

```text
.
├── server/                 # WebSocket bridge 및 공정 이벤트 서버
├── dashboard_backend/      # Django API, order/event/detection 모델
├── web/                    # Vue 대시보드
├── sem1_pjt_ws/            # ROS 2 공정 제어 workspace
│   └── src/
│       ├── mission_orchestrator/
│       ├── vision_detector/
│       ├── conveyor_controller/
│       ├── dobot_controller/
│       ├── turtlebot_delivery/
│       └── hri_interfaces/
├── hardware/conveyor_pi/   # Raspberry Pi conveyor standalone scripts
├── assets/stl/car/         # 조립 대상 STL asset
├── docs/                   # 설계/실행/인터페이스 문서
├── tests/                  # mock scenario 및 API 테스트
└── scripts/                # 개발/실행 보조 스크립트
```

## 핵심 구현 내용

### 1. Mission Orchestrator FSM
`mission_orchestrator`가 공정 상태를 관리하고 비전, 컨베이어, Dobot, TurtleBot, HRI 모듈의 이벤트를 하나의 흐름으로 연결합니다.

### 2. Dashboard Backend
`dashboard_backend.operations`에는 `Order`, `FactoryEvent`, `VisionDetection` 모델이 정의되어 있어 작업 오더와 공정 이벤트를 API/DB 관점에서 관리할 수 있습니다.

### 3. Hardware Script 분리
Raspberry Pi conveyor 제어 코드는 `hardware/conveyor_pi/`에 따로 두어 edge controller로 복사해 실행할 수 있게 했습니다.

### 4. Mock-first 검증
실제 장비 없이도 `pytest`와 mock runner로 공정 FSM, 이벤트 흐름, WebSocket bridge를 먼저 검증할 수 있습니다.

## Local Mock Quick Start

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
python3 -m sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.mock_runner
```

WebSocket bridge는 다음 명령으로 실행합니다.

```bash
python3 -m server.app
```

## Vue/Django Dashboard Quick Start

```bash
# Frontend
cd web
npm install
npm run build

# Django backend
cd ..
export SMART_ASSEMBLY_DB_NAME=smart_assembly_transport
export SMART_ASSEMBLY_DB_USER=smart_assembly
export SMART_ASSEMBLY_DB_PASSWORD=smart_assembly
python3 manage.py migrate
python3 manage.py runserver 0.0.0.0:8000
```

로컬에서 MySQL 없이 확인할 때는 SQLite fallback을 사용할 수 있습니다.

```bash
SMART_ASSEMBLY_DB_BACKEND=sqlite python3 manage.py migrate
SMART_ASSEMBLY_DB_BACKEND=sqlite python3 manage.py runserver 127.0.0.1:8000
```

## Documentation

상세 기획과 실행 문서는 [`docs/`](./docs/README.md)에 정리되어 있습니다.

| # | 문서 | 내용 |
|---|---|---|
| 01 | [프로젝트 개요](./docs/01-overview.md) | 목표, 동작 요약, 범위 |
| 02 | [시스템 아키텍처](./docs/02-architecture.md) | 전체 구조, 데이터 흐름, FSM |
| 03 | [하드웨어 구성](./docs/03-hardware.md) | 사용 장비, 역할, 검증 항목 |
| 04 | [기술 스택](./docs/04-tech-stack.md) | ROS 2, Vision, Web, STT/TTS |
| 05 | [데이터 모델 / 인터페이스](./docs/05-data-model.md) | ROS 2 토픽, 이벤트, API 초안 |
| 13 | [로컬 Mock 실행 가이드](./docs/13-local-mock-runbook.md) | 테스트, mock runner, WebSocket 실행 |
| 14 | [실제 하드웨어 실행 가이드](./docs/14-real-hardware-runbook.md) | 실제 Conveyor/TurtleBot/Dobot dry-run 및 실행 |

---
ROS 2와 웹 대시보드를 연결해 조립 공정과 배송 흐름을 통합한 스마트팩토리 프로젝트입니다.
