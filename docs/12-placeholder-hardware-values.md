# 12. 하드웨어 임의값 / 추후 실측 필요 목록

현재 실제 하드웨어가 없어서 아래 값은 **reference/mock placeholder**로 들어가 있습니다. 실제 장비 연결 전 반드시 실측/보정해야 합니다.

| 위치/파일 | 값 | 현재 의미 | 실제 장비에서 해야 할 일 |
|---|---:|---|---|
| `dobot_controller/calibration.py` | homography matrix | 참고 repo `picking_dobot/control_node.py`의 픽셀→로봇 좌표 변환행렬 | 카메라 고정 후 checker/known point로 재보정 |
| `dobot_controller/sequence.py` | `safe_z_mm=20.0` | 이동 시 충돌 회피 높이 | 실제 gripper/부품/컨베이어 높이에 맞게 조정 |
| `dobot_controller/sequence.py` | `pick_z_mm=-31.77` | 흡착/그리퍼가 물체를 잡는 Z 높이 | 부품 두께와 end-effector 기준으로 재측정 |
| `dobot_controller/sequence.py` | `part_a_pixel=(320,240)` | A부품 mock 검출 위치 | 비전 검출 결과로 대체 |
| `dobot_controller/sequence.py` | `part_b_pixel=(390,240)` | B부품 mock 검출 위치 | 비전 검출 결과로 대체 |
| `dobot_controller/sequence.py` | conveyor place `(220,0,-25,0)` | 컨베이어 위 적재 위치 | 컨베이어 좌표계 기준으로 teach-in |
| `dobot_controller/sequence.py` | stack offset `(0,0,18)` | B부품을 A 위에 올리는 높이 차 | 실제 부품 높이로 수정 |
| `turtlebot_delivery/targets.py` | A `(1.2,0,0)`, B `(0,1.2,1.5708)` | Nav2 mock 목적지 | 실제 map에서 pose 저장 후 반영 |
| `dobot_controller/sequence.py` | retreat safe home `(200,0,safe_z,0)` | 시퀀스 종료 후 충돌 회피 복귀 위치 | 실제 Dobot 작업영역에서 안전 home pose teach-in |
| `vision_detector/color_detector.py` | yellow HSV range | 참고 repo처럼 노란 물체 검출 | 조명/카메라에 맞게 HSV/YOLO 모델 튜닝 |
| `vision_detector/color_detector.py` | skin HSV range | 손 후보 감지용 임시 HSV 범위 | 실제 환경에서는 손/장갑 색상, YOLO/MediaPipe 등으로 재검증 |

원칙: 이 값들은 코드에 흩어져 있지 않도록 config/dataclass에 모아두었고, real node 전환 시 YAML/환경변수로 이동할 예정입니다.

비전/Dobot 픽셀 좌표 변환의 초기 참고 코드는 다음 GitHub 경로입니다.

```text
https://github.com/binedwin/pill-sorting-delivery/tree/main/src/picking_dobot/picking_dobot
```
