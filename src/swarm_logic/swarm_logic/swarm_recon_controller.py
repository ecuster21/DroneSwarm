#!/usr/bin/env python3

"""Centralized grouped patrol controller for swarm reconnaissance."""

from dataclasses import dataclass
from dataclasses import field
from functools import partial
import math
from typing import Dict
from typing import List
from typing import Optional

from geometry_msgs.msg import Pose2D
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy

from px4_msgs.msg import VehicleCommandAck
from px4_msgs.msg import VehicleLocalPosition
from px4_msgs.msg import VehicleStatus

from .planner import GroupTargetBundle
from .planner import PATROL_DIRECTION_FORWARD
from .planner import PHASE_FORM_UP
from .planner import PHASE_PATROL
from .planner import PHASE_TAKEOFF
from .planner import PHASE_TRANSIT_TO_ENTRY
from .planner import PHASE_WAIT_FOR_VEHICLES
from .planner import Pose2DTarget
from .planner import active_namespaces
from .planner import advance_setup_phase
from .planner import compute_group_center_offsets
from .planner import generate_grouped_phase_targets
from .planner import next_patrol_direction


ACK_LABELS = {
    VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED: 'ACCEPTED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_TEMPORARILY_REJECTED: 'TEMP_REJECTED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_DENIED: 'DENIED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_UNSUPPORTED: 'UNSUPPORTED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_FAILED: 'FAILED',
    VehicleCommandAck.VEHICLE_CMD_RESULT_IN_PROGRESS: 'IN_PROGRESS',
    VehicleCommandAck.VEHICLE_CMD_RESULT_CANCELLED: 'CANCELLED',
}

ACK_FAILURE_RESULTS = {
    VehicleCommandAck.VEHICLE_CMD_RESULT_DENIED,
    VehicleCommandAck.VEHICLE_CMD_RESULT_UNSUPPORTED,
    VehicleCommandAck.VEHICLE_CMD_RESULT_FAILED,
    VehicleCommandAck.VEHICLE_CMD_RESULT_CANCELLED,
}


def _coerce_bool(value) -> bool:
    """Convert ROS parameter values into a real bool."""
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


@dataclass
class VehicleContext:
    """Runtime state for one vehicle."""

    namespace: str
    instance_id: int
    system_id: int
    group_id: int
    lane_index: int
    phase: str
    active: bool = True
    is_alive: bool = False
    armed: bool = False
    is_offboard: bool = False
    seen_status: bool = False
    seen_local_position: bool = False
    ready: bool = False
    has_reached_target: bool = False
    coverage_gap: bool = False
    current_x: float = 0.0
    current_y: float = 0.0
    current_z: float = 0.0
    current_heading: float = 0.0
    spawn_x: float = 0.0
    spawn_y: float = 0.0
    last_status_time: float = 0.0
    last_position_time: float = 0.0
    last_ack_command: Optional[int] = None
    last_ack_result: Optional[int] = None
    failure_reason: Optional[str] = None
    current_target: Optional[Pose2DTarget] = None
    publisher = None


@dataclass
class GroupContext:
    """Runtime state for one patrol group."""

    group_id: int
    member_namespaces: List[str]
    subregion_center: float
    subregion_width: float
    patrol_direction: str = PATROL_DIRECTION_FORWARD
    coverage_gap: bool = False
    form_up_targets: Dict[str, Pose2DTarget] = field(default_factory=dict)
    entry_targets: Dict[str, Pose2DTarget] = field(default_factory=dict)
    forward_targets: Dict[str, Pose2DTarget] = field(default_factory=dict)
    backward_targets: Dict[str, Pose2DTarget] = field(default_factory=dict)


