# 11. 인터페이스 합의서

본 문서는 각 모듈 담당자가 지켜야 하는 인터페이스 계약을 정의한다. 구현 중 변경이 필요하면 먼저 이 문서를 수정하고 관련 담당자가 확인한다.

## 책임 경계

| 모듈 | 제공 인터페이스 | 호출/구독 대상 |
|---|---|---|
| Mission Orchestrator | `/factory/state`, subsystem command | Backend, 각 제어 노드 |
| Vision Detector | `/vision/detection`, `/factory/safety_event` | Orchestrator |
| Conveyor Controller | `/conveyor/status`, command receiver | Orchestrator |
| Dobot Controller | assembly/loading action | Orchestrator |
| TurtleBot Delivery | delivery action/result | Orchestrator |
| Backend Bridge | WebSocket/REST | Dashboard, Orchestrator |
| Dashboard | emergency stop/unlock command | Backend/Orchestrator |

## 변경 절차

1. 변경 필요 사항을 Issue 또는 PR에 기록한다.
2. `05-data-model.md`의 메시지 예시와 표를 수정한다.
3. 이 문서의 책임 경계가 바뀌면 함께 수정한다.
4. mock 노드와 real 노드 양쪽에서 동일 인터페이스를 유지한다.
5. 통합 테스트 후 merge한다.

## 환경 변수 / 설정 후보

| 이름 | 의미 |
|---|---|
| `ROS_DOMAIN_ID` | ROS 2 네트워크 도메인 |
| `CONVEYOR_HOST` | 컨베이어 제어 장치 주소 |
| `DASHBOARD_UNLOCK_PASSWORD` | 관리자 비상 해제 비밀번호 |
| `DEST_A_X`, `DEST_A_Y`, `DEST_A_YAW` | A구역 Nav2 목적지 |
| `DOBOT_STAGE1_POSE` | 1단계 조립 좌표 |
| `DOBOT_STAGE2_POSE` | 2단계 조립 좌표 |

## 합의 완료 체크리스트

- [ ] FSM 상태 이름 확정
- [ ] ROS 2 topic/action/service 이름 확정
- [ ] 안전 이벤트 필드 확정
- [ ] 목적지 좌표 설정 방식 확정
- [ ] 관리자 unlock 방식 확정
- [ ] mock/real 전환 방식 확정
- [ ] 데모 fallback 경로 확정
