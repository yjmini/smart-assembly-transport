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

`conveyor_control.py` 안의 GPIO/PWM TODO는 실제 모터 드라이버 배선에 맞게 수정해야 합니다.

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

## 5. 실제 실행

Dashboard에서 `실제 명령 실행 모드`를 켠 뒤 `실제 order plan 실행`을 누르면 SSH 명령이 실제로 전송됩니다. 이 단계 전에 반드시:

- 컨베이어 주변 안전 확보
- Dobot workspace에서 사람 손 제거
- TurtleBot 지도/Localization/Nav2 bringup 확인
- E-stop 접근 가능 상태 확인

을 완료해야 합니다.
