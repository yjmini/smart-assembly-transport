# 05. 데이터 모델 / 인터페이스

본 문서는 모듈 간 주고받는 데이터 계약을 정의한다. 실제 구현 중 변경이 필요하면 이 문서를 먼저 수정한다.

## 작업 오더

```json
{
  "order_id": "20260618-001",
  "product_type": "default_assembly",
  "destination": "A",
  "source": "stt",
  "raw_text": "제품 조립 후 A구역으로 배송해"
}
```

## 상태 이벤트

```json
{
  "order_id": "20260618-001",
  "state": "ASSEMBLY_STAGE_1",
  "severity": "info",
  "message": "1단계 조립 중",
  "timestamp": "2026-06-18T12:00:00+09:00"
}
```

## 안전 이벤트

```json
{
  "event": "HAND_DETECTED",
  "action": "EMERGENCY_STOP",
  "requires_admin_unlock": true,
  "source": "vision_detector"
}
```

## ROS 2 인터페이스 초안

| 이름 | 타입 후보 | 발행자 | 구독자 | 용도 |
|---|---|---|---|---|
| `/factory/order` | JSON/String or custom msg | Backend/STT | Orchestrator | 작업 오더 입력 |
| `/factory/state` | JSON/String | Orchestrator | Backend/Dashboard | FSM 상태 이벤트 |
| `/factory/safety_event` | JSON/String | Vision/Dashboard | Orchestrator | 손 감지, STOP 등 |
| `/conveyor/command` | JSON/String or service | Orchestrator | Conveyor | start/stop |
| `/conveyor/status` | JSON/String | Conveyor | Orchestrator | 컨베이어 상태 |
| `/vision/detection` | JSON/String | Vision | Orchestrator | 베이스/부품/손/QC 감지 |
| `/dobot/assembly_goal` | Action | Orchestrator | Dobot | 조립/적재 명령 |
| `/turtlebot/delivery_goal` | Action or Nav2 goal | Orchestrator | TurtleBot | 배송 목적지 명령 |

## WebSocket 메시지 초안

### Server → Dashboard

```json
{
  "type": "factory_state",
  "data": {
    "order_id": "20260618-001",
    "state": "CONVEYOR_MOVING",
    "message": "컨베이어 동작 중"
  }
}
```

### Dashboard → Server

```json
{
  "type": "admin_unlock",
  "data": {
    "password": "****",
    "target_order_id": "20260618-001"
  }
}
```

## REST/API 후보

| Method | Path | 용도 |
|---|---|---|
| POST | `/api/orders` | 수동 작업 오더 생성 |
| POST | `/api/emergency-stop` | UI 비상 정지 |
| POST | `/api/admin-unlock` | 비상 정지 해제 |
| GET | `/api/orders/{order_id}` | 작업 상태 조회 |
| GET | `/api/events` | 최근 이벤트 조회 |

## 변경 원칙

- 필드 이름 제거/변경은 모든 담당자 합의 후 진행한다.
- 필드 추가는 optional로 시작한다.
- 안전 이벤트는 누락되면 안 되므로 별도 테스트를 작성한다.
