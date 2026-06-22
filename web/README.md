# Web Dashboard

하드웨어 없이 `server/app.py`의 WebSocket mock server와 연결해서 공정 상태 UI를 확인할 수 있습니다.

## 실행 방법

터미널 1:

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m server.app
```

터미널 2:

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m http.server 3000
```

브라우저에서 접속:

```text
http://127.0.0.1:3000/web/index.html
```

## 확인 순서

1. `WebSocket 연결` 클릭
2. `작업 시작` 클릭
3. `다음 mock 이벤트`를 반복 클릭해서 공정이 `RETURNED_HOME`까지 진행되는지 확인
4. 중간에 `손 감지 / 비상정지` 클릭 시 `WAIT_ADMIN_UNLOCK` 상태가 되는지 확인
5. `관리자 Unlock` 클릭 후 이전 상태로 복구되는지 확인

## 실제 하드웨어 연동 확인

UI에는 실제 하드웨어용 버튼도 있습니다.

- `실제 하드웨어 구성 불러오기`: `config/hardware.json`의 Conveyor Pi, TurtleBot4, Dobot, Vision 설정 표시
- `실제 파이프라인 계획 보기`: 실제로 전송할 SSH/ROS/Dobot 계획을 DRY-RUN으로 표시
- `실제 order plan 실행`: `실제 명령 실행 모드`가 꺼져 있으면 DRY-RUN, 켜져 있으면 SSH 명령 전송

장비 설정:

```text
Conveyor Pi: ssafy@192.168.110.142
TurtleBot4: turtlebot4@192.168.110.174
TurtleBot ROS_DOMAIN_ID: 34
```

실제 실행 전에 `docs/14-real-hardware-runbook.md`를 먼저 확인하세요.
