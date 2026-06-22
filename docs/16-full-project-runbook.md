# 16. 프로젝트 전체 실행 Runbook

이 문서는 현재 `main` 기준으로 **처음부터 끝까지 프로젝트 코드를 실행하고**, UI dry-run을 거쳐 실제 하드웨어 테스트까지 진행하는 순서를 정리한 문서입니다.

> 현재 환경에서는 ROS2 Humble의 `launch_testing` pytest 플러그인이 `pytest`와 충돌할 수 있으므로, 테스트 실행 시 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`을 붙이는 것을 기본으로 합니다.

---

## 0. 현재 기준 장비 정보

설정 원본은 [`config/hardware.json`](../config/hardware.json)입니다.

| 장비 | 주소 / 설정 | 용도 |
|---|---|---|
| Conveyor Raspberry Pi | `ssafy@192.168.110.142` | 컨베이어 start/stop/emergency-stop 실행 |
| TurtleBot4 | `turtlebot4@192.168.110.174` | Nav2 배송 및 HOME 복귀 |
| TurtleBot ROS Domain | `ROS_DOMAIN_ID=34` | TurtleBot4 ROS2 통신 domain |
| WebSocket server | `ws://127.0.0.1:8765` | Dashboard ↔ Mission server 통신 |
| Dashboard URL | `http://127.0.0.1:3000/web/index.html` | 운영 UI |
| RealSense topic | `/camera/camera/color/image_raw` | YOLO/비전 입력 후보 |

---

## 1. 최신 코드 받기

```bash
cd /home/ssafy/smart-assembly-transport
git checkout main
git pull origin main
git status --short --branch
```

기대 상태:

```text
## main...origin/main
```

---

## 2. 가상환경 사용 여부

현재 프로젝트는 ROS2 Humble, TurtleBot4, Dobot action, 시스템 Python 패키지와 같이 동작해야 하므로 **하드웨어 실행 단계에서는 가상환경 없이 시스템 Python을 사용하는 것을 권장**합니다.

만약 프롬프트 앞에 `(.venv)`가 붙어 있으면 끕니다.

```bash
deactivate
```

`deactivate: command not found`가 나오면 이미 가상환경이 꺼진 상태이므로 무시해도 됩니다.

---

## 3. ROS2 환경 로딩

터미널을 새로 열었으면 프로젝트 실행 전에 ROS2 환경을 로딩합니다.

```bash
cd /home/ssafy/smart-assembly-transport
source /opt/ros/humble/setup.bash
```

워크스페이스를 빌드한 적이 있다면 install setup도 로딩합니다.

```bash
source sem1_pjt_ws/install/setup.bash
```

`~/.bashrc`가 ROS2 환경을 로딩하도록 구성되어 있다면 아래처럼 해도 됩니다.

```bash
source ~/.bashrc
```

단, `source ~/.bashrc`는 `.venv`를 끌 수 있으므로 하드웨어 실행 단계에서는 가상환경 없이 진행하는 것이 안전합니다.

---

## 4. Python 의존성 설치

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m pip install --user websockets pytest opencv-python
```

만약 `externally-managed-environment`가 뜨면:

```bash
python3 -m pip install --user --break-system-packages websockets pytest opencv-python
```

설치 확인:

```bash
python3 - <<'PY'
import websockets
print("websockets:", websockets.__version__)
PY
```

---

## 5. 로컬 코드 테스트

ROS2의 pytest 플러그인 자동 로딩이 충돌할 수 있으므로 아래 명령을 표준으로 사용합니다.

```bash
cd /home/ssafy/smart-assembly-transport
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

기대 결과:

```text
16 passed
```

만약 그냥 `python3 -m pytest -q`로 실행했을 때 `launch_testing`, `anyio`, `yaml`, `pluggy` 관련 에러가 나오면 하드웨어 문제가 아니라 pytest 플러그인 충돌입니다. 다시 아래 명령으로 실행합니다.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

---

