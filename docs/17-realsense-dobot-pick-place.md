# 17. RealSense D435i + Dobot 2개 물체 Pick & Place 실행 가이드

이 문서는 RealSense D435i로 물체 위치를 감지하고, Dobot이 **물체 1개를 집어 컨베이어에 올린 뒤**, 다시 **다른 물체 1개를 집어 컨베이어에 올리고**, 마지막에 컨베이어를 이동시키는 절차를 설명합니다.

참고 구현은 `/home/ssafy/project_pill/robot_control_ws/src/picking_dobot/picking_dobot`의 `vision_node.py`, `control_node.py`, `color_bridge_node.py` 패턴을 우리 프로젝트 구조에 맞게 이식한 것입니다.

## 추가된 ROS 2 노드

| 패키지 | 실행명 | 역할 |
|---|---|---|
| `vision_detector` | `realsense_object_detector` | RealSense color/depth/camera_info를 받아 HSV 기반으로 물체 3D 좌표를 `/target_pixel`에 publish |
| `dobot_controller` | `two_object_pick_place` | `/target_pixel`을 받아 Dobot pick/place를 2회 수행한 뒤 Conveyor Pi에 start 명령 전송 |

## 토픽/액션/서비스

| 이름 | 타입 | 설명 |
|---|---|---|
| `/camera/camera/color/image_raw` | `sensor_msgs/Image` | RealSense RGB 영상 |
| `/camera/camera/aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | RGB에 정렬된 depth 영상 |
| `/camera/camera/color/camera_info` | `sensor_msgs/CameraInfo` | RealSense intrinsics |
| `/target_color` | `std_msgs/String` | 감지할 색상. 기본 `yellow` |
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

## 3. Dobot bringup 확인

Dobot action/service가 떠 있어야 합니다.

```bash
ros2 action list | grep PTP_action
ros2 service list | grep suction
```

기대:

```text
PTP_action
/dobot_suction_cup_service
```

## 4. RealSense detector 실행

새 터미널:

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run vision_detector realsense_object_detector --ros-args -p target_color:=yellow -p min_area:=1000.0
```

색상 변경:

```bash
ros2 topic pub --once /target_color std_msgs/msg/String "{data: yellow}"
```

지원 색상:

```text
yellow, red, blue, green
```

## 5. Dobot 2개 물체 pick/place 노드 실행

새 터미널:

```bash
cd /home/ssafy/smart-assembly-transport/sem1_pjt_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run dobot_controller two_object_pick_place
```

동작 순서:

```text
1. /target_pixel 첫 번째 좌표 수신
2. Dobot이 첫 번째 물체 위로 이동
3. pick_z로 내려감
4. suction ON
5. safe_z로 상승
6. 컨베이어 place 위치 위로 이동
7. suction OFF로 컨베이어에 놓음
8. 두 번째 /target_pixel 좌표 수신 대기
9. 같은 순서로 두 번째 물체를 컨베이어에 놓음
10. Conveyor Pi에 start 명령 전송
```

## 6. 현재 기준 좌표/보정값

`project_pill`의 동작 코드에서 가져온 초기값입니다.

```text
safe_z_mm = 70.0
pick_z_mm = -39.0
conveyor_place_pose = x=48.2, y=196.3, z=17.8, r=0.0
object_place_spacing_y_mm = 28.0
```

카메라 → Dobot 변환 행렬도 `project_pill`의 `control_node.py` 값을 사용합니다.

```text
[[0.048553, 0.985575, 0.162123, 204.376144],
 [0.998327, -0.052987, 0.023133, -13.145106],
 [0.031390, 0.160728, -0.986499, 361.830566],
 [0.0,      0.0,      0.0,      1.0]]
```

실제 테이블에서는 `pick_z_mm`, `conveyor_place_pose`, `object_place_spacing_y_mm`는 미세 조정이 필요할 수 있습니다.

## 7. 모니터링

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

## 8. 안전 주의

- Dobot workspace 안에 손을 넣지 마세요.
- 첫 테스트는 suction/높이 보정값을 보수적으로 잡고 진행하세요.
- `pick_z_mm=-39.0`은 reference 값이므로 실제 물체 높이에 맞게 조정해야 할 수 있습니다.
- 컨베이어는 두 번째 물체를 놓은 뒤 한 번만 start됩니다.
- 비상 상황에서는 Conveyor Pi emergency-stop과 Dobot E-stop을 우선 사용하세요.
