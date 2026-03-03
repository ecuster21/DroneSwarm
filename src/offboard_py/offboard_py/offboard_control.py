#!/usr/bin/env python3

"""Offboard control node that can be reused for multi-vehicle setups."""

import math

from geometry_msgs.msg import Pose2D
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy

from px4_msgs.msg import OffboardControlMode
from px4_msgs.msg import TrajectorySetpoint
from px4_msgs.msg import VehicleCommand
from px4_msgs.msg import VehicleCommandAck
from px4_msgs.msg import VehicleLocalPosition
from px4_msgs.msg import VehicleStatus


ACK_LABELS = {
    VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED: 'ACCEPTED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_TEMPORARILY_REJECTED: 'TEMP_REJECTED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_DENIED: 'DENIED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_UNSUPPORTED: 'UNSUPPORTED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_FAILED: 'FAILED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_IN_PROGRESS: 'IN_PROGRESS',
    VehicleCommandAck.VEHICLE_CMD_RESULT_CANCELLED: 'CANCELLED',
}


def _coerce_bool(value) -> bool:
    """Convert ROS parameter values into a real bool."""
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


class OffboardControl(Node):
    """PX4 offboard executor for a single vehicle namespace."""

    def __init__(self):
        super().__init__('offboard_control_node')
        self.target_x = float(self.declare_parameter('target_x', 0.0).value)
        self.target_y = float(self.declare_parameter('target_y', 0.0).value)
        self.target_z = float(self.declare_parameter('target_z', -5.0).value)
        self.target_yaw = float(
            self.declare_parameter('target_yaw', -3.14).value
        )
        self.engage_after_setpoints = max(
            1,
            int(self.declare_parameter('engage_after_setpoints', 10).value),
        )
        self.retry_interval = max(
            1,
            int(self.declare_parameter('retry_interval', 10).value),
        )
        self.timer_period_sec = float(
            self.declare_parameter('timer_period_sec', 0.1).value
        )
        self.command_target_system = int(
            self.declare_parameter('command_target_system', 1).value
        )
        self.command_target_component = int(
            self.declare_parameter('command_target_component', 1).value
        )
        self.command_source_system = int(
            self.declare_parameter('command_source_system', 1).value
        )
        self.command_source_component = int(
            self.declare_parameter('command_source_component', 1).value
        )
        self.acceptance_radius_m = float(
            self.declare_parameter('acceptance_radius_m', 1.5).value
        )
        self.log_ack = _coerce_bool(
            self.declare_parameter('log_ack', True).value
        )
        self.auto_discover_target_ids = _coerce_bool(
            self.declare_parameter('auto_discover_target_ids', True).value
        )

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.offboard_control_mode_publisher_ = self.create_publisher(
            OffboardControlMode,
            'fmu/in/offboard_control_mode',
            qos_profile,
        )
        self.trajectory_setpoint_publisher_ = self.create_publisher(
            TrajectorySetpoint,
            'fmu/in/trajectory_setpoint',
            qos_profile,
        )
        self.vehicle_command_publisher_ = self.create_publisher(
            VehicleCommand,
            'fmu/in/vehicle_command',
            qos_profile,
        )

        self.vehicle_status_subscriber_ = self.create_subscription(
            VehicleStatus,
            'fmu/out/vehicle_status',
            self.vehicle_status_callback,
            qos_profile,
        )
        self.vehicle_local_position_subscriber_ = self.create_subscription(
            VehicleLocalPosition,
            'fmu/out/vehicle_local_position',
            self.vehicle_local_position_callback,
            qos_profile,
        )
        self.vehicle_command_ack_subscriber_ = self.create_subscription(
            VehicleCommandAck,
            'fmu/out/vehicle_command_ack',
            self.vehicle_command_ack_callback,
            qos_profile,
        )
        self.mission_setpoint_subscriber_ = self.create_subscription(
            Pose2D,
            'mission_setpoint',
            self.mission_setpoint_callback,
            10,
        )

        self.offboard_setpoint_counter_ = 0
        self.vehicle_status = VehicleStatus()
        self.current_position = VehicleLocalPosition()
        self.has_vehicle_status = False
        self.has_position = False
        self._target_reached_logged = False
        self._last_ack_signature = None

        self.timer_ = self.create_timer(
            self.timer_period_sec,
            self.timer_callback,
        )

        namespace = self.get_namespace()
        namespace_label = namespace if namespace != '/' else '/fmu'
        self.get_logger().info(
            (
                f'Starting offboard controller for {namespace_label} '
                f'with target=({self.target_x:.2f}, {self.target_y:.2f}, '
                f'{self.target_z:.2f}) yaw={self.target_yaw:.2f}'
            )
        )

    def vehicle_status_callback(self, msg):
        """Track the latest PX4 status."""
        self.vehicle_status = msg
        self.has_vehicle_status = True
        if not self.auto_discover_target_ids:
            return

        new_target_system = int(msg.system_id) or self.command_target_system
        new_target_component = int(msg.component_id) or self.command_target_component
        ids_changed = (
            new_target_system != self.command_target_system
            or new_target_component != self.command_target_component
        )
        if not ids_changed:
            return

        self.command_target_system = new_target_system
        self.command_target_component = new_target_component
        self.get_logger().info(
            (
                'Using discovered PX4 target ids '
                f'system={self.command_target_system} '
                f'component={self.command_target_component}'
            )
        )

    def vehicle_local_position_callback(self, msg):
        """Track the latest local position for target reach logging."""
        self.current_position = msg
        self.has_position = True

    def vehicle_command_ack_callback(self, msg):
        """Log PX4 command acknowledgements when requested."""
        signature = (msg.command, msg.result, msg.result_param1, msg.result_param2)
        if signature == self._last_ack_signature:
            return

        self._last_ack_signature = signature
        if not self.log_ack:
            return

        result_label = ACK_LABELS.get(msg.result, f'UNKNOWN_{msg.result}')
        log_message = (
            'VehicleCommandAck command='
            f'{msg.command} result={result_label} '
            f'target_system={msg.target_system}'
        )
        if msg.result in (
            VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED,
            VehicleCommandAck.VEHICLE_CMD_RESULT_IN_PROGRESS,
        ):
            self.get_logger().info(log_message)
        else:
            self.get_logger().warning(log_message)

    def mission_setpoint_callback(self, msg):
        """Update the dynamic mission target for this vehicle."""
        new_target_x = float(msg.x)
        new_target_y = float(msg.y)
        new_target_yaw = float(msg.theta)
        if (
            math.isclose(new_target_x, self.target_x, abs_tol=1e-6)
            and math.isclose(new_target_y, self.target_y, abs_tol=1e-6)
            and math.isclose(new_target_yaw, self.target_yaw, abs_tol=1e-6)
        ):
            return

        self.target_x = new_target_x
        self.target_y = new_target_y
        self.target_yaw = new_target_yaw
        self._target_reached_logged = False
        self.get_logger().info(
            (
                'Received mission setpoint '
                f'({self.target_x:.2f}, {self.target_y:.2f}, {self.target_z:.2f}) '
                f'yaw={self.target_yaw:.2f}'
            )
        )

    def publish_offboard_control_mode(self):
        """Publish the offboard heartbeat."""
        msg = OffboardControlMode()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_control_mode_publisher_.publish(msg)

    def publish_trajectory_setpoint(self):
        """Publish the latest position target."""
        msg = TrajectorySetpoint()
        msg.position = [
            self.target_x,
            self.target_y,
            self.target_z,
        ]
        msg.yaw = self.target_yaw
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.trajectory_setpoint_publisher_.publish(msg)

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0):
        """Publish a PX4 vehicle command."""
        msg = VehicleCommand()
        msg.param1 = param1
        msg.param2 = param2
        msg.command = command
        msg.target_system = self.command_target_system
        msg.target_component = self.command_target_component
        msg.source_system = self.command_source_system
        msg.source_component = self.command_source_component
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.vehicle_command_publisher_.publish(msg)

    def arm(self):
        """Send an arm command."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            1.0,
        )
        self.get_logger().info('Arm command send')

    def engage_offboard_mode(self):
        """Request PX4 offboard mode."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
            1.0,
            6.0,
        )
        self.get_logger().info('Switch to Offboard mode command send')

    def _log_target_reached(self):
        if not self.has_position or self._target_reached_logged:
            return

        distance = math.hypot(
            self.current_position.x - self.target_x,
            self.current_position.y - self.target_y,
        )
        if distance <= self.acceptance_radius_m:
            self._target_reached_logged = True
            self.get_logger().info(
                f'Target reached within {distance:.2f} m'
            )

    def timer_callback(self):
        """Maintain offboard mode and keep publishing setpoints."""
        self.publish_offboard_control_mode()
        self.publish_trajectory_setpoint()
        self._log_target_reached()

        command_ready = self.has_vehicle_status or not self.auto_discover_target_ids
        if not command_ready:
            self.offboard_setpoint_counter_ += 1
            return

        if self.offboard_setpoint_counter_ == self.engage_after_setpoints:
            self.engage_offboard_mode()
            self.arm()

        if (
            self.offboard_setpoint_counter_ > self.engage_after_setpoints
            and self.vehicle_status.arming_state
            != VehicleStatus.ARMING_STATE_ARMED
            and self.offboard_setpoint_counter_ % self.retry_interval == 0
        ):
            self.arm()

        if (
            self.offboard_setpoint_counter_ > self.engage_after_setpoints
            and self.vehicle_status.nav_state
            != VehicleStatus.NAVIGATION_STATE_OFFBOARD
            and self.offboard_setpoint_counter_ % self.retry_interval == 0
        ):
            self.engage_offboard_mode()

        self.offboard_setpoint_counter_ += 1


def main(args=None):
    """Run the node."""
    rclpy.init(args=args)
    offboard_control = OffboardControl()
    rclpy.spin(offboard_control)
    offboard_control.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