## 6. ROS2 워크스페이스 빌드

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
colcon build --event-handlers console_direct+
```

빌드 후:

```bash
cd /home/ssafy/smart-assembly-transport
source sem1_pjt_ws/install/setup.bash
```

---

## 7. 하드웨어 네트워크 / SSH 연결 확인

```bash
cd /home/ssafy/smart-assembly-transport
bash scripts/check_hardware_connections.sh
```

수동 확인:

```bash
ssh ssafy@192.168.110.142 'hostname && whoami'
```

```bash
ssh turtlebot4@192.168.110.174 'hostname && whoami'
```

둘 중 하나라도 접속이 안 되면 다음을 확인합니다.

- PC와 장비가 같은 네트워크에 있는지
- 장비 IP가 바뀌지 않았는지
- SSH 서버가 켜져 있는지
- 계정명/비밀번호가 맞는지
- `config/hardware.json` 주소가 현재 장비와 맞는지

---

## 8. Conveyor Raspberry Pi edge script 설치

컨베이어 Pi에 제어 스크립트를 복사합니다.

```bash
cd /home/ssafy/smart-assembly-transport

ssh ssafy@192.168.110.142 'mkdir -p ~/smart-assembly-transport-edge'

scp scripts/edge/conveyor_control.py \
  ssafy@192.168.110.142:~/smart-assembly-transport-edge/conveyor_control.py

ssh ssafy@192.168.110.142 \
  'chmod +x ~/smart-assembly-transport-edge/conveyor_control.py'
```

컨베이어 status 확인:

```bash
ssh ssafy@192.168.110.142 \
  'python3 ~/smart-assembly-transport-edge/conveyor_control.py status'
```

현재 컨베이어 스크립트는 두 모드를 지원합니다.

```text
CONVEYOR_MODE=digital  # 단일 GPIO ON/OFF, 릴레이/DC 모터 enable용
CONVEYOR_MODE=stepper  # STEP/DIR/ENABLE 스텝모터 드라이버용
```

`start` 때 GPIO 18에 연결된 서보가 움직였다면, 단일 digital 모드가 스텝모터가 아니라 서보 신호선을 건드린 것입니다. 기본 프로젝트 설정은 이를 피하기 위해 `config/hardware.json`의 `conveyor.remote_env`를 `stepper` 모드로 둡니다.

기본값:

```text
CONVEYOR_MODE=stepper
CONVEYOR_STEP_PIN=27
CONVEYOR_DIR_PIN=17
CONVEYOR_ENABLE_PIN=22
CONVEYOR_STEPS=800
CONVEYOR_STEP_DELAY_SEC=0.0001
CONVEYOR_ENABLE_ACTIVE_HIGH=0
CONVEYOR_DIR_ACTIVE_HIGH=0
CONVEYOR_GPIO_BACKEND=gpiod
```

실제 배선과 다르면 먼저 `config/hardware.json`에서 BCM GPIO 번호를 수정합니다.

먼저 통합 파이프라인이 아니라 독립 진단 스크립트로 서보/스텝모터를 확인합니다.

서보 좌/중앙/우 왕복 테스트:

```bash
ssh ssafy@192.168.110.142 \
  'python3 ~/smart-assembly-transport-edge/motor_diagnostic.py servo --servo-cycles 3 --hold-sec 0.8'
```

스텝모터 정방향/역방향 테스트:

```bash
ssh ssafy@192.168.110.142 \
  'python3 ~/smart-assembly-transport-edge/motor_diagnostic.py stepper --duration-sec 3 --delay-sec 0.0002 --pause-sec 1'
