# 자동 조립 공정 및 무인 배송 시스템

음성 명령을 기반으로 컨베이어, 비전, Dobot 로봇팔, TurtleBot을 연동하여 **제품 조립 → 품질 확인 → 무인 배송**까지 수행하는 스마트팩토리 통합 프로젝트입니다.

본 프로젝트는 단일 기능 구현보다 여러 로봇/AI 모듈이 하나의 공정으로 연결되는 것을 목표로 합니다.

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

- STT 기반 작업 명령 입력
- 컨베이어 구동 및 정위치 정지
- YOLO/OpenCV 기반 부품·손·완성품 인식
- 사람 손 감지 시 비상 정지 및 관리자 승인 후 복구
- Dobot 로봇팔 기반 다단계 조립 및 적재
- TurtleBot3 SLAM/Nav2 기반 무인 배송
- 대시보드 기반 작업 상태 모니터링
- TTS 기반 완료/경고 안내

## Repository Structure

```text
server/             작업 오더, 상태 이벤트, WebSocket API
web/                공정 모니터링 및 비상 복구 대시보드
sem1_pjt_ws/        ROS 2 기반 로봇/공정 제어 워크스페이스
  src/
    mission_orchestrator/   전체 공정 FSM 및 모듈 통합
    vision_detector/        부품/손/QC 비전 인식
    conveyor_controller/    컨베이어 구동/정지 제어
    dobot_controller/       Dobot 조립 및 적재 제어
    turtlebot_delivery/     TurtleBot 배송 목표 제어
    hri_interfaces/         STT/TTS 및 웹 연동 인터페이스
docs/               프로젝트 기획, 아키텍처, 인터페이스, 일정 문서
sample-data/        테스트 이미지, 영상, 지도, 예제 입력 데이터
```

> 현재 repository는 하드웨어 없이도 mock 공정 흐름을 먼저 검증할 수 있도록 `sem1_pjt_ws` 기반 Python/ROS 2 scaffold와 WebSocket bridge 초안을 포함합니다.

## Local Mock Quick Start

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
python3 -m sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.mock_runner
```

WebSocket bridge는 다음으로 실행합니다.

```bash
python3 -m server.app
```

## Documentation

프로젝트 상세 기획은 [`docs/`](./docs/README.md)에 정리합니다.

| # | 문서 | 내용 |
|---|---|---|
| 01 | [프로젝트 개요](./docs/01-overview.md) | 목표, 동작 요약, 범위 |
| 02 | [시스템 아키텍처](./docs/02-architecture.md) | 전체 구조, 데이터 흐름, FSM |
| 03 | [하드웨어 구성](./docs/03-hardware.md) | 사용 장비, 역할, 검증 항목 |
| 04 | [기술 스택](./docs/04-tech-stack.md) | ROS 2, Vision, Web, STT/TTS |
| 05 | [데이터 모델 / 인터페이스](./docs/05-data-model.md) | ROS 2 토픽, 이벤트, API 초안 |
| 06 | [단계별 목표](./docs/06-stages.md) | 1주일 MVP 단계별 산출물 |
| 07 | [역할 및 일정](./docs/07-roles-and-schedule.md) | WBS, Kanban 운영, 일정 |
| 08 | [STT/TTS 설계](./docs/08-stt-tts.md) | 음성 명령, 응답, fallback |
| 09 | [데모 시나리오](./docs/09-demo-scenario.md) | 시연 흐름, 촬영/발표 기준 |
| 10 | [위험 요소](./docs/10-risks.md) | 리스크와 대응 전략 |
| 11 | [인터페이스 합의서](./docs/11-interfaces.md) | 모듈 간 합의가 필요한 계약 |
| 12 | [하드웨어 임의값 목록](./docs/12-placeholder-hardware-values.md) | 실측/보정이 필요한 mock 좌표와 설정 |
| 13 | [로컬 Mock 실행 가이드](./docs/13-local-mock-runbook.md) | 테스트, mock runner, WebSocket 실행 |
| 14 | [실제 하드웨어 실행 가이드](./docs/14-real-hardware-runbook.md) | 실제 Conveyor/TurtleBot/Dobot dry-run 및 실행 |
| 15 | [참고 프로젝트 고도화 적용 기준](./docs/15-reference-adaptation.md) | project_pill 참고 패턴 적용 기준 |

## 개발 원칙

- 공정 전체 흐름을 먼저 mock으로 연결한 뒤 실제 하드웨어 노드로 교체합니다.
- 안전 정지는 모든 기능보다 우선합니다.
- ROS 2 인터페이스와 상태 이벤트는 초기에 고정하고 문서 변경 없이 임의 수정하지 않습니다.
- 데모 성공을 위해 실제 장비 실패 시 사용할 fallback 경로를 항상 유지합니다.
