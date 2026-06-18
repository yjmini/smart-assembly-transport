# 10. 위험 요소 및 대응

## 위험 매트릭스

| # | 위험 | 영향 | 대응 |
|---|---|---|---|
| R1 | 1주일 일정이 매우 짧음 | 전체 기능 미완성 | mock E2E를 먼저 만들고 real node를 순차 교체 |
| R2 | 컨베이어 제어 방식 미확정 | 공정 시작/정지 실패 | GPIO/Modbus/RS232 중 실제 장비 기준 Day3 전 확정 |
| R3 | Vision 인식 불안정 | 정위치 정지/QC 실패 | 초기에는 ROI/OpenCV 또는 소량 클래스 YOLO로 단순화 |
| R4 | Dobot 좌표 변환 오차 | 조립 실패 | 첫 구현은 고정 좌표, 이후 depth/TF 확장 |
| R5 | TurtleBot Nav2 불안정 | 배송 실패 | 짧은 경로, 사전 맵, 수동 초기 pose 절차 준비 |
| R6 | STT/TTS 지연 또는 실패 | HRI 완성도 저하 | Dashboard 수동 입력/텍스트 알림 fallback |
| R7 | 통합 시 장비 충돌 위험 | 안전 문제 | 저속 테스트, 작업 반경 분리, emergency stop 우선 구현 |
| R8 | Dashboard 과투자 | 로봇 통합 시간 부족 | MVP는 상태 카드/비상 모달/완료 로그만 구현 |

## 우선 검증 체크리스트

- [ ] ROS 2 workspace build 가능
- [ ] 카메라 입력 확인
- [ ] 컨베이어 start/stop 단품 확인
- [ ] Dobot PTP 단품 확인
- [ ] TurtleBot Nav2 goal 단품 확인
- [ ] mock E2E 공정 완료
- [ ] HAND_DETECTED emergency stop 확인
- [ ] Dashboard에서 상태 이벤트 수신 확인

## 범위 축소 기준

일정이 밀리면 다음 순서로 축소한다.

1. Chart.js 등 통계 고도화 제외
2. QC를 단순 정상/불량 플래그로 축소
3. Vision-to-TF를 고정 좌표로 대체
4. 실제 STT를 수동 텍스트 오더로 대체
5. TurtleBot 실제 주행을 RViz/Nav2 시뮬레이션으로 대체

단, **비상 정지 흐름과 전체 공정 상태 흐름은 유지**한다.
