# 08. STT/TTS 설계

## 목표

작업자가 자연어로 공정 명령을 내리고, 시스템은 공정 상태와 완료/경고를 음성으로 피드백한다.

## 음성 명령 흐름

```text
마이크 입력
  → STT
  → 명령 텍스트
  → 의도/목적지 파싱
  → 작업 오더 생성
  → Mission Orchestrator 전달
```

## 명령 카탈로그 초안

| 발화 예시 | 의도 | 파라미터 |
|---|---|---|
| 제품 조립 후 A구역으로 배송해 | create_order | destination=A |
| B구역으로 보내줘 | create_order | destination=B |
| 공정 정지 | emergency_stop | - |
| 멈춰 | emergency_stop | - |
| 다시 시작 | request_resume | - |
| 현재 상태 알려줘 | query_status | - |

## TTS 출력 예시

| 상황 | 출력 문장 |
|---|---|
| 작업 시작 | 작업 오더를 접수했습니다. 조립 공정을 시작합니다. |
| 비상 정지 | 사람 손이 감지되어 공정을 정지합니다. |
| 복구 완료 | 관리자 승인이 확인되었습니다. 공정을 재개합니다. |
| 배송 완료 | A구역 배송을 완료했습니다. |
| 오류 | 장비 상태를 확인해 주세요. |

## 안전 명령 처리 원칙

- “정지”, “멈춰”, “stop” 등 안전 키워드는 LLM/복잡한 파싱을 거치지 않고 즉시 비상 정지로 처리한다.
- STT 실패 시 Dashboard STOP 버튼으로 동일한 정지 동작이 가능해야 한다.
- TTS 실패는 공정 중단 사유가 아니지만 Dashboard에는 반드시 경고를 남긴다.

## fallback

| 실패 상황 | fallback |
|---|---|
| STT 인식 실패 | Dashboard 수동 오더 입력 |
| TTS 출력 실패 | Dashboard 알림으로 대체 |
| 자연어 파싱 실패 | 목적지 선택 UI로 대체 |
| 마이크 노이즈 | push-to-talk 또는 고정 명령어 사용 |


## Dashboard WebSocket 연동

Whisper STT 노드나 테스트 UI는 최종 인식 결과를 아래 형태로 보낸다.

```json
{
  "type": "speech.stt.final",
  "transcript": "B구역으로 조립품 배송 시작"
}
```

Dashboard/server는 transcript에서 목적지 A/B와 안전 명령을 파싱한다. `정지`, `멈춰`, `중지`, `stop`, `emergency` 키워드는 즉시 `emergency_stop`으로 매핑한다.

TTS 노드는 안내 시작/완료 상태를 아래 형태로 보낼 수 있다.

```json
{
  "type": "speech.tts.done",
  "text": "B구역 배송을 완료했습니다.",
  "voice": "ko"
}
```

UI는 작업 접수, 비상정지, 배송 완료, TurtleBot 복귀 완료 상태에서 안내 문장을 패널에 표시하고 브라우저 TTS로도 재생한다.