```

위 독립 테스트가 통과하면 기존 edge command도 확인합니다. `start`는 지정된 step 수만큼 pulse를 내는 동안 실행 중인 프로세스입니다. 이제 `stop`/`emergency-stop`은 별도 터미널에서 stop request 파일을 쓰고, 실행 중인 `start`가 이를 감지해 중간에 `STOPPED_BY_REQUEST`로 종료합니다.

긴 start를 걸어둔 뒤 다른 터미널에서 stop이 즉시 먹는지 테스트:

```bash
ssh ssafy@192.168.110.142 \
  'CONVEYOR_MODE=stepper CONVEYOR_STEP_PIN=27 CONVEYOR_DIR_PIN=17 CONVEYOR_ENABLE_PIN=22 CONVEYOR_ENABLE_ACTIVE_HIGH=0 CONVEYOR_DIR_ACTIVE_HIGH=0 CONVEYOR_GPIO_BACKEND=gpiod CONVEYOR_STEPS=200000 CONVEYOR_STEP_DELAY_SEC=0.0002 python3 ~/smart-assembly-transport-edge/conveyor_control.py start'
```

다른 터미널에서 정지 요청:

```bash
ssh ssafy@192.168.110.142 \
  'CONVEYOR_MODE=stepper CONVEYOR_STEP_PIN=27 CONVEYOR_DIR_PIN=17 CONVEYOR_ENABLE_PIN=22 CONVEYOR_ENABLE_ACTIVE_HIGH=0 CONVEYOR_DIR_ACTIVE_HIGH=0 CONVEYOR_GPIO_BACKEND=gpiod python3 ~/smart-assembly-transport-edge/conveyor_control.py stop'
```

비상정지 요청:

```bash
ssh ssafy@192.168.110.142 \
  'CONVEYOR_MODE=stepper CONVEYOR_STEP_PIN=27 CONVEYOR_DIR_PIN=17 CONVEYOR_ENABLE_PIN=22 CONVEYOR_ENABLE_ACTIVE_HIGH=0 CONVEYOR_DIR_ACTIVE_HIGH=0 CONVEYOR_GPIO_BACKEND=gpiod python3 ~/smart-assembly-transport-edge/conveyor_control.py emergency-stop'
```

정상이라면 첫 번째 터미널의 `start`가 전체 step 완료 전 `STOPPED_BY_REQUEST`로 끝납니다.

---

## 9. TurtleBot4 / Nav2 상태 확인

TurtleBot에 접속합니다.

```bash
ssh turtlebot4@192.168.110.174
```

TurtleBot 안에서 실행:

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot4_ws/install/setup.bash || true
export ROS_DOMAIN_ID=34
```

ROS2 node 확인:

```bash
ros2 node list
```

Nav2 action 확인:

```bash
ros2 action list | grep navigate
```

기대 결과:

```text
/navigate_to_pose
```

`/navigate_to_pose`가 보이지 않으면 TurtleBot4 bringup, map, localization, Nav2가 아직 준비되지 않은 상태입니다.

---

## 10. Dobot action 상태 확인

PC 터미널에서 ROS2 환경을 로딩한 뒤 action이 보이는지 확인합니다.

```bash
cd /home/ssafy/smart-assembly-transport
source /opt/ros/humble/setup.bash
source sem1_pjt_ws/install/setup.bash
ros2 action list | grep -E 'PTP|dobot|Dobot'
```

현재 설정 파일의 Dobot action 이름은 다음 값입니다.

```text
PTP_action
```

보이지 않는다면 Dobot ROS2 driver/action server가 아직 실행되지 않은 상태입니다.

---

## 11. 터미널에서 실제 파이프라인 dry-run 확인

장비를 움직이지 않고, 어떤 명령이 실행될지 먼저 확인합니다.

```bash
cd /home/ssafy/smart-assembly-transport
source /opt/ros/humble/setup.bash
source sem1_pjt_ws/install/setup.bash

python3 - <<'PY'
from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import HardwareConfig
from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.real_pipeline import RealHardwarePipeline

cfg = HardwareConfig.load()
pipeline = RealHardwarePipeline(cfg, execute=False)
events = pipeline.run_order_plan("A")

for e in events:
    if e["type"] == "factory.state":
        print("[STATE]", e["state"], "-", e["message"])
    elif e["type"] == "hardware.command_result":
        print("[CMD]", e["subsystem"], e["action"], "executed=", e["executed"])
        print("     ", " ".join(e["command"]) if isinstance(e["command"], list) else e["command"])
PY
```

