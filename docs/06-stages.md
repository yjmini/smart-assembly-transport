# 06. 단계별 목표

본 프로젝트는 1주일 MVP를 기준으로 단계별로 구현한다.

## 1단계 — 설계 및 인터페이스 고정

### 산출물

- 문서 구조 정리
- FSM 상태 정의
- ROS 2/WebSocket/API 인터페이스 초안
- GitHub Issues 기반 Kanban 작업 목록

### 완료 기준

- [ ] `docs/` 문서 인덱스 존재
- [ ] FSM 상태와 안전 전이 정의
- [ ] 각 모듈의 책임 경계 정의
- [ ] Day별 작업 이슈 생성

## 2단계 — Mock End-to-End 공정

### 산출물

- Mission Orchestrator 기본 FSM
- mock conveyor, mock vision, mock dobot, mock turtlebot
- 작업 오더 입력 후 `DELIVERED`까지 진행되는 로그

### 완료 기준

- [ ] 실제 장비 없이 전체 공정 상태가 순서대로 전이
- [ ] `HAND_DETECTED` 이벤트로 `EMERGENCY_STOP` 진입
- [ ] 관리자 해제 후 재개 또는 안전 재시작 가능

## 3단계 — Vision + Conveyor

### 산출물

- 카메라 기반 베이스 부품 감지
- 사람 손 감지 이벤트
- 컨베이어 start/stop 제어
- 비전 이벤트에 따른 컨베이어 정지

### 완료 기준

- [ ] 베이스 부품 정위치 감지 이벤트 발생
- [ ] 감지 후 컨베이어 정지
- [ ] 손 감지 시 공정 비상 정지

## 4단계 — Dobot 조립/적재

### 산출물

- Dobot bringup 절차
- 고정 좌표 기반 pick/place
- 1단계/2단계 조립 루틴
- TurtleBot 적재 루틴

### 완료 기준

- [ ] Dobot 단품 PTP 동작
- [ ] Orchestrator 명령으로 조립 루틴 실행
- [ ] Action result로 다음 FSM 상태 전이

## 5단계 — TurtleBot 배송

### 산출물

- 목적지 좌표 config
- Nav2 goal sender
- 도착 이벤트 처리
- TTS 완료 안내

### 완료 기준

- [ ] `destination=A`가 Nav2 goal로 변환
- [ ] TurtleBot 도착 상태 수신
- [ ] 완료 안내 출력

## 6단계 — Dashboard 및 통합 리허설

### 산출물

- 주문 카드와 현재 상태 표시
- 비상 정지 모달
- 관리자 unlock 입력
- 통합 리허설 로그

### 완료 기준

- [ ] Dashboard에서 상태 변화 확인
- [ ] 비상 정지/해제 흐름 확인
- [ ] 실제 장비 + mock fallback 혼합 데모 가능

## 7단계 — 최종 데모 정리

### 산출물

- 데모 스크립트
- fallback 시나리오
- 발표 자료/영상
- 실행 방법 문서

### 완료 기준

- [ ] 3회 리허설 중 최소 2회 성공
- [ ] 실패 시 fallback 설명 가능
- [ ] README와 docs가 실제 상태와 일치
