# 04. 기술 스택

## Core

| 영역 | 기술 | 용도 |
|---|---|---|
| OS/Middleware | Ubuntu, Raspbian, ROS 2 | 메인 PC/라즈베리파이/로봇 분산 제어 |
| Language | Python, C/C++ | ROS 2 노드, 비전, 장비 제어 |
| Vision/AI | YOLOv5, OpenCV, PyTorch, NumPy | 부품/손/완성품 인식, QC |
| Robot Arm | Dobot ROS 2 packages, PTP control | 조립 및 적재 |
| Mobile Robot | TurtleBot3, SLAM, Nav2 | 목적지 무인 배송 |
| Web/HRI | Backend API, WebSocket, Vue/React | 작업 상태 모니터링, 비상 복구 UI |
| Voice | STT, TTS | 음성 명령 및 완료/경고 안내 |
| Communication | ROS 2 DDS, TCP, Modbus/RS232/GPIO | 서브시스템 간 통신 및 장비 제어 |

## 참고 코드 자산

| 경로 | 활용 가능 내용 |
|---|---|
| `/home/ssafy/ssafy_ws` | ROS 2 실습 패키지, TF/센서/통합 예제 |
| `/home/ssafy/homework_ws/0520_conveyor` | 컨베이어 제어 예제 |
| `/home/ssafy/homework_ws/0519_Dobot_integration` | Dobot 연동 예제 |
| `/home/ssafy/magician_ros2_control_system_ws` | Dobot ROS 2 제어 패키지 |
| `/home/ssafy/turtlebot3_ws` | TurtleBot3 bringup, cartographer, navigation2 |
| `/home/ssafy/yolov5` | YOLOv5 학습/추론 코드 |

## 개발 환경 원칙

- ROS 2 패키지는 `ros2_ws/src` 아래 기능별 패키지로 분리한다.
- Python 의존성은 모듈별 `requirements.txt` 또는 `pyproject.toml`로 관리한다.
- 장비별 IP, 포트, 목적지 좌표, 안전 비밀번호는 코드에 하드코딩하지 않고 설정 파일/env로 분리한다.
- 실제 장비 연결 전에는 mock 노드로 인터페이스를 먼저 검증한다.
