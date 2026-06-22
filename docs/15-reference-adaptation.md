# 15. project_pill 참고 고도화 적용 기준

## 목적

`/home/ssafy/project_pill`은 이 프로젝트의 최종 산출물이 아니라, 다른 사람이 만든 유사 로봇-웹-Gazebo 통합 프로젝트의 참고 자료다. 따라서 약품/병동 배송 도메인을 그대로 가져오지 않고, 다음 통합 패턴만 `자동 조립 공정 및 무인 배송 시스템`에 맞게 적용한다.

## 참고해서 적용한 패턴

| project_pill에서 참고한 패턴 | 우리 프로젝트 적용 방식 |
|---|---|
| 웹에서 전체 공정 checkpoint를 명확히 보여줌 | `hardware.pipeline` 응답에 발표용 phase 목록 추가 |
| 배송 후 로봇이 시작 위치로 복귀 | TurtleBot 배송 완료 후 `RETURNING_HOME → RETURNED_HOME` 상태 추가 |
| Gazebo/실기 실행 전 dry-run으로 명령 흐름 확인 | `hardware.run_order_plan`은 기본 dry-run 유지 |
| 웹/백엔드/ROS2/로봇 사이의 명령 경로를 명시 | phase별 gate/event를 `real_pipeline.demo_phases()`로 노출 |
| 하드웨어/시뮬레이션 분리 | `mock` FSM과 `real` adapter interface 유지 |

## 현재 고도화된 공정 흐름

```text
작업 오더 수신
  → 컨베이어 이동
  → 비전 정위치 감지
  → 컨베이어 정지
  → Dobot 2단계 자동 조립
  → 비전 품질 확인
  → Dobot이 TurtleBot에 적재
  → TurtleBot 목적지 배송
  → TurtleBot 시작 위치 복귀
  → 다음 작업 대기
```

FSM 상태 기준:

```text
ORDER_RECEIVED
→ CONVEYOR_MOVING
→ BASE_DETECTED_STOPPING
→ ASSEMBLY_STAGE_1
→ ASSEMBLY_STAGE_2
→ QC_CHECK
→ LOADING_TO_TURTLEBOT
→ DELIVERY_NAVIGATING
→ DELIVERED
→ RETURNING_HOME
→ RETURNED_HOME
```

## 실제 하드웨어 테스트 시 확인할 것

1. `hardware.run_order_plan`을 먼저 dry-run으로 실행한다.
2. 로그에 다음 명령이 모두 보이는지 확인한다.
   - conveyor `start`
   - conveyor `stop`
   - Dobot `ptp_step_*`
   - TurtleBot `navigate_A` 또는 `navigate_B`
   - TurtleBot `return_HOME`
3. 실제 실행 모드를 켜기 전에는 컨베이어와 TurtleBot 주변 안전 공간을 확보한다.
4. 실제 테스트 후 실패한 지점을 아래 중 하나로 알려주면 된다.
   - SSH 연결 실패
   - 컨베이어 start/stop 실패
   - Dobot action 실패
   - 비전 gate가 실제로 들어오지 않음
   - TurtleBot 목적지 이동 실패
   - TurtleBot HOME 복귀 실패
   - 대시보드 상태 표시 불일치

## 주의

- 약품명, 병동, 재고 DB, 처방 UI는 우리 프로젝트의 목표가 아니므로 그대로 이식하지 않는다.
- 필요한 경우에는 `제품/부품 종류`, `조립 단계`, `배송 구역` 개념으로 변환해서만 참고한다.
