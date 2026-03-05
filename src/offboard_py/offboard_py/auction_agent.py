#!/usr/bin/env python3

"""ROS 2 node that wraps the asynchronous auction core for one UAV."""

import json
import math
from typing import List
from typing import Optional

from geometry_msgs.msg import Pose2D
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy
from std_msgs.msg import String

from px4_msgs.msg import VehicleLocalPosition
from px4_msgs.msg import VehicleStatus

from offboard_py.auction_core import AgentAuctionState
from offboard_py.auction_core import allocation_to_json
from offboard_py.auction_core import AsyncAuctionConfig
from offboard_py.auction_core import AsyncAuctionCore
from offboard_py.auction_core import agent_state_to_json
from offboard_py.auction_core import bid_from_json
from offboard_py.auction_core import bid_to_json
from offboard_py.auction_core import Task
from offboard_py.auction_core import task_list_from_json


def _coerce_namespace_list(values) -> List[str]:
    """Normalize parameter values into a list of ROS namespaces."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]

    normalized = []
    for value in values:
        label = str(value).strip().strip('/')
        if label:
            normalized.append(label)
    return normalized


class AuctionAgent(Node):
    """Publish bids, local state, and mission setpoints for one vehicle."""

    def __init__(self) -> None:
        """Initialize publishers, subscribers, and the auction core."""
        super().__init__('auction_agent')
        namespace = self.get_namespace().strip('/')
        default_agent_id = namespace if namespace else 'uav'

        self.agent_id = str(self.declare_parameter('agent_id', default_agent_id).value)
        self.update_period_sec = float(
            self.declare_parameter('update_period_sec', 0.2).value
        )
        self.tasks_topic = str(
            self.declare_parameter('tasks_topic', '/task_board/tasks').value
        )
        self.bid_publish_topic = str(
            self.declare_parameter('bid_publish_topic', 'auction/bid').value
        )
        self.peer_bid_topic_suffix = str(
            self.declare_parameter('peer_bid_topic_suffix', 'auction/bid').value
        )
        self.stale_timeout_ms = int(
            self.declare_parameter('stale_timeout_ms', 1000).value
        )
        self.stale_drop_ms = int(
            self.declare_parameter('stale_drop_ms', 5000).value
        )
        self.lock_distance_m = float(
            self.declare_parameter('lock_distance_m', 1.5).value
        )
        self.lambda_cost = float(
            self.declare_parameter('lambda_cost', 1.0).value
        )
        self.alpha_switch = float(
            self.declare_parameter('alpha_switch', 0.75).value
        )
        self.beta_stale = float(
            self.declare_parameter('beta_stale', 1.0).value
        )
        self.switch_hysteresis = float(
            self.declare_parameter('switch_hysteresis', 0.25).value
        )
        self.peer_namespaces = _coerce_namespace_list(
            self.declare_parameter('peer_namespaces', ['']).value
        )

        self.core = AsyncAuctionCore(
            agent_id=self.agent_id,
            config=AsyncAuctionConfig(
                lambda_cost=self.lambda_cost,
                alpha_switch=self.alpha_switch,
                beta_stale=self.beta_stale,
                stale_timeout_ms=self.stale_timeout_ms,
                stale_drop_ms=self.stale_drop_ms,
                lock_distance_m=self.lock_distance_m,
                switch_hysteresis=self.switch_hysteresis,
            ),
        )

        self.tasks: List[Task] = []
        self.vehicle_position: Optional[VehicleLocalPosition] = None
        self.vehicle_status: Optional[VehicleStatus] = None
        self._waiting_for_position_logged = False
        self._position_received_logged = False

        px4_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.state_publisher = self.create_publisher(String, 'auction/local_state', 10)
        self.bid_publisher = self.create_publisher(
            String,
            self.bid_publish_topic,
            10,
        )
        self.allocation_publisher = self.create_publisher(String, 'auction/allocation', 10)
        self.mission_setpoint_publisher = self.create_publisher(Pose2D, 'mission_setpoint', 10)

        self.create_subscription(
            VehicleLocalPosition,
            'fmu/out/vehicle_local_position',
            self._vehicle_local_position_callback,
            px4_qos,
        )
        self.create_subscription(
            VehicleStatus,
            'fmu/out/vehicle_status',
            self._vehicle_status_callback,
            px4_qos,
        )
        self.create_subscription(
            String,
            self.tasks_topic,
            self._tasks_callback,
            10,
        )

        for peer_namespace in self.peer_namespaces:
            if peer_namespace == namespace:
                continue
            self.create_subscription(
                String,
                f'/{peer_namespace}/{self.peer_bid_topic_suffix.lstrip("/")}',
                self._neighbor_bid_callback,
                10,
            )

        self.create_timer(self.update_period_sec, self._timer_callback)
        self.get_logger().info(
            (
                f'Starting auction agent {self.agent_id} in namespace '
                f'"{self.get_namespace()}" with peers={self.peer_namespaces}'
            )
        )

    def _vehicle_local_position_callback(self, msg: VehicleLocalPosition) -> None:
        """Store the latest local position from PX4."""
        self.vehicle_position = msg
        if not self._position_received_logged:
            self._position_received_logged = True
            self.get_logger().info(
                'Received first PX4 local position sample'
            )

    def _vehicle_status_callback(self, msg: VehicleStatus) -> None:
        """Store the latest vehicle status from PX4."""
        self.vehicle_status = msg

    def _tasks_callback(self, msg: String) -> None:
        """Update the task board snapshot from the shared JSON topic."""
        try:
            self.tasks = task_list_from_json(msg.data)
        except (ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warning(f'Failed to parse task board payload: {exc}')

    def _neighbor_bid_callback(self, msg: String) -> None:
        """Merge a neighbor bid into the asynchronous auction cache."""
        try:
            bid = bid_from_json(msg.data)
        except (ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warning(f'Failed to parse neighbor bid payload: {exc}')
            return
        self.core.update_neighbor_bid(bid)

    def _timer_callback(self) -> None:
        """Publish the current local state, bid, and mission setpoint."""
        if self.vehicle_position is None:
            if not self._waiting_for_position_logged:
                self._waiting_for_position_logged = True
                self.get_logger().warning(
                    'Waiting for PX4 local position on fmu/out/vehicle_local_position'
                )
            return

        now_ns = self.get_clock().now().nanoseconds
        now_ms = int(now_ns / 1_000_000)
        current_task_id = self.core.current_task_id
        locked = False
        if current_task_id is not None:
            current_task = self._find_task(current_task_id)
            if current_task is not None:
                lock_distance = max(current_task.radius_m, self.lock_distance_m)
                locked = self._distance_to_task(current_task) <= lock_distance

        local_state = AgentAuctionState(
            agent_id=self.agent_id,
            x=float(self.vehicle_position.x),
            y=float(self.vehicle_position.y),
            vx=float(self.vehicle_position.vx),
            vy=float(self.vehicle_position.vy),
            current_task_id=current_task_id,
            locked=locked,
            stamp_ms=now_ms,
        )
        decision = self.core.step(local_state, self.tasks, now_ms)

        state_msg = String()
        state_msg.data = agent_state_to_json(decision.state)
        self.state_publisher.publish(state_msg)

        bid_msg = String()
        bid_msg.data = bid_to_json(decision.bid)
        self.bid_publisher.publish(bid_msg)

        allocation_msg = String()
        allocation_msg.data = allocation_to_json(decision.snapshot)
        self.allocation_publisher.publish(allocation_msg)

        selected_task = self._find_task(decision.snapshot.winner_task_id)
        if selected_task is not None:
            self._publish_mission_setpoint(selected_task)

    def _find_task(self, task_id: Optional[str]) -> Optional[Task]:
        """Look up a task by id from the current task board snapshot."""
        if task_id is None:
            return None
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def _distance_to_task(self, task: Task) -> float:
        """Compute the current distance to a task."""
        if self.vehicle_position is None:
            return math.inf
        return math.hypot(
            float(self.vehicle_position.x) - task.x,
            float(self.vehicle_position.y) - task.y,
        )

    def _publish_mission_setpoint(self, task: Task) -> None:
        """Publish the task location as the next local position target."""
        if self.vehicle_position is None:
            return

        msg = Pose2D()
        msg.x = task.x
        msg.y = task.y
        msg.theta = math.atan2(
            task.y - float(self.vehicle_position.y),
            task.x - float(self.vehicle_position.x),
        )
        self.mission_setpoint_publisher.publish(msg)


def main(args=None) -> None:
    """Run the asynchronous auction node."""
    rclpy.init(args=args)
    node = AuctionAgent()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
