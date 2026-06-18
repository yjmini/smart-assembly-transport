# 1주일 프로젝트 진행 계획

> 목표: 7일 안에 “음성 명령 → 컨베이어 정지 → Dobot 조립 → QC/적재 → TurtleBot 배송 → TTS/대시보드 완료 보고”가 보이는 MVP를 만든다.

## 전략

기간이 1주일이므로 모든 기능을 완성형으로 만들기보다, **ROS 2 인터페이스와 FSM을 먼저 고정**하고 각 기능을 mock/sim/real 단계로 끌어올린다.

우선순위는 다음과 같다.

1. 안전 정지 FSM
2. ROS 2 통합 오케스트레이션
3. 컨베이어/비전/Dobot/TurtleBot 단품 동작
4. End-to-end 데모
5. 웹 대시보드/통계 고도화

## Day 1 — 저장소/요구사항/아키텍처 고정

**목표:** 팀이 같은 인터페이스로 병렬 개발할 수 있게 만든다.

- GitHub repo 기본 문서, WBS, 아키텍처 작성
- 기존 로컬 자산 조사
  - `homework_ws/0520_conveyor`: 컨베이어 제어 예제
  - `homework_ws/0519_Dobot_integration`, `magician_ros2_control_system_ws`: Dobot 제어
  - `turtlebot3_ws`, `homework_ws/0513_SLAM`, `0514_NAV2`: TurtleBot SLAM/Nav2
  - `yolov5`, `homework_ws/0602_custom_yolo`: 비전/YOLO
- ROS 2 패키지 구조 결정
- FSM 상태, topic/action/service 이름 확정
- GitHub Issues/Kanban 백로그 생성

**완료 기준:** README, 아키텍처, WBS, Kanban 이슈가 repo에 존재한다.

## Day 2 — Mission Orchestrator + Mock E2E

**목표:** 실제 하드웨어 없이 전체 상태 흐름을 먼저 통과시킨다.

- `mission_orchestrator` 패키지 생성
- 작업 오더 입력 CLI 또는 간단한 REST/WebSocket bridge 작성
- 컨베이어, 비전, Dobot, TurtleBot mock 노드 작성
- FSM 정상 흐름 구현
- HAND_DETECTED 인터럽트 → EMERGENCY_STOP 상태 구현
- 관리자 비밀번호 해제 mock 구현

**완료 기준:** 한 명령으로 mock end-to-end 로그가 `DELIVERED`까지 진행된다.

## Day 3 — Vision + Conveyor 단품 통합

**목표:** 베이스 부품 감지와 사람 손 감지로 컨베이어를 멈추는 핵심 장면을 만든다.

- YOLOv5 또는 OpenCV ROI 기반 베이스 부품 감지 MVP
- 사람 손 감지 클래스/모델 또는 임시 OpenCV/YOLO 클래스 연결
- RealSense/RGBD 카메라 입력 확인
- Raspberry Pi 5 컨베이어 start/stop 노드 이식
- Vision 이벤트가 Orchestrator의 컨베이어 stop과 emergency stop을 트리거하도록 연결

**완료 기준:** 카메라 감지 이벤트로 컨베이어 정지/비상정지가 재현된다.

## Day 4 — Dobot 조립 루틴 통합

**목표:** 정지된 베이스 위에 1~2단계 pick/place 루틴을 수행한다.

- Dobot bringup/driver 실행 절차 정리
- PTP 또는 Action Client 기반 pick/place 함수 작성
- 좌표는 초기에는 고정 좌표로 시작하고, 가능하면 Vision-to-TF 좌표로 확장
- stage1, stage2 순차 조립 상태를 FSM에 연결
- Action feedback/result로 다음 상태 전이

**완료 기준:** Orchestrator 명령으로 Dobot이 최소 1개 이상의 조립 동작을 수행한다.

## Day 5 — TurtleBot 배송 + TTS 연결

**목표:** 완성품 적재 후 목적지까지 이동하고 완료 보고를 한다.

- TurtleBot3 SLAM 지도/기존 map 확인
- Nav2 goal sender 노드 작성
- 목적지 A/B/C 좌표 config 작성
- TurtleBot 도착 result를 FSM에 연결
- TTS 완료 안내 연결

**완료 기준:** `destination=A` 작업 오더가 TurtleBot Nav2 goal로 변환되고 도착 이벤트가 기록된다.

## Day 6 — Dashboard/Backend + 통합 리허설

**목표:** 사람이 보기 쉬운 데모 화면과 로그를 만든다.

- Node.js 또는 Django 중 실제 구현 비용이 낮은 쪽으로 backend 최소 구현
- WebSocket으로 FSM 상태 이벤트 송신
- Vue dashboard: 주문 카드, 현재 상태, emergency modal, unlock form
- Chart.js는 간단한 완료/실패 count 정도만 구현
- 실제 하드웨어 가능한 부분과 mock fallback을 혼합해 end-to-end 리허설

**완료 기준:** 대시보드에서 작업 시작/상태 변화/비상 정지/해제/완료를 확인할 수 있다.

## Day 7 — 안정화/촬영/발표 산출물

**목표:** 실패 가능성을 줄이고 제출 가능한 결과물을 만든다.

- 전체 데모 스크립트 작성
- 하드웨어 실패 시 mock fallback 시나리오 준비
- README 실행 방법 업데이트
- 아키텍처 다이어그램/WBS/R&R 정리
- 데모 영상 촬영
- 발표용 핵심 시나리오 정리

**완료 기준:** 3회 연속 데모 리허설 중 최소 2회 성공, 실패 시 원인과 fallback 설명 가능.

## 병렬 개발 레인

| Lane | 담당 범위 | 산출물 |
|---|---|---|
| Orchestration/Safety | ROS 2 FSM, 비상 정지, 재개 | `mission_orchestrator` |
| Vision/AI | 베이스/부품/손/QC 감지 | `vision_detector`, model/config |
| Manufacturing Control | 컨베이어, Dobot 조립/적재 | `conveyor_controller`, `dobot_*` |
| Mobile Robot | TurtleBot SLAM/Nav2 배송 | `turtlebot_delivery` |
| Web/HRI | STT/TTS, Backend, Dashboard | API, WebSocket, Vue UI |
| Integration/Docs | 통합 테스트, README, 발표자료 | demo script, WBS, architecture |

## 리스크와 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 하드웨어 연결 지연 | 통합 데모 실패 | mock 노드와 실제 노드를 같은 인터페이스로 교체 가능하게 설계 |
| YOLO 학습 시간 부족 | 비전 인식 불안정 | Day 3 MVP는 ROI/OpenCV 또는 소량 클래스부터 시작 |
| Dobot 좌표 변환 오차 | 조립 실패 | 초기에는 고정 좌표 pick/place, 이후 TF 보정 |
| TurtleBot 지도/위치 추정 불안정 | 배송 실패 | 짧은 경로 + 사전 맵 + 수동 초기 pose 절차 문서화 |
| 웹 기능 과투자 | 로봇 통합 시간 부족 | Dashboard는 상태 카드/비상해제/완료로그만 MVP |

## 매일 검증 명령/기록 원칙

- 각 레인은 매일 최소 1개 실행 로그 또는 데모 영상을 남긴다.
- 통합 레인은 매일 `docs/integration-log/YYYY-MM-DD.md`를 업데이트한다.
- `main`은 항상 문서/실행 절차가 맞는 상태로 유지한다.
