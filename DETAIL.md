# Smart Assembly Transport - DETAIL

이 문서는 `smart-assembly-transport` 프로젝트를 나중에 아무것도 기억나지 않는 상태에서 다시 봐도 이해할 수 있도록 작성한 상세 설명입니다. 이 프로젝트는 단일 기능보다 **여러 로봇/비전/웹 모듈을 하나의 공정 시나리오로 연결하는 것**이 핵심입니다.

## 1. 프로젝트 한 줄 요약

작업자의 음성 명령을 시작으로 컨베이어, RealSense 비전, Dobot 로봇팔, TurtleBot 배송, Django/Vue 대시보드를 연결해 조립 공정과 무인 배송을 수행하는 스마트팩토리 통합 프로젝트입니다.

## 2. 전체 시나리오

```text
작업자 음성 명령
  → 작업 오더 생성
  → 컨베이어 구동
  → RealSense/YOLO로 부품 위치 감지
  → Dobot pick/place 조립
  → 품질 확인
  → TurtleBot 적재 및 목적지 이동
  → 대시보드 상태 갱신
  → TTS/완료 이벤트
```

이 프로젝트는 실제 장비가 모두 연결되지 않은 상태에서도 mock runner와 테스트로 흐름을 먼저 확인할 수 있도록 구성되어 있습니다.

## 3. 상위 디렉터리 구조

```text
.
├── server/                     # WebSocket bridge
├── dashboard_backend/           # Django API/backend
├── web/                         # Vue dashboard
├── sem1_pjt_ws/                 # ROS 2 workspace
│   └── src/
│       ├── mission_orchestrator/
│       ├── hri_interfaces/
│       ├── vision_detector/
│       ├── conveyor_controller/
│       ├── dobot_controller/
│       └── turtlebot_delivery/
├── hardware/conveyor_pi/        # Raspberry Pi conveyor standalone script
├── scripts/                     # 실행/배포/bridge 보조 스크립트
├── tests/                       # mock 및 하드웨어 파이프라인 테스트
├── docs/                        # 설계/실행 문서
├── config/                      # hardware/nav config
├── assets/                      # STL 등 asset
└── map/                         # navigation map 파일
```

## 4. 핵심 설계: FSM 중심 구조

공정 전체는 `mission_orchestrator`의 FSM을 중심으로 움직입니다. FSM은 이벤트를 입력받고 다음 상태와 실행해야 할 command를 반환합니다.

### 4.1 주요 상태 흐름

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
  → RETURNING_HOME
  → RETURNED_HOME
