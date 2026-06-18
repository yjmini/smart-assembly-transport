# 07. 역할 및 일정

## Kanban 운영

GitHub Issues를 Kanban 작업 단위로 사용한다.

| 컬럼 | 의미 |
|---|---|
| Backlog | 해야 할 작업 |
| Ready | 바로 시작 가능 |
| In Progress | 진행 중 |
| Review | 검증/리뷰 대기 |
| Done | 완료 |
| Blocked | 장비/환경/의존성으로 막힘 |

## 1주일 일정

| Day | 목표 | 주요 작업 |
|---|---|---|
| Day 1 | 설계 고정 | FSM, 인터페이스, 문서, Kanban |
| Day 2 | Mock E2E | Orchestrator, mock nodes, safety FSM |
| Day 3 | Vision/Conveyor | 베이스/손 감지, 컨베이어 정지 |
| Day 4 | Dobot | 조립/적재 루틴, Action result 연결 |
| Day 5 | TurtleBot | Nav2 goal, 목적지 배송, TTS |
| Day 6 | Dashboard/통합 | WebSocket 상태 표시, 비상 해제, 리허설 |
| Day 7 | 안정화/발표 | 데모 스크립트, 영상, fallback, 문서 정리 |

## 작업 레인

| 레인 | 담당 범위 |
|---|---|
| Orchestration/Safety | FSM, 비상 정지, 복구 |
| Vision/AI | 부품/손/QC 감지 |
| Manufacturing Control | 컨베이어, Dobot 조립/적재 |
| Mobile Robot | TurtleBot SLAM/Nav2 배송 |
| Web/HRI | STT/TTS, Backend, Dashboard |
| Integration/Docs | 통합 테스트, 발표자료, 문서 |

## 현재 GitHub Issues

- #1 Day1: Define ROS 2 FSM and interface contract
- #2 Day2: Build mission_orchestrator mock end-to-end flow
- #3 Day2: Implement emergency stop and admin unlock FSM
- #4 Day3: Integrate YOLO/OpenCV base and hand detection events
- #5 Day3: Port conveyor start/stop controller
- #6 Day4: Implement Dobot fixed-coordinate assembly routine
- #7 Day5: Implement TurtleBot Nav2 delivery goal sender
- #8 Day6: Build WebSocket dashboard MVP
- #9 Day6: Run first integrated rehearsal
- #10 Day7: Prepare final demo script and fallback plan

## 완료 정의

- 실행 방법 또는 검증 방법이 문서화되어 있다.
- 성공/실패 로그, 사진, 영상 중 하나로 근거가 있다.
- 안전 관련 작업은 실패 시 정지 상태가 기본값이다.
- 인터페이스 변경 사항이 `05-data-model.md`에 반영되어 있다.
