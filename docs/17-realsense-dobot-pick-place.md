# 17. RealSense D435i + Dobot 2개 물체 Pick & Place 실행 가이드

이 문서는 RealSense D435i로 물체 위치를 감지하고, Dobot이 **물체 1개를 집어 컨베이어에 올린 뒤**, 다시 **다른 물체 1개를 집어 컨베이어에 올리고**, 마지막에 컨베이어를 이동시키는 절차를 설명합니다.

참고 구현은 `/home/ssafy/project_pill/robot_control_ws/src/picking_dobot/picking_dobot`의 `vision_node.py`, `control_node.py`, `color_bridge_node.py` 패턴을 우리 프로젝트 구조에 맞게 이식한 것입니다.

## 추가된 ROS 2 노드

| 패키지 | 실행명 | 역할 |
|---|---|---|
| `vision_detector` | `realsense_object_detector` | RealSense color/depth/camera_info를 받아 YOLOv5 `best.pt`의 `car_lower`/`car_upper` 라벨 또는 legacy HSV 기반으로 물체 3D 좌표를 `/target_pixel`에 publish |
| `dobot_controller` | `two_object_pick_place` | `/target_pixel`을 받아 Dobot pick/place를 2회 수행한 뒤 Conveyor Pi에 start 명령 전송 |

## 토픽/액션/서비스

| 이름 | 타입 | 설명 |
|---|---|---|
| `/camera/camera/color/image_raw` | `sensor_msgs/Image` | RealSense RGB 영상 |
| `/camera/camera/aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | RGB에 정렬된 depth 영상 |
| `/camera/camera/color/camera_info` | `sensor_msgs/CameraInfo` | RealSense intrinsics |
| `/target_color` | `std_msgs/String` | YOLO 모드에서는 감지할 라벨(`car_lower`, `car_upper`), legacy HSV 모드에서는 색상. 기본 `car_lower` |
| `/target_pixel` | `geometry_msgs/Point` | camera-frame 3D 좌표(mm): `x`, `y`, `z` |
| `PTP_action` | `dobot_msgs/action/PointToPoint` | Dobot PTP 이동 action |
| `/dobot_suction_cup_service` | `dobot_msgs/srv/SuctionCupControl` | 흡착 ON/OFF |
| `/task_status` | `std_msgs/String` | 작업 완료 상태 |
| `/dobot/two_object_plan` | `std_msgs/String` | 실행 계획 JSON |

## 1. 빌드

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
colcon build --event-handlers console_direct+
source install/setup.bash
```

## 2. RealSense bringup

RealSense D435i가 연결된 PC에서 camera node를 실행합니다.

```bash
source /opt/ros/humble/setup.bash
ros2 launch realsense2_camera rs_launch.py \
  align_depth.enable:=true \
  pointcloud.enable:=false
```

토픽 확인:

```bash
ros2 topic list | grep camera
```

필수 토픽:

```text
/camera/camera/color/image_raw
/camera/camera/aligned_depth_to_color/image_raw
/camera/camera/color/camera_info
```

## 3. Dobot bringup 및 homing

Dobot을 실제로 움직이는 `two_object_pick_place` 노드는 Dobot bringup과 homing이 끝난 뒤 실행해야 합니다. 새 터미널에서 다음을 실행합니다.

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch dobot_bringup dobot_magician_control_system.launch.py
```

bringup 터미널은 계속 켜 둔 상태로, 다른 터미널에서 homing을 실행합니다.

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 service call /dobot_homing_service dobot_msgs/srv/ExecuteHomingProcedure
```

## 4. Dobot action/service 확인

Dobot action/service가 떠 있는지 확인합니다.

```bash
ros2 action list | grep PTP_action
ros2 service list | grep suction
```

기대:

```text
PTP_action
/dobot_suction_cup_service
```

`PTP_action`이 보이지 않는 상태에서도 **RealSense detector만 실행하는 것은 가능합니다.** detector는 카메라 토픽만 사용해서 `/target_pixel`을 publish하기 때문입니다. 다만 `two_object_pick_place`는 Dobot 이동 action인 `PTP_action`을 기다리므로, `PTP_action`이 없으면 실제 Dobot pick/place 단계에서 멈춥니다.