확인할 핵심:

```text
executed= False
conveyor start
conveyor stop
dobot ptp_step_1 ...
turtlebot navigate_A
turtlebot return_HOME
```

---

## 12. Backend WebSocket server 실행

터미널 1에서 실행합니다.

```bash
cd /home/ssafy/smart-assembly-transport
source /opt/ros/humble/setup.bash
source sem1_pjt_ws/install/setup.bash
python3 -m server.app
```

기대 출력:

```text
WebSocket mission server listening on ws://127.0.0.1:8765
```

`websockets` 에러가 나오면:

```bash
python3 -m pip install --user websockets
```

---

## 13. Dashboard HTTP server 실행

터미널 2에서 실행합니다.

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m http.server 3000
```

브라우저에서 접속:

```text
http://127.0.0.1:3000/web/index.html
```

---

## 14. Dashboard에서 mock 흐름 확인

브라우저에서 다음 순서로 확인합니다.

```text
1. WebSocket 연결
2. STT/Mock 작업 시작
3. 다음 mock 이벤트 반복 클릭
4. RETURNED_HOME까지 진행되는지 확인
```

확인할 UI 영역:

- `RealSense D435i · YOLO 실시간 화면`
- `SLAM / TurtleBot 위치`
- `전체 진행상황`
- `STT 명령 확인`
- `생산성 지표`
- `작업 타임라인`
- `이벤트 / 하드웨어 로그`

비상정지 UI 확인:

```text
1. 손 감지 / 비상정지 클릭
2. WAIT_ADMIN_UNLOCK 상태 확인
3. 비상정지 횟수 증가 확인
4. 관리자 Unlock 클릭
5. 이전 흐름으로 복구되는지 확인
```

---

## 15. Dashboard에서 실제 하드웨어 dry-run 확인

실제 장비를 움직이기 전에 반드시 dry-run을 먼저 확인합니다.

브라우저에서:

```text
1. WebSocket 연결
2. 하드웨어 구성
3. 파이프라인 계획
4. 실제 명령 실행 모드 OFF 확인
5. 실제 order plan 실행
```

로그에서 확인:

```text
executed: false
```

이 단계에서는 실제 장비가 움직이면 안 됩니다.

---

## 16. 실제 실행 전 안전 체크리스트

실제 실행 모드를 켜기 전에 아래를 모두 확인합니다.

```text
[ ] 컨베이어 주변에 손/장애물이 없음
[ ] Dobot workspace 안에 사람 손이 없음
[ ] TurtleBot 이동 경로가 확보됨
[ ] TurtleBot localization/Nav2가 정상임
[ ] /navigate_to_pose action이 보임
[ ] E-stop 또는 전원 차단 수단이 바로 접근 가능함
[ ] dry-run에서 executed=false 명령 목록을 확인함
[ ] HOME/A/B 좌표가 실제 맵 기준으로 안전함
```

현재 기본 TurtleBot 목표 좌표:

```json
"HOME": {"x": 0.0, "y": 0.0, "yaw": 0.0}
"A": {"x": 1.2, "y": 0.0, "yaw": 0.0}
"B": {"x": 0.0, "y": 1.2, "yaw": 1.5708}
```

좌표가 실제 맵 기준으로 위험하면 먼저 [`config/hardware.json`](../config/hardware.json)을 수정합니다.

---

## 17. Dashboard에서 실제 하드웨어 실행

브라우저에서:

```text
1. WebSocket 연결
2. 하드웨어 구성
3. 파이프라인 계획
4. 실제 명령 실행 모드 ON
5. 실제 order plan 실행
```

이 단계부터 실제 SSH/ROS 명령이 전송됩니다.

---

## 18. 터미널에서 실제 하드웨어 실행

UI 없이 CLI에서 바로 실행할 수도 있습니다.

> 주의: 아래 명령은 실제 장비를 움직일 수 있습니다.

A 구역 실행:

```bash
cd /home/ssafy/smart-assembly-transport
source /opt/ros/humble/setup.bash
source sem1_pjt_ws/install/setup.bash

