# 프로젝트 기획 문서

자동 조립 공정 및 무인 배송 시스템 — 음성 명령 기반 컨베이어·비전·로봇팔·모바일 로봇 통합 스마트팩토리 프로젝트

## 문서 인덱스

| # | 문서 | 내용 |
|---|---|---|
| 01 | [01-overview.md](./01-overview.md) | 프로젝트 개요, 목표, 동작 요약, 범위 |
| 02 | [02-architecture.md](./02-architecture.md) | 시스템 구조, 통신 흐름, FSM, 안전 흐름 |
| 03 | [03-hardware.md](./03-hardware.md) | 사용 장비, 역할, 검증 항목 |
| 04 | [04-tech-stack.md](./04-tech-stack.md) | 기술 스택, 개발 환경, 참고 코드 자산 |
| 05 | [05-data-model.md](./05-data-model.md) | 작업 오더, 상태 이벤트, ROS 2/WebSocket/API 메시지 |
| 06 | [06-stages.md](./06-stages.md) | 1주일 MVP 단계별 목표와 완료 기준 |
| 07 | [07-roles-and-schedule.md](./07-roles-and-schedule.md) | WBS, Kanban 이슈, 일정 운영 방식 |
| 08 | [08-stt-tts.md](./08-stt-tts.md) | STT/TTS 명령 흐름, 명령 카탈로그, fallback |
| 09 | [09-demo-scenario.md](./09-demo-scenario.md) | 최종 데모 시나리오, 촬영 순서, 발표 포인트 |
| 10 | [10-risks.md](./10-risks.md) | 위험 매트릭스, 우선 검증 체크리스트 |
| 11 | [11-interfaces.md](./11-interfaces.md) | 모듈 간 인터페이스 합의서 |
| 12 | [12-placeholder-hardware-values.md](./12-placeholder-hardware-values.md) | 하드웨어 임의값 / 추후 실측 필요 목록 |
| 13 | [13-local-mock-runbook.md](./13-local-mock-runbook.md) | 하드웨어 없이 로컬에서 mock 공정 검증 |

## 빠른 요약

- **목표**: 음성 명령으로 시작된 작업 오더를 컨베이어, 비전, Dobot, TurtleBot이 협력하여 조립·검사·배송까지 수행
- **기간**: 1주일 MVP
- **핵심 기술**: ROS 2, Python, C/C++, YOLO/OpenCV, Dobot, TurtleBot3, Nav2, STT/TTS, WebSocket Dashboard
- **하드웨어**: Ubuntu PC, Raspberry Pi 5, Conveyor, RealSense/RGBD Camera, Dobot Magician, TurtleBot3
- **시연 목표**: end-to-end 공정 흐름과 비상 정지/복구 시나리오를 보여주는 데모

## MVP 우선순위

1. ROS 2 Mission Orchestrator와 안전 FSM
2. 컨베이어 정위치 정지 + 손 감지 비상 정지
3. Dobot 조립/적재 루틴
4. TurtleBot 목적지 배송
5. Dashboard와 STT/TTS 연동

## 문서 갱신 원칙

- 인터페이스 변경은 `05-data-model.md`와 `11-interfaces.md`를 먼저 수정합니다.
- 일정/범위 변경은 `06-stages.md`, `07-roles-and-schedule.md`, `10-risks.md`에 반영합니다.
- 실제 장비 검증 결과는 해당 문서의 체크리스트에 기록합니다.