따라서 권장 순서는 다음과 같습니다.

```text
- 카메라 좌표 감지만 확인하려는 경우: PTP_action 없이 5번 RealSense detector 실행 가능
- Dobot까지 실제 구동하려는 경우: dobot bringup + homing 후 PTP_action 확인이 먼저 필요
```

만약 `ros2 launch dobot_bringup ...` 실행 후에도 `PTP_action`이 계속 보이지 않으면, bringup 터미널 로그에서 serial port 연결 실패, permission denied, Dobot 전원/USB 연결 문제, action server 기동 실패 메시지를 먼저 확인합니다.

### `np.maximum_sctype` / NumPy 2.x 오류가 나는 경우

다음과 같은 로그가 나오면 Dobot 자체보다 Python 의존성 충돌 문제입니다.

```text
AttributeError: `np.maximum_sctype` was removed in the NumPy 2.0 release
```

원인은 `tf_transformations -> transforms3d`가 `~/.local/lib/python3.10/site-packages/numpy`의 NumPy 2.x를 잡고 있는데, 현재 설치된 `transforms3d`가 NumPy 2.x에서 제거된 API를 사용하기 때문입니다. 이 경우 `PTP_server`, `trajectory_validator_server`, `state_publisher`가 죽어서 `PTP_action`이 나타나지 않습니다.

가장 단순한 조치. 실제 Dobot bringup에서 `PTP_action` 복구가 확인된 버전은 `numpy==1.23.5`입니다.

```bash
python3 -m pip install --user --force-reinstall numpy==1.23.5
```

설치 중 `opencv-python ... requires numpy>=2` 경고가 나올 수 있지만, Dobot ROS2 bringup에는 `tf_transformations/transforms3d` 호환성이 더 우선입니다. 이 경고는 pip resolver 경고이며, 설치가 `Successfully installed numpy-1.23.5`로 끝나고 `PTP_action`이 뜨면 Dobot 쪽은 정상입니다.

설치 후 새 터미널을 열고 다시 확인합니다.

```bash
python3 - <<'PY'
import numpy as np
import transforms3d
print('numpy', np.__version__, np.__file__)
print('transforms3d', transforms3d.__file__)
PY
```

`numpy`가 `1.x`로 나오면 Dobot bringup을 다시 실행합니다.

```bash
ros2 launch dobot_bringup dobot_magician_control_system.launch.py
ros2 action list | grep PTP_action
```

## 5. YOLO 모델 위치

학습된 모델은 repository 루트에 있던 `best.pt`를 다음 위치로 옮겨 사용합니다. `.gitignore`의 `*.pt` 규칙 때문에 Git에는 올라가지 않으므로, 다른 PC에서는 같은 경로에 직접 복사해야 합니다.

```text
/home/ssafy/smart-assembly-transport/models/yolo/car_parts_best.pt
```

SHA-256 확인값:

```text
82e1e142b78bdf6da44b7b52ad379ef1a92c08f38b811e85706d1613b3ae7f40
```

## 6. RealSense + YOLO detector 실행

새 터미널:

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run vision_detector realsense_object_detector --ros-args \
  -p detector_mode:=yolo \
  -p yolo_model_path:=/home/ssafy/smart-assembly-transport/models/yolo/car_parts_best.pt \
  -p target_labels:=car_lower,car_upper \
  -p min_confidence:=0.35 \
  -p min_area:=1000.0
```

감지 라벨 수동 변경:

```bash
ros2 topic pub --once /target_color std_msgs/msg/String "{data: car_upper}"
# 또는 명시적 라벨 명령 토픽
ros2 topic pub --once /target_label_cmd std_msgs/msg/String "{data: car_upper}"
```

지원 라벨:

```text
car_lower, car_upper
```

색상 기반 이전 방식이 필요하면 `-p detector_mode:=color -p target_color:=yellow`로 실행할 수 있습니다.

## 7. Dobot 2개 물체 pick/place 노드 실행

분류 기능을 쓰려면 Conveyor Pi의 edge script도 최신이어야 합니다.

```bash
scp /home/ssafy/smart-assembly-transport/scripts/edge/conveyor_control.py \
  ssafy@192.168.110.142:~/smart-assembly-transport-edge/conveyor_control.py