python3 - <<'PY'
from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import HardwareConfig
from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.real_pipeline import RealHardwarePipeline

cfg = HardwareConfig.load()
pipeline = RealHardwarePipeline(cfg, execute=True)
events = pipeline.run_order_plan("A")

for e in events:
    if e["type"] == "factory.state":
        print("[STATE]", e["state"], "-", e["message"])
    elif e["type"] == "hardware.command_result":
        print("[CMD]", e["subsystem"], e["action"], "executed=", e["executed"], "returncode=", e.get("returncode"))
        if e.get("stdout"):
            print("[STDOUT]", e["stdout"])
        if e.get("stderr"):
            print("[STDERR]", e["stderr"])
PY
```

B 구역 실행은 `run_order_plan("A")`를 `run_order_plan("B")`로 바꾸면 됩니다.

---

## 19. RealSense / YOLO 화면 확인

현재 UI에는 RealSense/YOLO 화면 표시 영역이 있습니다.

기본 스트림 URL:

```text
http://127.0.0.1:8080/stream?topic=/camera/camera/color/image_raw
```

브라우저에서:

```text
1. RealSense D435i · YOLO 실시간 화면 패널 확인
2. 스트림 URL 입력
3. 카메라 스트림 연결 클릭
```

아직 ROS image topic을 HTTP/MJPEG로 바꾸는 bridge가 실행 중이 아니라면 화면이 안 나오는 것이 정상입니다. 이 경우 다음 개발 단계에서 ROS image → MJPEG bridge를 추가해야 합니다.

---

## 20. 문제 발생 시 보고 형식

문제가 생기면 아래 형식으로 로그를 남깁니다.

```text
실패 단계:
실행 명령:
에러 로그:
실제 현상:
```

예시:

```text
실패 단계: TurtleBot navigate_A
실행 명령: UI에서 실제 order plan 실행
에러 로그: returncode=1, action server not available
실제 현상: TurtleBot이 움직이지 않음
```

분류 예시:

```text
1. SSH 연결 실패
2. 컨베이어 status 실패
3. 컨베이어 start 실패
4. 컨베이어 stop 실패
5. Dobot ptp_step_N 실패
6. TurtleBot /navigate_to_pose 없음
7. TurtleBot navigate_A/B 실패
8. TurtleBot return_HOME 실패
9. UI 상태 표시가 실제와 다름
10. RealSense 화면 안 나옴
```

---

## 21. 가장 짧은 전체 실행 순서

이미 코드 테스트까지 통과했다면 다음부터 진행합니다.

```bash
cd /home/ssafy/smart-assembly-transport

bash scripts/check_hardware_connections.sh

ssh ssafy@192.168.110.142 \
  'python3 ~/smart-assembly-transport-edge/conveyor_control.py status'

ssh turtlebot4@192.168.110.174 \
  'source /opt/ros/humble/setup.bash && source ~/turtlebot4_ws/install/setup.bash || true; export ROS_DOMAIN_ID=34; ros2 action list | grep navigate'
```

터미널 1:

```bash
cd /home/ssafy/smart-assembly-transport
source /opt/ros/humble/setup.bash
source sem1_pjt_ws/install/setup.bash
python3 -m server.app
```

터미널 2:

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m http.server 3000
```

브라우저:

```text
http://127.0.0.1:3000/web/index.html
```

Dashboard:

```text
WebSocket 연결
→ 하드웨어 구성
→ 파이프라인 계획
→ 실제 명령 실행 모드 OFF
→ 실제 order plan 실행
```

여기까지 문제가 없으면, 안전 체크 후 `실제 명령 실행 모드 ON`으로 실제 실행합니다.
