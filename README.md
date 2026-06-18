# smart-assembly-transport

STT 연동 컨베이어-로봇팔 동적 조립 및 모바일 로봇 무인 배송 체계

## 목표

작업자의 자연어 음성 명령을 시작점으로 삼아 다음 end-to-end 공정을 1주일 MVP로 구현한다.

1. STT로 작업 오더 생성
2. 컨베이어 구동 및 YOLO 기반 베이스 부품 정위치 감지
3. 사람 손 감지 시 즉시 비상 정지 및 관리자 비밀번호 복구
4. Dobot 로봇팔 다단계 조립
5. 비전 기반 QC 후 TurtleBot 적재
6. TurtleBot Nav2 배송
7. TTS와 웹 대시보드로 상태 보고

## 참고 로컬 자산

이 저장소는 새 프로젝트 저장소이며, 아래 로컬 폴더와 기존 GitHub 자료를 참고/이식 대상으로 사용한다.

- `/home/ssafy/ssafy_ws`
- `/home/ssafy/homework_ws`
- `/home/ssafy/magician_ros2_control_system_ws`
- `/home/ssafy/turtlebot3_ws`
- `/home/ssafy/yolov5`
- <https://github.com/yjmini/robot_study>
- <https://github.com/yjmini/backup_ssafy4/tree/main/works_15th>

## 문서

- [1주일 진행 계획](docs/WEEK1_PLAN.md)
- [시스템 아키텍처](docs/ARCHITECTURE.md)
- [WBS / Kanban 작업 분해](docs/WBS.md)

## 기본 개발 원칙

- 시뮬레이션/스텁 → 단품 하드웨어 테스트 → 통합 테스트 순서로 진행
- ROS 2 인터페이스를 먼저 고정하고 각 서브시스템을 병렬 개발
- 안전 정지 FSM을 MVP 최우선 기능으로 취급
- 매일 종료 시 `main`에 동작 가능한 상태를 유지하거나 PR 단위로 검증
