# Web Dashboard

하드웨어 없이 `server/app.py`의 WebSocket mock server와 연결해서 공정 상태 UI를 확인할 수 있습니다.

## 실행 방법

터미널 1:

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m server.app
```

터미널 2 — RealSense MJPEG 브릿지:

```bash
cd /home/ssafy/smart-assembly-transport
scripts/start_realsense_stream.sh
```

터미널 3:

```bash
cd /home/ssafy/smart-assembly-transport
python3 -m http.server 3001
```

브라우저에서 접속:

```text
http://127.0.0.1:3001/web/index.html
```

## 확인 순서

1. `WebSocket 연결` 클릭
2. `STT/Mock 작업 시작` 클릭
3. `다음 mock 이벤트`를 반복 클릭해서 공정이 `RETURNED_HOME`까지 진행되는지 확인
4. 상단 생산성 지표, 전체 진행상황, STT 명령 확인, SLAM/TurtleBot 위치가 같이 갱신되는지 확인
5. 중간에 `손 감지 / 비상정지` 클릭 시 `WAIT_ADMIN_UNLOCK` 상태와 비상정지 횟수가 반영되는지 확인
6. `관리자 Unlock` 클릭 후 이전 상태로 복구되는지 확인

## 운영 화면 구성

- `RealSense D435i · YOLO 실시간 화면`: `scripts/start_realsense_stream.sh`가 `/camera/camera/color/image_raw`를 `http://127.0.0.1:8080/stream?topic=/camera/camera/color/image_raw` MJPEG로 브릿지합니다. 기본은 raw `sensor_msgs/Image`입니다. compressed 토픽이 따로 있을 때만 `REALSENSE_COLOR_TOPIC=/camera/camera/color/image_raw/compressed REALSENSE_COMPRESSED=1 scripts/start_realsense_stream.sh`처럼 실행합니다. Fast DDS shared-memory lock 경고는 토픽 데이터가 나오면 무시해도 되며, 정말 통신이 막힐 때만 `USE_FASTDDS_NO_SHM=1`로 UDP-only 프로파일을 적용하세요. 대시보드는 기본으로 이 URL을 자동 연결하고, `vision.detections` 또는 `vision.detection` WebSocket 메시지를 받으면 bounding box와 객체 목록을 실시간 오버레이합니다.
- `SLAM / TurtleBot 위치`: `map/pjt_map.pgm`에서 만든 지도 중 사용자가 직접 잘라낸 `map/pjt_map_view_crop.png`를 기본으로 로드합니다. 이 이미지는 지도 영역만 최대한 남긴 dashboard용 지도이며, 하늘색 화살표는 TurtleBot 현재 pose, 초록색 원은 HOME, 빨간색 A 원/파란색 B 원은 사용자가 지정한 배송 목적지를 표시합니다. 다른 PNG 지도를 쓰려면 지도 URL 입력칸을 바꾸고 `SLAM 지도 로드`를 누르세요.
- `전체 진행상황`: 조립·검사·적재·배송·복귀 단계별 상태를 표시합니다.
- `STT 명령 확인`: Whisper STT transcript를 UI에 표시하고, 최종 인식 문장을 `speech.stt.final` / `whisper.transcript` 이벤트로 받아 작업 시작 또는 비상정지 명령에 반영합니다.
- `TTS 안내`: 작업 접수, 비상정지, 배송 완료, 복귀 완료 시 안내 문장을 UI에 표시하고 브라우저 TTS로 재생합니다. 외부 TTS 노드는 `speech.tts.speaking`, `speech.tts.done` 이벤트를 보내 같은 패널 상태를 갱신할 수 있습니다.
- `생산성 지표`: 완료 사이클, 조립 완료 수량, 배송 완료 횟수, 비상정지 횟수를 표시합니다.

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
