import json

from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import (
    DEFAULT_CONFIG_PATH,
    HardwareConfig,
)
from sem1_pjt_ws.src.conveyor_controller.conveyor_controller.real_conveyor import (
    ConveyorCommandBuilder,
)
from sem1_pjt_ws.src.turtlebot_delivery.turtlebot_delivery.real_turtlebot import (
    TurtleBotCommandBuilder,
)
from sem1_pjt_ws.src.turtlebot_delivery.turtlebot_delivery.delivery_round_trip import (
    build_parser,
    run_delivery_round_trip,
)
from sem1_pjt_ws.src.mission_orchestrator.mission_orchestrator.real_pipeline import (
    RealHardwarePipeline,
)
from server.app import WebSocketMissionServer


def test_default_hardware_config_uses_project_device_addresses():
    config = HardwareConfig.load(DEFAULT_CONFIG_PATH)

    assert config.conveyor.ssh_user == "ssafy"
    assert config.conveyor.host == "192.168.110.142"
    assert config.turtlebot.ssh_user == "turtlebot4"
    assert config.turtlebot.host == "192.168.110.174"
    assert config.turtlebot.ros_domain_id == 34
    assert config.turtlebot.delivery_dwell_sec == 3.0
    assert config.mode == "real"


def test_conveyor_command_builder_wraps_remote_commands_safely():
    config = HardwareConfig.load(DEFAULT_CONFIG_PATH)
    builder = ConveyorCommandBuilder(config.conveyor)

    start = builder.ssh_command("start")
    stop = builder.ssh_command("stop")

    assert start[:3] == ["ssh", "-o", "BatchMode=yes"]
    assert "ssafy@192.168.110.142" in start
    assert "CONVEYOR_MODE=stepper" in start[-1]
    assert "CONVEYOR_STEP_PIN=27" in start[-1]
    assert "CONVEYOR_DIR_PIN=17" in start[-1]
    assert "CONVEYOR_ENABLE_PIN=22" in start[-1]
    assert "CONVEYOR_ENABLE_ACTIVE_HIGH=0" in start[-1]
    assert "CONVEYOR_DIR_ACTIVE_HIGH=0" in start[-1]
    assert "CONVEYOR_GPIO_BACKEND=gpiod" in start[-1]
    assert "conveyor_control.py start" in start[-1]
    assert "conveyor_control.py stop" in stop[-1]


def test_turtlebot_command_builder_sets_ros_domain_id_34_and_goal_pose():
    config = HardwareConfig.load(DEFAULT_CONFIG_PATH)
    builder = TurtleBotCommandBuilder(config.turtlebot)

    cmd = builder.navigate_command("A")

    assert "turtlebot4@192.168.110.174" in cmd
    remote = cmd[-1]
    assert "export ROS_DOMAIN_ID=34" in remote
    assert "source ~/turtlebot4_ws/install/setup.bash" in remote
    assert "ros2 action send_goal" in remote
    assert "/navigate_to_pose" in remote
    assert "position" in remote


def test_server_can_report_real_hardware_status_without_connecting_to_devices():
    server = WebSocketMissionServer()
    status = server.hardware_status_snapshot()

    assert status["mode"] == "real"
    assert status["conveyor"]["target"] == "ssafy@192.168.110.142"
    assert status["turtlebot"]["target"] == "turtlebot4@192.168.110.174"
    assert status["turtlebot"]["ros_domain_id"] == 34


def test_real_pipeline_message_schema_is_dashboard_friendly():
    server = WebSocketMissionServer()
    payload = server.real_pipeline_summary()

    encoded = json.dumps(payload, ensure_ascii=False)
    assert "hardware.pipeline" in encoded
    assert "conveyor" in encoded
    assert "turtlebot" in encoded
    assert "dobot" in encoded
    assert "vision" in encoded


def test_real_pipeline_summary_exposes_demo_phases_and_return_home_target():
    server = WebSocketMissionServer()
    payload = server.real_pipeline_summary()

    assert payload["turtlebot"]["home_destination"] == "HOME"
    assert payload["turtlebot"]["delivery_dwell_sec"] == 3.0
    assert "HOME" in payload["turtlebot"]["targets"]
    phases = payload["phases"]
    phase_ids = [phase["id"] for phase in phases]
    assert phase_ids == [
        "order",
        "conveyor_to_vision_gate",
        "assembly",
        "quality_check",
        "load_to_turtlebot",
        "delivery",
        "return_home",
    ]
    assert phases[-1]["source_reference"] == "project_pill_return_flow_adapted"


def test_turtlebot_command_builder_can_generate_return_home_navigation():
    config = HardwareConfig.load(DEFAULT_CONFIG_PATH)
    builder = TurtleBotCommandBuilder(config.turtlebot)

    cmd = builder.return_home_command()

    remote = cmd[-1]
    assert "export ROS_DOMAIN_ID=34" in remote
    assert "ros2 action send_goal" in remote
    assert '"x": 0.0' in remote
    assert '"y": 0.0' in remote


def test_turtlebot_command_builder_generates_nav2_dwell_return_round_trip():
    config = HardwareConfig.load(DEFAULT_CONFIG_PATH)
    builder = TurtleBotCommandBuilder(config.turtlebot)

    cmd = builder.delivery_round_trip_command("B", dwell_sec=3.0)
    remote = cmd[-1]

    assert "turtlebot4@192.168.110.174" in cmd
    assert "export ROS_DOMAIN_ID=34" in remote
    assert remote.count("ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose") == 2
    assert "sleep 3" in remote
    assert '"x": 0.0' in remote  # HOME return pose
    assert '"y": 1.2' in remote  # B destination pose


def test_turtlebot_delivery_round_trip_cli_dry_run_outputs_three_steps():
    args = build_parser().parse_args(["A"])

    payload = run_delivery_round_trip(args)

    assert payload["type"] == "turtlebot.delivery_round_trip.result"
    assert payload["execute"] is False
    assert payload["dwell_sec"] == 3.0
    assert [step["step"] for step in payload["steps"]] == ["navigate_A", "wait_3s", "return_HOME"]
    assert all(step["stdout"] == "DRY_RUN" for step in payload["steps"])


def test_real_order_plan_dry_run_covers_full_pipeline_commands_states_and_return_home():
    config = HardwareConfig.load(DEFAULT_CONFIG_PATH)
    pipeline = RealHardwarePipeline(config, execute=False)

    events = pipeline.run_order_plan("A")
    states = [event.get("state") for event in events if event["type"] == "factory.state"]
    command_actions = [event.get("action") for event in events if event["type"] == "hardware.command_result"]

    assert states == [
        "ORDER_RECEIVED",
        "CONVEYOR_MOVING",
        "BASE_DETECTED_STOPPING",
        "ASSEMBLY_STAGE_1",
        "ASSEMBLY_STAGE_2",
        "QC_CHECK",
        "LOADING_TO_TURTLEBOT",
        "DELIVERY_NAVIGATING",
        "DELIVERED",
        "RETURNING_HOME",
        "RETURNED_HOME",
    ]
    assert "start" in command_actions
    assert "stop" in command_actions
    assert any(action and action.startswith("ptp_step_") for action in command_actions)
    assert "navigate_A" in command_actions
    assert "wait_3s" in command_actions
    assert "return_HOME" in command_actions
    assert all(event.get("executed") is False for event in events if event["type"] == "hardware.command_result")
