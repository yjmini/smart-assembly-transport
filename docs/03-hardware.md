# 03. 하드웨어 구성

## 하드웨어 목록

| 장비 | 역할 | 검증 항목 |
|---|---|---|
| Ubuntu PC | ROS 2 메인 제어, 비전, 백엔드, 대시보드 | ROS 2 실행, 카메라 인식, 네트워크 |
| Raspberry Pi 5 | 컨베이어 제어 | GPIO/Modbus/Serial 제어, start/stop |
| Conveyor | 베이스/완성품 이송 | 속도, 정지 응답성, 모터 제어 |
| RealSense/RGBD Camera | 부품/손/QC 인식 | RGB/depth 프레임, 좌표 변환 |
| Dobot Magician | 조립 및 적재 | bringup, PTP 제어, gripper/suction |
| TurtleBot3 | 무인 배송 | bringup, SLAM, Nav2, goal 이동 |
| Speaker/Microphone | STT/TTS HRI | 음성 입력, 완료/경고 출력 |

## 우선 검증 순서

1. Ubuntu PC에서 ROS 2 workspace build 가능 여부 확인
2. RealSense 또는 사용 카메라 입력 확인
3. 컨베이어 start/stop 단품 테스트
4. Dobot 단품 PTP 이동 테스트
5. TurtleBot3 bringup 및 Nav2 goal 테스트
6. 모든 장비를 같은 네트워크/ROS_DOMAIN_ID 기준으로 통합

## 안전 관련 하드웨어 고려사항

- 컨베이어와 Dobot은 비상 상황에서 즉시 정지 가능한 명령 경로를 가져야 한다.
- 가능하면 소프트웨어 STOP 외에 물리 전원 차단 또는 물리 STOP도 준비한다.
- 사람 손 감지 테스트는 저속/무부하 상태에서 먼저 수행한다.
- Dobot 작업 반경과 TurtleBot 이동 경로를 분리해 충돌 가능성을 줄인다.

## 미확정 항목

- 컨베이어 제어 방식: GPIO, Modbus, RS232 중 실제 장비 기준 확정 필요
- 카메라 설치 위치와 캘리브레이션 방식
- Dobot gripper/end-effector 형태
- TurtleBot 적재함 구조와 제품 고정 방식
