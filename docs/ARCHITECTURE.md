# 시스템 아키텍처 초안

## End-to-end 플로우

```text
작업자 음성
  → STT 노드/서비스
  → Backend API + WebSocket Dashboard
  → ROS 2 Mission Orchestrator FSM
  → Conveyor Controller
  → Vision Detector(YOLOv5 + RealSense/RGBD)
  → Dobot Assembly Action Client
  → Vision QC
  → Dobot Loading Action Client
  → TurtleBot Nav2 Goal Sender
  → TTS 완료 안내 + Dashboard 상태 갱신
```

## 핵심 ROS 2 노드 후보

| 노드 | 역할 | 참고 자산 |
|---|---|---|
| `mission_orchestrator` | 전체 FSM, 작업 오더 수신, 상태 전이, 비상 정지/복구 | 신규 작성 |
| `stt_gateway` | 음성 명령 → 작업 오더 JSON | 신규 또는 백엔드 연동 |
| `conveyor_controller` | Raspberry Pi 5 Modbus/GPIO 기반 컨베이어 start/stop | `homework_ws/0520_conveyor` |
| `vision_detector` | 베이스/부품/손/완성품 감지, 중심점 산출 | `yolov5`, `homework_ws/0602_custom_yolo`, `0521_RGBD` |
| `tf_projector` | 픽셀 + depth → Dobot base 좌표 변환 | `homework_ws/0521_RGBD`, `ssafy_ws` TF 예제 |
| `dobot_assembly_client` | PTP/Action 기반 1단계·2단계 조립 | `magician_ros2_control_system_ws`, `homework_ws/0519_Dobot_integration` |
| `qc_classifier` | 조립 완료/불량/누락 판단 | `yolov5`, OpenCV |
| `dobot_loader` | 완성품 TurtleBot 적재 | Dobot 제어 패키지 |
| `turtlebot_delivery` | 목적지별 Nav2 goal 전송, 도착 이벤트 | `turtlebot3_ws`, `homework_ws/0513_SLAM`, `0514_NAV2` |
| `tts_reporter` | 완료/오류 상태 음성 안내 | 신규 작성 |
| `dashboard_bridge` | Backend/WebSocket과 ROS 상태 동기화 | 신규 작성 |

## FSM 상태 초안

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
ANY_ACTIVE_STATE + HAND_DETECTED
  → EMERGENCY_STOP
  → WAIT_ADMIN_UNLOCK
  → RESUME_PREVIOUS_STATE 또는 SAFE_RESTART
```

## 최소 메시지/API 계약

### 작업 오더

```json
{
  "order_id": "20260618-001",
  "product_type": "default_assembly",
  "destination": "A",
  "source": "stt",
  "raw_text": "해당 제품 조립 후 A구역으로 배송해"
}
```

### 상태 이벤트

```json
{
  "order_id": "20260618-001",
  "state": "ASSEMBLY_STAGE_1",
  "severity": "info",
  "message": "1단계 부품 조립 중",
  "timestamp": "ISO-8601"
}
```

### 안전 이벤트

```json
{
  "event": "HAND_DETECTED",
  "action": "EMERGENCY_STOP",
  "requires_admin_password": true
}
```

## 1주일 MVP 범위

필수:

- ROS 2 FSM과 각 서브시스템의 mock/sim 인터페이스
- STT 명령 또는 텍스트 입력으로 작업 오더 생성
- 컨베이어 start/stop 단품 제어
- YOLO 또는 OpenCV 기반 베이스/손 감지 데모
- Dobot PTP 1개 이상 pick/place 루틴
- TurtleBot Nav2 goal 전송 데모
- 비상 정지 → 비밀번호 해제 → 재개 흐름
- 대시보드 또는 CLI 로그로 전체 상태 확인

후순위:

- 완성도 높은 Vue/Chart.js 통계 화면
- 실제 다품종 조립 데이터셋 확장
- 정교한 QC 모델
- 고급 동적 장애물 시나리오