```

새 터미널:

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run dobot_controller two_object_pick_place --ros-args \
  -p target_colors:=car_lower,car_upper \
  -p quality_result:=normal \
  -p conveyor_sort_steps:=3200
```

분류 방향:

```text
quality_result:=normal   → 왼쪽 분류(sort-left)
quality_result:=abnormal → 오른쪽 분류(sort-right)
```

`conveyor_sort_steps`는 두 물체를 올린 뒤 분류 지점까지 충분히 이동시키기 위한 컨베이어 pulse 수입니다. 기존 짧은 테스트값보다 길게 기본 `3200`으로 잡았습니다. 너무 짧으면 `4000`, `5000`처럼 올리고, 너무 길면 낮춥니다.

동작 순서:

```text
1. `/target_color=car_lower`로 첫 번째 라벨 감지
2. /target_pixel 첫 번째 좌표 수신
3. Dobot이 첫 번째 물체 위로 이동
4. pick_z로 내려감
5. suction ON
6. safe_z로 상승
7. 컨베이어 place 위치 위로 이동
8. 컨베이어 z 위치까지 내려감
9. suction OFF로 컨베이어에 안정적으로 놓음
10. safe_z로 다시 상승
11. `/target_color=car_upper`로 두 번째 라벨 전환 후 잠시 대기
12. 두 번째 /target_pixel 좌표 수신
13. 같은 순서로 두 번째 물체를 컨베이어에 놓음
14. 품질 결과가 `normal`이면 컨베이어를 길게 구동하면서 왼쪽으로 분류
15. 품질 결과가 `abnormal`이면 컨베이어를 길게 구동하면서 오른쪽으로 분류
```

## 8. 현재 기준 좌표/보정값

`project_pill`의 동작 코드에서 가져온 뒤, 실제 YOLO/Dobot 테스트 피드백을
반영해 조정한 값입니다. pick은 직전 값보다 2mm 더 낮췄고,
place 높이는 그대로 유지합니다. `car_lower`는 컨베이어에 낮게 내려놓되 `car_upper`는 `car_lower` 위에
쌓이도록 더 높은 Z에서 release합니다.

```text
safe_z_mm = 70.0
pick_z_mm = -52.0
car_lower_place_pose = x=48.2, y=196.3, z=6.8, r=0.0
car_upper_place_pose = x=48.2, y=224.3, z=14.8, r=0.0
object_place_spacing_y_mm = 28.0
upper_stack_place_lift_mm = 8.0
```

카메라 → Dobot 변환 행렬도 `project_pill`의 `control_node.py` 값을 사용합니다.

```text
[[0.048553, 0.985575, 0.162123, 204.376144],
 [0.998327, -0.052987, 0.023133, -13.145106],
 [0.031390, 0.160728, -0.986499, 361.830566],
 [0.0,      0.0,      0.0,      1.0]]
```

실제 테이블에서는 `pick_z_mm`, `conveyor_place_pose`, `object_place_spacing_y_mm`는 미세 조정이 필요할 수 있습니다.

## 9. 모니터링

계획 JSON 확인:

```bash
ros2 topic echo /dobot/two_object_plan
```

상태 확인:

```bash
ros2 topic echo /task_status
```

기대 상태:

```text
COMPLETED_OBJECT_1_WAITING_FOR_OBJECT_2
COMPLETED_TWO_OBJECT_PICK_PLACE
```

## 10. 안전 주의

- Dobot workspace 안에 손을 넣지 마세요.
- 첫 테스트는 suction/높이 보정값을 보수적으로 잡고 진행하세요.
- `pick_z_mm=-52.0`은 직전 테스트값에서 2mm 더 낮춘 값입니다.
- `car_lower` place Z는 `6.8`, `car_upper` place Z는 `14.8`입니다. `car_upper`가 `car_lower` 위에 잘 쌓이지 않으면 `upper_stack_place_lift_mm`를 1~2mm씩 조정하세요.
- 컨베이어는 두 번째 물체를 놓은 뒤 한 번만 start됩니다.
- 비상 상황에서는 Conveyor Pi emergency-stop과 Dobot E-stop을 우선 사용하세요.
