import asyncio
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
    assert config.turtlebot.command_mode == "local"
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

    assert cmd[:2] == ["bash", "-lc"]
    local = cmd[-1]
    assert "export ROS_DOMAIN_ID=34" in local
    assert "source ~/turtlebot3_ws/install/setup.bash" in local
    assert "ros2 action send_goal" in local
    assert "/navigate_to_pose" in local
    assert "position" in local
    assert '\"stamp\": {\"sec\": 0, \"nanosec\": 0}' in local
    assert config.turtlebot.pose_for("A").yaw == -1.5708
    assert config.turtlebot.pose_for("B").yaw == -1.5708
    assert '\"z\": -0.707' in local
    assert '\"w\": 0.707' in local


def test_server_can_report_real_hardware_status_without_connecting_to_devices():
    server = WebSocketMissionServer()
    status = server.hardware_status_snapshot()

    assert status["mode"] == "real"
    assert status["conveyor"]["target"] == "ssafy@192.168.110.142"
    assert status["turtlebot"]["target"] == "turtlebot4@192.168.110.174"
    assert status["turtlebot"]["command_mode"] == "local"
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
    assert '"x": 0.057' in remote
    assert '"y": -0.0714' in remote


def test_turtlebot_command_builder_generates_nav2_dwell_return_round_trip():
    config = HardwareConfig.load(DEFAULT_CONFIG_PATH)
    builder = TurtleBotCommandBuilder(config.turtlebot)

    cmd = builder.delivery_round_trip_command("B", dwell_sec=3.0)
    remote = cmd[-1]

    assert cmd[:2] == ["bash", "-lc"]
    assert "export ROS_DOMAIN_ID=34" in remote
    assert remote.count("ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose") == 2
    assert "sleep 3" in remote
    assert '"x": 0.057' in remote  # HOME return pose
    assert '"y": -1.32' in remote  # B destination pose


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


def test_server_maps_whisper_stt_transcript_to_turtlebot_navigation_dry_run():
    server = WebSocketMissionServer()

    result = server.handle_whisper_transcript({"type": "speech.stt.final", "transcript": "B구역으로 조립품 배송 시작"})

    assert [event["type"] for event in result] == ["speech.stt.final", "factory.state", "hardware.command_result"]
    assert result[0]["execute"] is False
    assert result[1]["state"] == "DELIVERY_NAVIGATING"
    assert result[1]["payload"]["speech"]["intent"] == "create_order"
    assert result[1]["payload"]["speech"]["destination"] == "B"
    assert result[2]["subsystem"] == "turtlebot"
    assert result[2]["action"] == "navigate_B"
    assert result[2]["executed"] is False


def test_server_maps_home_stt_transcript_to_home_navigation_dry_run():
    server = WebSocketMissionServer()

    result = server.handle_whisper_transcript({"type": "speech.stt.final", "transcript": "홈 위치로 이동"})

    assert isinstance(result, list)
    assert [event["type"] for event in result] == ["speech.stt.final", "factory.state", "hardware.command_result"]
    assert result[1]["state"] == "DELIVERY_NAVIGATING"
    assert result[1]["payload"]["speech"]["destination"] == "HOME"
    assert result[1]["payload"]["speech"]["parts"] == []
    assert result[2]["subsystem"] == "turtlebot"
    assert result[2]["action"] == "navigate_HOME"
    assert result[2]["destination"] == "HOME"
    assert result[2]["target_pose"] == {"x": 0.057, "y": -0.0714, "yaw": 0.0}
    assert result[2]["executed"] is False


def test_whisper_stt_navigation_does_not_reenter_order_fsm_while_already_navigating():
    server = WebSocketMissionServer()
    server.fsm.state = type(server.fsm.state).DELIVERY_NAVIGATING

    result = asyncio.run(server.handle_message(json.dumps({"type": "speech.stt.final", "transcript": "B구역으로 조립품 배송 시작"}, ensure_ascii=False)))

    assert result[0]["type"] == "speech.stt.final"
    assert result[1]["type"] == "factory.state"
    assert result[1]["state"] == "DELIVERY_NAVIGATING"
    assert result[2]["action"] == "navigate_B"


def test_server_maps_whisper_stop_words_to_emergency_stop():
    server = WebSocketMissionServer()
    server.handle_whisper_transcript({"type": "speech.stt.final", "transcript": "A구역으로 조립품 배송 시작"})

    result = server.handle_whisper_transcript({"type": "speech.stt.final", "transcript": "멈춰"})

    assert result["type"] == "factory.state"
    assert result["state"] == "WAIT_ADMIN_UNLOCK"
    assert result["payload"]["speech"]["intent"] == "emergency_stop"


def test_server_can_dry_run_direct_turtlebot_navigation_from_stt():
    server = WebSocketMissionServer()

    result = server.navigate_turtlebot_from_speech(
        {"intent": "create_order", "command": "B구역으로 가", "destination": "B", "parts": []},
        "B구역으로 가",
        execute=False,
    )

    assert [event["type"] for event in result] == ["speech.stt.final", "factory.state", "hardware.command_result"]
    assert result[1]["state"] == "DELIVERY_NAVIGATING"
    assert result[2]["subsystem"] == "turtlebot"
    assert result[2]["action"] == "navigate_B"
    assert result[2]["executed"] is False
    assert "ros2 action send_goal" in result[2]["command"][-1]


def test_server_passthroughs_turtlebot_pose_messages_for_dashboard_broadcast():
    server = WebSocketMissionServer()
    payload = {"type": "turtlebot.pose", "pose": {"x": 0.1, "y": -0.2, "yaw": 1.57}, "status": "실시간 pose 수신"}

    result = asyncio.run(server.handle_message(json.dumps(payload, ensure_ascii=False)))

    assert result == payload