class SwarmReconController(Node):
    """Centralized mission planner for grouped patrol reconnaissance."""

    def __init__(self):
        super().__init__('swarm_recon_controller')
        self.num_drones = max(1, int(self.declare_parameter('num_drones', 20).value))
        self.first_instance = int(self.declare_parameter('first_instance', 1).value)
        self.namespace_prefix = str(
            self.declare_parameter('namespace_prefix', 'px4_').value
        )
        self.system_id_offset = int(
            self.declare_parameter('system_id_offset', 1).value
        )
        self.group_size = max(1, int(self.declare_parameter('group_size', 5).value))
        self.origin_x = float(self.declare_parameter('origin_x', 50.0).value)
        self.origin_y = float(self.declare_parameter('origin_y', 0.0).value)
        self.width_m = float(self.declare_parameter('width_m', 80.0).value)
        self.height_m = float(self.declare_parameter('height_m', 120.0).value)
        self.heading_rad = float(self.declare_parameter('heading_rad', 0.0).value)
        self.staging_offset_m = float(
            self.declare_parameter('staging_offset_m', 20.0).value
        )
        self.staging_spacing_m = float(
            self.declare_parameter('staging_spacing_m', 6.0).value
        )
        self.survey_altitude_z = float(
            self.declare_parameter('survey_altitude_z', -10.0).value
        )
        self.survey_speed_mps = float(
            self.declare_parameter('survey_speed_mps', 4.0).value
        )
        self.acceptance_radius_m = float(
            self.declare_parameter('acceptance_radius_m', 2.0).value
        )
        self.takeoff_acceptance_m = float(
            self.declare_parameter('takeoff_acceptance_m', 1.0).value
        )
        self.command_timeout_sec = float(
            self.declare_parameter('command_timeout_sec', 5.0).value
        )
        self.startup_wait_timeout_sec = float(
            self.declare_parameter('startup_wait_timeout_sec', 15.0).value
        )
        self.reassign_on_prestart_failure = _coerce_bool(
            self.declare_parameter('reassign_on_prestart_failure', True).value
        )
        self.spawn_layout = str(
            self.declare_parameter('spawn_layout', 'grid').value
        ).strip().lower()
        self.spawn_origin_x_m = float(
            self.declare_parameter('spawn_origin_x_m', 0.0).value
        )
        self.spawn_origin_y_m = float(
            self.declare_parameter('spawn_origin_y_m', 0.0).value
        )
        self.spawn_spacing_x_m = float(
            self.declare_parameter('spawn_spacing_x_m', 3.0).value
        )
        self.spawn_spacing_y_m = float(
            self.declare_parameter('spawn_spacing_y_m', 3.0).value
        )
        self.spawn_grid_cols = max(
            0,
            int(self.declare_parameter('spawn_grid_cols', 0).value),
        )
        self.spawn_x_m = float(self.declare_parameter('spawn_x_m', 0.0).value)
        self.spawn_y_base_m = float(
            self.declare_parameter('spawn_y_base_m', 0.0).value
        )
        self.spawn_y_step_m = float(
            self.declare_parameter('spawn_y_step_m', 3.0).value
        )
        self.group_count = max(1, math.ceil(self.num_drones / self.group_size))
        self.phase = PHASE_WAIT_FOR_VEHICLES
        self.start_time_sec = self._now_sec()
        self.wait_log_interval_sec = 5.0
        self._next_wait_log_time = self.start_time_sec + self.startup_wait_timeout_sec
        self._subscriptions = []

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.vehicle_contexts: Dict[str, VehicleContext] = {}
        self.namespace_order = []
        for index in range(self.num_drones):
            instance_id = self.first_instance + index
            namespace = f'{self.namespace_prefix}{instance_id}'
            system_id = instance_id + self.system_id_offset
            group_id = index // self.group_size
            spawn_x, spawn_y = self._compute_spawn_position(index, instance_id)
            context = VehicleContext(
                namespace=namespace,
                instance_id=instance_id,
                system_id=system_id,
                group_id=group_id,
                lane_index=index % self.group_size,
                phase=self.phase,
                spawn_x=spawn_x,
                spawn_y=spawn_y,
            )
            context.publisher = self.create_publisher(
                Pose2D,
                f'/{namespace}/mission_setpoint',
                10,
            )
            self._subscriptions.append(
                self.create_subscription(
                    VehicleStatus,
                    f'/{namespace}/fmu/out/vehicle_status',
                    partial(self._vehicle_status_callback, namespace),
                    qos_profile,
                )
            )
            self._subscriptions.append(
                self.create_subscription(
                    VehicleLocalPosition,
                    f'/{namespace}/fmu/out/vehicle_local_position',
                    partial(self._vehicle_local_position_callback, namespace),
                    qos_profile,
                )
            )
            self._subscriptions.append(
                self.create_subscription(
                    VehicleCommandAck,
                    f'/{namespace}/fmu/out/vehicle_command_ack',
                    partial(self._vehicle_command_ack_callback, namespace),
                    qos_profile,
                )
            )
            self.vehicle_contexts[namespace] = context
            self.namespace_order.append(namespace)

        group_centers = compute_group_center_offsets(self.group_count, self.width_m)
        group_width = self.width_m / float(self.group_count)
        self.group_contexts: Dict[int, GroupContext] = {}
        for group_id in range(self.group_count):
            member_namespaces = [
                namespace
                for namespace in self.namespace_order
                if self.vehicle_contexts[namespace].group_id == group_id
            ]
            self.group_contexts[group_id] = GroupContext(
                group_id=group_id,
                member_namespaces=member_namespaces,
                subregion_center=group_centers[group_id],
                subregion_width=group_width,
            )

        self._rebuild_group_targets()
        self.timer = self.create_timer(0.5, self._timer_callback)
        self.get_logger().info(
            (
                f'Starting grouped patrol controller for {self.num_drones} vehicles '
                f'in {self.group_count} groups'
            )
        )

    def _now_sec(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _update_ready_state(self, context: VehicleContext):
        context.ready = context.seen_status and context.seen_local_position

    def _resolved_spawn_grid_cols(self) -> int:
        if self.spawn_grid_cols > 0:
            return self.spawn_grid_cols

        return max(1, math.ceil(math.sqrt(self.num_drones)))

    def _compute_spawn_position(
        self,
        index: int,
        instance_id: int,
    ) -> tuple[float, float]:
        if self.spawn_layout == 'line':
            return (
                self.spawn_x_m,
                self.spawn_y_base_m + self.spawn_y_step_m * instance_id,
            )

        grid_cols = self._resolved_spawn_grid_cols()
        row_index = index // grid_cols
        col_index = index % grid_cols
        return (
            self.spawn_origin_x_m + self.spawn_spacing_x_m * col_index,
            self.spawn_origin_y_m + self.spawn_spacing_y_m * row_index,
        )

    def _vehicle_status_callback(self, namespace: str, msg: VehicleStatus):
        context = self.vehicle_contexts[namespace]
        context.armed = msg.arming_state == VehicleStatus.ARMING_STATE_ARMED
        context.is_offboard = msg.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        context.seen_status = True
        context.is_alive = True
        context.last_status_time = self._now_sec()
        self._update_ready_state(context)

    def _vehicle_local_position_callback(
        self,
        namespace: str,
        msg: VehicleLocalPosition,
    ):
        context = self.vehicle_contexts[namespace]
        context.current_x = float(msg.x)
        context.current_y = float(msg.y)
        context.current_z = float(msg.z)
        context.current_heading = float(msg.heading)
        context.seen_local_position = True
        context.is_alive = True
        context.last_position_time = self._now_sec()
        self._update_ready_state(context)

    def _vehicle_command_ack_callback(self, namespace: str, msg: VehicleCommandAck):
        context = self.vehicle_contexts[namespace]
        if (
            context.last_ack_command == msg.command
            and context.last_ack_result == msg.result
        ):
            return

        context.last_ack_command = msg.command
        context.last_ack_result = msg.result
        label = ACK_LABELS.get(msg.result, f'UNKNOWN_{msg.result}')
        log_message = (
            f'{namespace} ack command={msg.command} '
            f'result={label} target_system={msg.target_system}'
        )
        if msg.result in ACK_FAILURE_RESULTS:
            self.get_logger().warning(log_message)
            if self.phase != PHASE_WAIT_FOR_VEHICLES and context.active:
                self._handle_vehicle_loss(context, 'ack rejection')
        elif msg.result == VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED:
            self.get_logger().info(log_message)
        else:
            self.get_logger().debug(log_message)

    def _active_contexts(self) -> List[VehicleContext]:
        ordered_namespaces = active_namespaces(
            self.namespace_order,
            [
                namespace
                for namespace, context in self.vehicle_contexts.items()
                if not context.active
            ],
        )
        return [self.vehicle_contexts[namespace] for namespace in ordered_namespaces]

    def _active_group_members(self, group_id: int) -> List[str]:
        return [
            namespace
            for namespace in self.group_contexts[group_id].member_namespaces
            if self.vehicle_contexts[namespace].active
        ]

    def _all_configured_ready(self) -> bool:
        return all(context.ready for context in self.vehicle_contexts.values())

    def _all_active_reached(self) -> bool:
        active_contexts = self._active_contexts()
        if not active_contexts:
            return False

        return all(context.has_reached_target for context in active_contexts)

    def _all_active_at_takeoff_altitude(self) -> bool:
        active_contexts = self._active_contexts()
        if not active_contexts:
            return False

        return all(
            abs(context.current_z - self.survey_altitude_z)
            <= self.takeoff_acceptance_m
            for context in active_contexts
        )

    def _group_all_reached(self, group_id: int) -> bool:
        members = [
            self.vehicle_contexts[namespace]
            for namespace in self._active_group_members(group_id)
        ]
        if not members:
            return False

        return all(context.has_reached_target for context in members)

    def _not_ready_namespaces(self) -> List[str]:
        return [
            namespace
            for namespace, context in self.vehicle_contexts.items()
            if not context.ready
        ]

    def _log_waiting_status(self):
        now_sec = self._now_sec()
        if now_sec < self._next_wait_log_time:
            return

        not_ready = self._not_ready_namespaces()
        if not_ready:
            joined = ', '.join(not_ready)
            self.get_logger().warning(
                f'Waiting for ready vehicles: {joined}'
            )
        self._next_wait_log_time = now_sec + self.wait_log_interval_sec

    def _select_target(
        self,
        context: VehicleContext,
    ) -> Optional[Pose2DTarget]:
        group = self.group_contexts[context.group_id]
        if self.phase == PHASE_WAIT_FOR_VEHICLES:
            return None
        if self.phase == PHASE_TAKEOFF:
            return Pose2DTarget(
                x=0.0,
                y=0.0,
                yaw=self.heading_rad,
            )
        if self.phase == PHASE_FORM_UP:
            return self._world_to_local_target(
                context,
                group.form_up_targets.get(context.namespace),
            )
        if self.phase == PHASE_TRANSIT_TO_ENTRY:
            return self._world_to_local_target(
                context,
                group.entry_targets.get(context.namespace),
            )
        if self.phase == PHASE_PATROL:
            if group.patrol_direction == PATROL_DIRECTION_FORWARD:
                return self._world_to_local_target(
                    context,
                    group.forward_targets.get(context.namespace),
                )
            return self._world_to_local_target(
                context,
                group.backward_targets.get(context.namespace),
            )
        return None

    def _world_to_local_target(
        self,
        context: VehicleContext,
        target: Optional[Pose2DTarget],
    ) -> Optional[Pose2DTarget]:
        if target is None:
            return None

        return Pose2DTarget(
            x=target.x - context.spawn_x,
            y=target.y - context.spawn_y,
            yaw=target.yaw,
        )

    def _sync_targets(self, reset_reached: bool):
        for context in self.vehicle_contexts.values():
            if not context.active:
                context.current_target = None
                context.has_reached_target = False
                continue

            context.current_target = self._select_target(context)
            context.phase = self.phase
            if reset_reached:
                context.has_reached_target = False

    def _sync_group_targets(self, group_id: int):
        for namespace in self.group_contexts[group_id].member_namespaces:
            context = self.vehicle_contexts[namespace]
            if not context.active:
                context.current_target = None
                context.has_reached_target = False
                continue

            context.current_target = self._select_target(context)
            context.phase = self.phase
            context.has_reached_target = False

    def _rebuild_group_targets(self):
        ordered_groups = [
            self._active_group_members(group_id)
            for group_id in range(self.group_count)
        ]
        bundles = generate_grouped_phase_targets(
            ordered_groups,
            origin_x=self.origin_x,
            origin_y=self.origin_y,
            width_m=self.width_m,
            height_m=self.height_m,
            heading_rad=self.heading_rad,
            staging_offset_m=self.staging_offset_m,
            staging_spacing_m=self.staging_spacing_m,
        )
        for group_id, group in self.group_contexts.items():
            bundle = bundles.get(group_id, GroupTargetBundle(
                group_id=group_id,
                center_offset=group.subregion_center,
                width=group.subregion_width,
                targets={},
            ))
            group.subregion_center = bundle.center_offset
            group.subregion_width = bundle.width
            group.form_up_targets = {
                namespace: phase_targets.form_up
                for namespace, phase_targets in bundle.targets.items()
            }
            group.entry_targets = {
                namespace: phase_targets.entry_target
                for namespace, phase_targets in bundle.targets.items()
            }
            group.forward_targets = {
                namespace: phase_targets.forward_patrol_target
                for namespace, phase_targets in bundle.targets.items()
            }
            group.backward_targets = {
                namespace: phase_targets.backward_patrol_target
                for namespace, phase_targets in bundle.targets.items()
            }
            for lane_index, namespace in enumerate(ordered_groups[group_id]):
                self.vehicle_contexts[namespace].lane_index = lane_index

        self._sync_targets(reset_reached=True)

    def _set_phase(self, new_phase: str):
        if new_phase == self.phase:
            return

        self.phase = new_phase
        if new_phase == PHASE_PATROL:
            for group in self.group_contexts.values():
                group.patrol_direction = PATROL_DIRECTION_FORWARD
        self._sync_targets(reset_reached=True)
        self.get_logger().info(
            f'Phase changed to {self.phase} with {len(self._active_contexts())} active vehicles'
        )

    def _mark_inactive(self, context: VehicleContext, reason: str):
        if not context.active:
            return

        context.active = False
        context.is_alive = False
        context.has_reached_target = False
        context.failure_reason = reason
        if self.phase == PHASE_PATROL:
            context.coverage_gap = True
            self.group_contexts[context.group_id].coverage_gap = True
        self.get_logger().warning(
            f'{context.namespace} marked inactive during {self.phase}: {reason}'
        )

    def _handle_vehicle_loss(self, context: VehicleContext, reason: str):
        pre_patrol = self.phase in (PHASE_FORM_UP, PHASE_TRANSIT_TO_ENTRY)
        self._mark_inactive(context, reason)
        if pre_patrol and self.reassign_on_prestart_failure:
            self._rebuild_group_targets()

    def _refresh_timeouts(self):
        if self.phase == PHASE_WAIT_FOR_VEHICLES:
            return

        now_sec = self._now_sec()
        for context in self.vehicle_contexts.values():
            if not context.active:
                continue

            last_position_time = context.last_position_time
            stale = (
                last_position_time == 0.0
                or (now_sec - last_position_time) > self.command_timeout_sec
            )
            if stale:
                self._handle_vehicle_loss(context, 'no position updates')

    def _update_reached_flags(self):
        for context in self.vehicle_contexts.values():
            if not context.active or context.current_target is None:
                context.has_reached_target = False
                continue

            distance = math.hypot(
                context.current_x - context.current_target.x,
                context.current_y - context.current_target.y,
            )
            context.has_reached_target = distance <= self.acceptance_radius_m

    def _publish_targets(self):
        for context in self._active_contexts():
            if context.current_target is None:
                continue

            msg = Pose2D()
            msg.x = context.current_target.x
            msg.y = context.current_target.y
            msg.theta = context.current_target.yaw
            context.publisher.publish(msg)

    def _flip_patrol_groups(self):
        for group_id, group in self.group_contexts.items():
            if not self._group_all_reached(group_id):
                continue

            old_direction = group.patrol_direction
            group.patrol_direction = next_patrol_direction(group.patrol_direction)
            self._sync_group_targets(group_id)
            self.get_logger().info(
                (
                    f'Group {group_id} patrol direction '
                    f'{old_direction} -> {group.patrol_direction}'
                )
            )

    def _timer_callback(self):
        if self.phase == PHASE_WAIT_FOR_VEHICLES:
            self._log_waiting_status()
            next_phase = advance_setup_phase(
                self.phase,
                all_ready=self._all_configured_ready(),
                all_active_reached=False,
            )
            self._set_phase(next_phase)
            self._publish_targets()
            return

        self._refresh_timeouts()
        self._update_reached_flags()

        if self.phase in (PHASE_TAKEOFF, PHASE_FORM_UP, PHASE_TRANSIT_TO_ENTRY):
            next_phase = advance_setup_phase(
                self.phase,
                all_ready=True,
                all_active_reached=(
                    self._all_active_at_takeoff_altitude()
                    if self.phase == PHASE_TAKEOFF
                    else self._all_active_reached()
                ),
            )
            self._set_phase(next_phase)
        elif self.phase == PHASE_PATROL:
            self._flip_patrol_groups()

        self._publish_targets()


def main(args=None):
    """Run the swarm mission controller."""
    rclpy.init(args=args)
    controller = SwarmReconController()
    rclpy.spin(controller)
    controller.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
