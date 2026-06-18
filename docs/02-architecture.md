# 02. 시스템 아키텍처

## 설계 방향

본 시스템은 ROS 2 Mission Orchestrator를 중심으로 각 서브시스템을 느슨하게 연결한다. 각 장비 제어 노드는 단일 책임을 갖고, 전체 공정 순서와 안전 상태 전이는 Orchestrator가 담당한다.

## 전체 구조

```text
[Operator]
  │ voice
  ▼
[STT/TTS + Dashboard]
  │ order/status JSON
  ▼
[Backend / WebSocket Bridge]
  │ ROS 2 event bridge
  ▼
[Mission Orchestrator FSM]
  ├─ [Conveyor Controller]
  ├─ [Vision Detector]
  ├─ [Dobot Controller]
  ├─ [TurtleBot Delivery]
  └─ [Safety Manager]
```

## 주요 컴포넌트

| 컴포넌트 | 책임 |
|---|---|
| Mission Orchestrator | 전체 FSM, 작업 오더 처리, 상태 전이, 서브시스템 명령 |
| Safety Manager | 손 감지/STOP/장비 오류 시 비상 정지 및 복구 조건 관리 |
| Vision Detector | 베이스 부품, 조립 부품, 사람 손, 완성품/QC 이벤트 감지 |
| Conveyor Controller | 컨베이어 start/stop, 상태 보고 |
| Dobot Controller | 조립 stage1/stage2, TurtleBot 적재 |
| TurtleBot Delivery | 목적지별 Nav2 goal 전송, 도착 상태 보고 |
| Backend Bridge | Dashboard와 ROS 2 상태 이벤트 중계 |
| Dashboard | 작업 상태 표시, 비상 정지, 관리자 해제 UI |
| STT/TTS | 음성 명령 입력과 완료/경고 음성 출력 |

## FSM 초안

```text
IDLE
  → ORDER_RECEIVED
  → CONVEYOR_MOVING
  → BASE_DETECTED_STOPPING
  → ASSEMBLY_STAGE_1
  → ASSEMBLY_STAGE_2
  → QC_CHECK
  → LOADING_TO_TURTLEBOT
  → DELIVERY_NAVIGATING
  → DELIVERED
  → IDLE
```

전역 인터럽트:

```text
ANY_ACTIVE_STATE + HAND_DETECTED/STOP/CRITICAL_ERROR
  → EMERGENCY_STOP
  → WAIT_ADMIN_UNLOCK
  → RESUME_PREVIOUS_STATE 또는 SAFE_RESTART
```

## 데이터 흐름

### 작업 오더 흐름

```text
음성 명령 → STT → Backend → Mission Orchestrator → 공정 시작
```

### 비전 기반 정지 흐름

```text
Camera → Vision Detector → BASE_IN_POSITION 이벤트 → Orchestrator → Conveyor STOP
```

### 조립 흐름

```text
Orchestrator → Dobot Controller stage command → Action feedback/result → 다음 상태 전이
```

### 배송 흐름

```text
Orchestrator → TurtleBot Delivery Nav2 goal → 도착 result → 완료 이벤트
```

### 안전 흐름

```text
Vision HAND_DETECTED 또는 Dashboard STOP
  → Orchestrator emergency interrupt
  → Conveyor/Dobot/TurtleBot stop 명령
  → Dashboard emergency modal
  → 관리자 비밀번호 확인
  → 복구 또는 안전 재시작
```

## mock/real 모드 원칙

모든 하드웨어 노드는 같은 인터페이스를 유지한 채 mock과 real 구현을 분리한다.

- mock: 통합 흐름 검증과 발표 fallback
- real: 실제 장비 제어
- Orchestrator는 mock/real 여부를 몰라도 동일한 topic/action/service를 사용한다.