```

### 4.2 주요 이벤트

`hri_interfaces.events.EventType`에 정의된 이벤트가 중심입니다.

| 이벤트 | 의미 |
| --- | --- |
| `order.created` | 작업 오더 생성 |
| `conveyor.started` | 컨베이어 시작 |
| `conveyor.stopped` | 컨베이어 정지 |
| `vision.base_in_position` | 베이스 부품 정위치 감지 |
| `safety.hand_detected` | 손 감지로 비상 상황 |
| `safety.dashboard_stop` | 대시보드 정지 요청 |
| `assembly.stage_1_done` | Dobot 조립 1단계 완료 |
| `assembly.stage_2_done` | Dobot 조립 2단계 완료 |
| `qc.passed` | 품질 확인 통과 |
| `delivery.arrived` | TurtleBot 목적지 도착 |
| `admin.unlocked` | 관리자 승인 후 재개 |

### 4.3 FSM command

FSM은 상태만 바꾸는 것이 아니라 다음에 실행할 command도 반환합니다.

| 전이 | command |
| --- | --- |
| order created | `conveyor.start` |
| base in position | `conveyor.stop` |
| conveyor stopped | `dobot.assembly_stage_1` |
| assembly stage 1 done | `dobot.assembly_stage_2` |
| assembly stage 2 done | `vision.qc_check` |
| qc passed | `dobot.load_to_turtlebot` |
| loaded to turtlebot | `turtlebot.navigate` |
| delivery arrived | `tts.say_complete` |
| return requested | `turtlebot.return_home` |
| return arrived | `factory.reset_for_next_order` |
| emergency | `factory.emergency_stop` |

이 구조 덕분에 ROS callback, WebSocket message, 테스트 코드가 같은 FSM을 공유할 수 있습니다.

## 5. `server/app.py` WebSocket bridge

`server/app.py`는 dashboard/STT client와 실제 하드웨어 adapter 사이를 연결하는 WebSocket bridge입니다.

### 5.1 실행

```bash
python -m server.app
```

기본 WebSocket 주소는 다음과 같습니다.

```text
ws://127.0.0.1:8765
```

### 5.2 주요 class/function

| 이름 | 역할 |
| --- | --- |
| `WebSocketMissionServer` | WebSocket client 관리와 mission message 처리 |
| `hardware_status_snapshot` | hardware config 기준 현재 연결/명령 상태 요약 |
| `real_pipeline_summary` | 실제 장비 pipeline 요약 반환 |
| `parse_whisper_command` | STT transcript를 작업 명령으로 해석 |
| `handle_whisper_transcript` | 음성 인식 결과를 order/event로 변환 |
| `navigate_turtlebot_from_speech` | 음성 목적지 기반 TurtleBot 이동 처리 |
| `broadcast` | 연결된 client에 event 전파 |
| `websocket_handler` | client별 WebSocket session 처리 |

### 5.3 dry-run 기본값

파일 상단 docstring에도 적혀 있듯, 기본 hardware command는 dry-run 중심입니다. 실제 장비에 명령을 보내려면 message에서 `execute: true`를 명시하는 방식으로 설계되어 있습니다. 이는 개발 PC에서 실수로 컨베이어나 로봇이 움직이는 것을 막기 위한 구조입니다.

## 6. Django backend

`dashboard_backend/operations`는 대시보드 API와 DB model을 담당합니다.

### 6.1 Models

`dashboard_backend/operations/models.py`에는 다음 모델이 있습니다.

| 모델 | 역할 |
| --- | --- |
| `Order` | 작업 오더 저장 |
| `FactoryEvent` | 공정 이벤트 기록 |
| `VisionDetection` | 비전 감지 결과 저장 |
| `DeliveryResult` | 배송 결과 기록 |
| `EmergencyStopLog` | 비상 정지 로그 기록 |

### 6.2 Views/API

`dashboard_backend/operations/views.py`에는 다음 기능이 있습니다.

| 함수 | 역할 |
| --- | --- |
| `health` | 서버 상태 확인 |
| `create_order` | 작업 오더 생성 |
| `record_event` | 공정 이벤트 기록 |
| `metrics` | 대시보드 지표 반환 |
| `seed_demo_data` | 데모 데이터 생성 |
| `project_chatbot` | 프로젝트 설명/상태 질의용 챗봇 endpoint |
| `dashboard_index` | Vue build 또는 fallback HTML 제공 |

챗봇은 Ollama API를 사용할 수 있게 되어 있으며 기본 model/url은 환경변수로 조정합니다.

```text
SMART_ASSEMBLY_OLLAMA_MODEL
SMART_ASSEMBLY_OLLAMA_URL
```

## 7. Vue dashboard

`web/` 폴더는 Vue 기반 대시보드입니다. `ProgressView.vue`, `App.vue`, chart/UI 파일이 포함되어 있고, Django backend build 결과 또는 fallback HTML과 연결됩니다.

주요 목적:

- 현재 공정 상태 표시
- 오더/이벤트/배송 상태 확인
- 비상 정지/관리자 승인 흐름 표시
- Vision/Dobot/TurtleBot 상태를 한 화면에서 확인

실행 예시:

```bash
cd web
npm install
npm run build
```

## 8. ROS 2 workspace `sem1_pjt_ws`

이 프로젝트의 실제 로봇 제어 코드는 `sem1_pjt_ws/src` 아래에 있습니다.

### 8.1 `hri_interfaces`

공통 event, work order, hardware config를 정의합니다.

중요 파일:

- `events.py`
- `hardware_config.py`

`WorkOrder`는 다음 필드를 갖습니다.

| 필드 | 의미 |
| --- | --- |
| `command` | 원본 작업 명령 |
| `destination` | 배송 목적지 |
| `parts` | 조립/운반 대상 부품 목록 |
| `order_id` | 자동 생성되는 order id |
| `priority` | 우선순위 |

### 8.2 `mission_orchestrator`

공정 FSM과 real hardware pipeline을 담당합니다.

중요 파일:

- `fsm.py`
- `real_pipeline.py`
- `mock_runner.py`

`real_pipeline.py`의 `RealHardwarePipeline`은 conveyor, TurtleBot, Dobot controller를 한 곳에서 묶습니다. `execute=False`일 때는 실제 명령 실행 대신 어떤 command가 실행될지 반환하는 구조입니다.

### 8.3 `vision_detector`

RealSense D435i color/depth 기반 감지를 담당합니다.

중요 파일:

- `realsense_detector.py`

기능:

- color image 구독
- aligned depth image 구독
- camera info 구독
- HSV 기반 색상 감지
- YOLO 결과 parsing
- ROI filtering
- pixel + depth를 camera frame 3D point(mm)로 변환
- 감지 결과 JSON 및 annotated image publish

핵심 class/function:

| 이름 | 역할 |
| --- | --- |
| `RealSenseIntrinsics` | 카메라 내부 파라미터 |
| `HsvRange` | HSV threshold 범위 |
| `DepthDetection` | depth 기반 감지 결과 |
| `YoloDetection` | YOLO 감지 결과 |
| `deproject_pixel_to_camera_mm` | pixel/depth를 3D 좌표로 변환 |
| `detect_largest_colored_depth_point` | 색상 기반 가장 큰 물체 감지 |
| `parse_yolo_xyxy_results` | YOLO xyxy 결과 파싱 |
| `build_vision_detections_message` | 대시보드/ROS 메시지 payload 생성 |

### 8.4 `dobot_controller`

Dobot 조립/픽앤플레이스 흐름을 담당합니다.

중요 파일:

- `realsense_pick_place.py`
- `real_dobot.py`

`realsense_pick_place.py`는 RealSense로 얻은 camera point를 Dobot 좌표로 변환하고, 안전 z 이동을 포함한 pick/place sequence를 만듭니다.

주요 개념:

- `CameraPoint`: 카메라 기준 3D 좌표
- `PickPlaceStep`: 한 단계의 Dobot 동작
- `PickPlacePlan`: 전체 pick/place plan
- `PickPlaceConfig`: 좌표 변환/높이/속도 설정
- `ObjectPickPlaceCoordinator`: 여러 object 작업 순서 관리
- `TwoObjectPickPlaceNode`: ROS 2 실행 node

### 8.5 `conveyor_controller`

컨베이어 제어 추상화입니다. 실제 Raspberry Pi script를 SSH 또는 로컬 명령으로 호출하는 구조와 연결됩니다.

### 8.6 `turtlebot_delivery`

TurtleBot 배송 제어입니다. 목적지 pose로 navigation command를 구성하고, 배송 도착/복귀 이벤트와 연결됩니다.

## 9. Raspberry Pi conveyor script

`hardware/conveyor_pi/conveyor_control.py`는 컨베이어 edge device에서 직접 실행할 수 있는 standalone script입니다.

### 9.1 주요 환경변수

| 환경변수 | 기본값 | 의미 |
| --- | --- | --- |
| `CONVEYOR_MODE` | `digital` | digital/stepper 등 동작 모드 |
| `CONVEYOR_STATE_FILE` | `~/.smart_assembly_conveyor_state.json` | 상태 기록 파일 |
| `CONVEYOR_STOP_FILE` | `~/.smart_assembly_conveyor_stop.json` | stop request 파일 |
| `CONVEYOR_MOTOR_PIN` | `18` | digital motor pin |
| `CONVEYOR_STEP_PIN` | `27` | stepper step pin |
| `CONVEYOR_DIR_PIN` | `17` | stepper direction pin |
| `CONVEYOR_ENABLE_PIN` | `22` | stepper enable pin |
| `CONVEYOR_STEPS` | `800` | stepper mode step 수 |
| `SORTER_SERVO_PIN` | `18` | sorter servo pin |

### 9.2 지원 동작

- digital motor on/off
- stepper pulse 기반 이동
- sorter servo pulse
- stop request file 기반 중단
- state JSON 기록
- gpiozero/gpiod backend 선택

## 10. Hardware config

`config/hardware.json`을 `hri_interfaces.hardware_config.HardwareConfig`가 읽습니다.

주요 config class:

| class | 역할 |
| --- | --- |
| `ConveyorConfig` | conveyor Pi SSH/remote script 설정 |
| `TurtleBotConfig` | TurtleBot host, ROS domain, nav target 설정 |
| `DobotConfig` | Dobot action/service와 pick/place 높이 설정 |
| `VisionConfig` | camera topic, base color, min area 등 |
| `DashboardConfig` | WebSocket/HTTP port 설정 |
| `HardwareConfig` | 전체 hardware 설정 묶음 |

## 11. 테스트 구조

`tests/`에는 mock/real hardware pipeline을 검증하는 테스트가 있습니다.

주요 테스트 파일:

- `test_real_hardware_pipeline.py`
- `test_realsense_pick_place.py`
- `test_realsense_stream_bridge.py`
- FSM/mock scenario 관련 테스트

실행:

```bash
python3 -m pytest -q
```

## 12. 실행 흐름

### 12.1 개발 PC에서 mock 검증

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
python3 -m sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.mock_runner
```

