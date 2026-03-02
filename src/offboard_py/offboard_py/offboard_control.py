#!/usr/bin/env python3

"""Offboard control node that can be reused for multi-vehicle setups."""

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy

from px4_msgs.msg import OffboardControlMode
from px4_msgs.msg import TrajectorySetpoint
from px4_msgs.msg import VehicleCommand
from px4_msgs.msg import VehicleStatus


class OffboardControl(Node):

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

        # 配置 QoS (必须匹配 PX4 的 DDS 设置)
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # --- 发布者 ---
        # 1. 发送 Offboard 控制模式心跳
        self.offboard_control_mode_publisher_ = self.create_publisher(
            OffboardControlMode, 'fmu/in/offboard_control_mode', qos_profile)

        # 2. 发送位置期望值
        self.trajectory_setpoint_publisher_ = self.create_publisher(
            TrajectorySetpoint, 'fmu/in/trajectory_setpoint', qos_profile)

        # 3. 发送车辆指令 (解锁、切换模式)
        self.vehicle_command_publisher_ = self.create_publisher(
            VehicleCommand, 'fmu/in/vehicle_command', qos_profile)

        # --- 订阅者 ---
        # 订阅车辆状态以检查是否连接和当前模式
        self.vehicle_status_subscriber_ = self.create_subscription(
            VehicleStatus,
            'fmu/out/vehicle_status',
            self.vehicle_status_callback,
            qos_profile,
        )

        # --- 变量 ---
        self.offboard_setpoint_counter_ = 0
        self.vehicle_status = VehicleStatus()

        # 创建定时器，100ms (10Hz) 运行一次
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
        self.vehicle_status = msg

    def publish_offboard_control_mode(self):
        msg = OffboardControlMode()
        msg.position = True  # 启用位置控制
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_control_mode_publisher_.publish(msg)

    def publish_trajectory_setpoint(self):
        msg = TrajectorySetpoint()
        msg.position = [
            self.target_x,
            self.target_y,
            self.target_z,
        ]  # x, y, z (NED)
        msg.yaw = self.target_yaw
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.trajectory_setpoint_publisher_.publish(msg)

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0):
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
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            1.0,
        )
        self.get_logger().info("Arm command send")

    def engage_offboard_mode(self):
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
            1.0,  # base_mode (1 = custom)
            6.0,  # custom_main_mode (6 = offboard)
        )
        self.get_logger().info("Switch to Offboard mode command send")

    def timer_callback(self):
        # 1. 无论如何，必须持续发送 Offboard 模式心跳和期望位置
        self.publish_offboard_control_mode()
        self.publish_trajectory_setpoint()

        # 2. 只有在发送了一定数量的数据包（让PX4识别到Offboard信号）后，才尝试解锁和切模式
        if self.offboard_setpoint_counter_ == self.engage_after_setpoints:
            self.engage_offboard_mode()
            self.arm()

        # 简单的逻辑：如果还没有解锁且计数器很大，尝试再次解锁（防止丢包）
        if (
            self.offboard_setpoint_counter_ > self.engage_after_setpoints
            and self.vehicle_status.arming_state
            != VehicleStatus.ARMING_STATE_ARMED
            and self.offboard_setpoint_counter_ % self.retry_interval == 0
        ):
            self.arm()

        # 如果已经解锁但不是 Offboard 模式，尝试再次切换
        if (
            self.offboard_setpoint_counter_ > self.engage_after_setpoints
            and self.vehicle_status.nav_state
            != VehicleStatus.NAVIGATION_STATE_OFFBOARD
            and self.offboard_setpoint_counter_ % self.retry_interval == 0
        ):
            self.engage_offboard_mode()

        self.offboard_setpoint_counter_ += 1


def main(args=None):
    rclpy.init(args=args)
    offboard_control = OffboardControl()
    rclpy.spin(offboard_control)
    offboard_control.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
