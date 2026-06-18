# WBS / Kanban 작업 분해

## Kanban 컬럼

- `Backlog`: 해야 할 작업
- `Ready`: 바로 시작 가능한 작업
- `In Progress`: 진행 중
- `Review`: 코드/문서 리뷰 또는 단품 검증 대기
- `Done`: 완료
- `Blocked`: 하드웨어/환경/의존성 문제로 막힘

GitHub Issues에 `area:*`, `priority:*`, `day:*`, `status:*` 라벨을 붙여 Kanban으로 관리한다.

## 1주일 WBS

| ID | Day | Area | 작업 | 의존성 | 완료 기준 |
|---|---:|---|---|---|---|
| W01 | 1 | planning | repo/README/문서 구조 생성 | 없음 | GitHub repo와 기본 문서 push |
| W02 | 1 | architecture | FSM 상태와 ROS 2 인터페이스 정의 | W01 | `docs/ARCHITECTURE.md` 작성 |
| W03 | 1 | kanban | GitHub Issues/Kanban 백로그 생성 | W02 | 주요 작업 이슈화 |
| W04 | 2 | orchestration | `mission_orchestrator` 패키지 생성 | W02 | ROS 2 노드 실행 가능 |
| W05 | 2 | orchestration | mock 노드 기반 정상 FSM 구현 | W04 | `DELIVERED`까지 로그 출력 |
| W06 | 2 | safety | HAND_DETECTED emergency stop 구현 | W05 | 임의 이벤트로 `EMERGENCY_STOP` 진입 |
| W07 | 2 | safety | 관리자 비밀번호 해제/재개 구현 | W06 | unlock 후 이전/안전 상태 재개 |
| W08 | 3 | vision | 카메라 입력 및 YOLO/OpenCV 감지 MVP | W02 | 베이스/손 이벤트 publish |
| W09 | 3 | conveyor | 컨베이어 start/stop 노드 이식 | W02 | 단품 start/stop 확인 |
| W10 | 3 | integration | vision 이벤트 → conveyor stop 연결 | W08,W09 | 감지 시 컨베이어 정지 |
| W11 | 4 | dobot | Dobot bringup/driver 실행 절차 정리 | W02 | README 실행 절차 작성 |
| W12 | 4 | dobot | 고정 좌표 pick/place 루틴 구현 | W11 | 단품 동작 성공 |
| W13 | 4 | dobot | Dobot action result → FSM 연결 | W05,W12 | stage1/stage2 상태 전이 |
| W14 | 5 | turtlebot | map/Nav2 실행 절차 정리 | W02 | 목적지 좌표 config 작성 |
| W15 | 5 | turtlebot | Nav2 goal sender 구현 | W14 | A구역 goal 전송 성공 |
| W16 | 5 | hri | TTS 완료 안내 연결 | W05,W15 | 배송 완료 음성 출력 |
| W17 | 6 | web | Backend 상태 이벤트 API/WebSocket 구현 | W05 | FSM 이벤트 수신 가능 |
| W18 | 6 | web | Vue dashboard MVP 구현 | W17 | 주문/상태/비상 모달 표시 |
| W19 | 6 | integration | 전체 리허설 1차 | W10,W13,W15,W18 | 실패 지점 기록 |
| W20 | 7 | integration | 전체 리허설 2~3차 및 안정화 | W19 | 2/3회 이상 데모 성공 |
| W21 | 7 | docs | 실행 가이드/발표자료/영상 정리 | W20 | 제출 가능한 산출물 완성 |

## MVP GitHub Issue 초안

1. `Day1: Define ROS 2 FSM and interface contract`
2. `Day2: Build mission_orchestrator mock end-to-end flow`
3. `Day2: Implement emergency stop and admin unlock FSM`
4. `Day3: Integrate YOLO/OpenCV base and hand detection events`
5. `Day3: Port conveyor start/stop controller`
6. `Day4: Implement Dobot fixed-coordinate assembly routine`
7. `Day5: Implement TurtleBot Nav2 delivery goal sender`
8. `Day6: Build WebSocket dashboard MVP`
9. `Day6: Run first integrated rehearsal`
10. `Day7: Prepare final demo script and fallback plan`

## Definition of Done

각 작업은 다음 조건을 만족해야 Done으로 이동한다.

- 실행 명령이 문서화되어 있다.
- 성공/실패 로그 또는 스크린샷/영상 근거가 있다.
- mock과 real 모드 중 최소 하나가 동작한다.
- 통합에 필요한 topic/action/service 이름이 문서와 일치한다.
- 안전 관련 작업은 실패 시 기본값이 정지 상태여야 한다.