### 12.2 WebSocket bridge 실행

```bash
python3 -m server.app
```

### 12.3 Dashboard build

```bash
cd web
npm install
npm run build
```

### 12.4 Django backend 실행

MySQL 환경:

```bash
export SMART_ASSEMBLY_DB_NAME=smart_assembly_transport
export SMART_ASSEMBLY_DB_USER=smart_assembly
export SMART_ASSEMBLY_DB_PASSWORD=<db_password>
python3 manage.py migrate
python3 manage.py runserver 0.0.0.0:8000
```

SQLite fallback:

```bash
SMART_ASSEMBLY_DB_BACKEND=sqlite python3 manage.py migrate
SMART_ASSEMBLY_DB_BACKEND=sqlite python3 manage.py runserver 127.0.0.1:8000
```

## 13. 실제 장비 연결 전 확인 순서

1. `pytest`가 통과하는지 확인
2. `config/hardware.json`의 host/user/port가 현재 장비와 맞는지 확인
3. conveyor Pi에 `conveyor_control.py`가 배포되어 있는지 확인
4. TurtleBot ROS domain과 nav target pose를 확인
5. Dobot homing, PTP action, vacuum/gripper 제어가 개별적으로 되는지 확인
6. RealSense color/depth/camera_info topic이 들어오는지 확인
7. WebSocket bridge를 dry-run으로 먼저 실행
8. 마지막에만 `execute=true`로 실제 명령 실행

## 14. 나중에 빠르게 기억할 요약

- 이 프로젝트는 ROS 2 + Web + 실제 장비를 묶은 스마트팩토리 통합 프로젝트입니다.
- 중앙 개념은 `mission_orchestrator`의 FSM입니다.
- `server/app.py`는 WebSocket bridge이며, 기본은 dry-run 안전 구조입니다.
- `dashboard_backend`는 Django API와 DB model입니다.
- `web`은 Vue 대시보드입니다.
- `vision_detector`는 RealSense/YOLO 기반 3D 위치 감지입니다.
- `dobot_controller`는 RealSense 좌표를 Dobot pick/place plan으로 바꿉니다.
- `hardware/conveyor_pi`는 Raspberry Pi에서 직접 돌릴 conveyor 제어 script입니다.
- 실제 장비 실행 전에는 테스트, config, dry-run을 먼저 확인해야 합니다.
