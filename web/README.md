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
3. `다음 mock 이벤트`를 반복 클릭해서 공정이 `DELIVERED`까지 진행되는지 확인
4. 중간에 `손 감지 / 비상정지` 클릭 시 `WAIT_ADMIN_UNLOCK` 상태가 되는지 확인
5. `관리자 Unlock` 클릭 후 이전 상태로 복구되는지 확인

현재 UI는 실제 대시보드 구현 전 mock 확인용입니다.
