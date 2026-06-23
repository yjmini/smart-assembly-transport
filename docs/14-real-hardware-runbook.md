# 14. 실제 하드웨어 연동 실행 가이드

이 브랜치는 mock 흐름 위에 실제 연결 대상 설정과 SSH/ROS 2 command layer를 추가합니다.

## 장비 주소

| 장비 | SSH target | 비고 |
|---|---|---|
| Conveyor Raspberry Pi | `ssafy@192.168.110.142` | `scripts/edge/conveyor_control.py` 설치 필요 |
| TurtleBot4 | `turtlebot4@192.168.110.174` | `ROS_DOMAIN_ID=34` 사용 |

설정 원본은 `config/hardware.json`입니다.

## 1. 네트워크/SSH 확인

```bash
cd /home/ssafy/smart-assembly-transport
bash scripts/check_hardware_connections.sh
```

## 2. 컨베이어 Pi에 edge script 설치

```bash
ssh ssafy@192.168.110.142 'mkdir -p ~/smart-assembly-transport-edge'
scp scripts/edge/conveyor_control.py ssafy@192.168.110.142:~/smart-assembly-transport-edge/conveyor_control.py
ssh ssafy@192.168.110.142 'chmod +x ~/smart-assembly-transport-edge/conveyor_control.py'
```

`conveyor_control.py`는 두 가지 모드를 지원합니다.

- `CONVEYOR_MODE=digital`: 단일 GPIO ON/OFF 방식입니다. 릴레이/DC 모터 enable에는 맞지만, STEP/DIR 방식 스텝모터에는 맞지 않습니다.
- `CONVEYOR_MODE=stepper`: project_pill의 컨베이어가 `/conveyor/*/speed` 명령으로 일정 방향 속도를 주는 패턴을 실제 GPIO에 맞게 변환한 방식입니다. `start` 명령에서 STEP 핀에 정해진 수만큼 pulse를 주고, `stop`/`emergency-stop`은 enable을 끕니다.

현재 기본 설정은 `config/hardware.json`의 `conveyor.remote_env`에 있습니다.

```json
"CONVEYOR_MODE": "stepper",
"CONVEYOR_STEP_PIN": "27",
"CONVEYOR_DIR_PIN": "17",
"CONVEYOR_ENABLE_PIN": "22",
"CONVEYOR_STEPS": "800",
"CONVEYOR_STEP_DELAY_SEC": "0.0001",
"CONVEYOR_ENABLE_ACTIVE_HIGH": "0",
"CONVEYOR_DIR_ACTIVE_HIGH": "0",
"CONVEYOR_GPIO_BACKEND": "gpiod"
```

실제 배선이 다르면 `CONVEYOR_STEP_PIN`, `CONVEYOR_DIR_PIN`, `CONVEYOR_ENABLE_PIN`을 먼저 수정해야 합니다. GPIO 번호는 Raspberry Pi **BCM 번호** 기준입니다.

## 3. Backend/UI 실행

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m server.app
```

다른 터미널:

```bash
python3 -m http.server 3000
```

브라우저:

```text
http://127.0.0.1:3000/web/index.html
```

## 4. 안전한 dry-run 확인

Dashboard의 `실제 하드웨어 구성 불러오기`와 `실제 파이프라인 계획 보기`는 장비에 명령을 보내지 않습니다. 실제로 실행할 SSH/ROS command를 UI 로그에서 확인할 수 있습니다.

## 5. TurtleBot Nav2 배송 단독 dry-run/실행

조립 완료품이 TurtleBot에 적재된 뒤, 사용자가 지정한 SLAM map 위치로 Nav2 이동 → 3초 정지 → HOME 복귀만 따로 검증할 수 있습니다.

Dry-run으로 실제 전송될 SSH/ROS 명령 확인:

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m sem1_pjt_ws.src.turtlebot_delivery.turtlebot_delivery.delivery_round_trip A
```

실제 실행:

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m sem1_pjt_ws.src.turtlebot_delivery.turtlebot_delivery.delivery_round_trip A --execute
```

`A`, `B`, `HOME` 좌표와 목적지 대기 시간은 `config/hardware.json`의 `turtlebot.targets`, `turtlebot.home_destination`, `turtlebot.delivery_dwell_sec`에서 조정합니다. ROS 2 workspace를 빌드/소스한 환경에서는 console script도 사용할 수 있습니다.

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
colcon build --packages-select turtlebot_delivery
source install/setup.bash
turtlebot-delivery-round-trip A --execute
```

## 6. 실제 실행

Dashboard에서 `실제 명령 실행 모드`를 켠 뒤 `실제 order plan 실행`을 누르면 SSH 명령이 실제로 전송됩니다. 이 단계 전에 반드시:

- 컨베이어 주변 안전 확보
- Dobot workspace에서 사람 손 제거
- TurtleBot 지도/Localization/Nav2 bringup 확인
- E-stop 접근 가능 상태 확인

을 완료해야 합니다.
