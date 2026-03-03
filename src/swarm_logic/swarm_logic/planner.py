"""Pure planning helpers for the grouped swarm reconnaissance mission."""

from dataclasses import dataclass
import math
from typing import Dict
from typing import Iterable
from typing import List
from typing import Sequence
from typing import Tuple


PHASE_WAIT_FOR_VEHICLES = 'WAIT_FOR_VEHICLES'
PHASE_TAKEOFF = 'TAKEOFF'
PHASE_FORM_UP = 'FORM_UP'
PHASE_TRANSIT_TO_ENTRY = 'TRANSIT_TO_ENTRY'
PHASE_PATROL = 'PATROL'

PATROL_DIRECTION_FORWARD = 'forward'
PATROL_DIRECTION_BACKWARD = 'backward'


@dataclass(frozen=True)
class Pose2DTarget:
    """Simple target pose in the PX4 local NED frame."""

    x: float
    y: float
    yaw: float


@dataclass(frozen=True)
class VehiclePhaseTargets:
    """All phase targets for one vehicle."""

    form_up: Pose2DTarget
    entry_target: Pose2DTarget
    forward_patrol_target: Pose2DTarget
    backward_patrol_target: Pose2DTarget


@dataclass(frozen=True)
class GroupTargetBundle:
    """Targets and geometry for one swarm group."""

    group_id: int
    center_offset: float
    width: float
    targets: Dict[str, VehiclePhaseTargets]


def compute_even_offsets(count: int, span_m: float) -> List[float]:
    """Return evenly spaced center offsets across a span."""
    if count <= 0:
        return []

    spacing = span_m / float(count)
    first_center = (-span_m / 2.0) + (spacing / 2.0)
    return [first_center + spacing * index for index in range(count)]


def compute_lane_center_offsets(num_lanes: int, width_m: float) -> List[float]:
    """Return evenly spaced lane centers across a group width."""
    return compute_even_offsets(num_lanes, width_m)


def compute_group_center_offsets(num_groups: int, width_m: float) -> List[float]:
    """Return evenly spaced group centers across the full area width."""
    return compute_even_offsets(num_groups, width_m)


def rotate_xy(
    x_local: float,
    y_local: float,
    heading_rad: float,
) -> Tuple[float, float]:
    """Rotate a local point into the world frame."""
    cos_heading = math.cos(heading_rad)
    sin_heading = math.sin(heading_rad)
    return (
        x_local * cos_heading - y_local * sin_heading,
        x_local * sin_heading + y_local * cos_heading,
    )


def local_to_world(
    origin_x: float,
    origin_y: float,
    along_track: float,
    across_track: float,
    heading_rad: float,
) -> Pose2DTarget:
    """Convert along/across-track coordinates into NED x/y."""
    x_rotated, y_rotated = rotate_xy(
        along_track,
        across_track,
        heading_rad,
    )
    return Pose2DTarget(
        x=origin_x + x_rotated,
        y=origin_y + y_rotated,
        yaw=heading_rad,
    )


def generate_grouped_phase_targets(
    group_namespaces: Sequence[Sequence[str]],
    *,
    origin_x: float,
    origin_y: float,
    width_m: float,
    height_m: float,
    heading_rad: float,
    staging_offset_m: float,
    staging_spacing_m: float,
) -> Dict[int, GroupTargetBundle]:
    """Generate fixed targets for all groups and their members."""
    group_count = len(group_namespaces)
    if group_count <= 0:
        return {}

    half_height = height_m / 2.0
    group_width = width_m / float(group_count)
    group_centers = compute_group_center_offsets(group_count, width_m)
    bundles: Dict[int, GroupTargetBundle] = {}

    for group_id, namespaces in enumerate(group_namespaces):
        group_center = group_centers[group_id]
        lane_offsets = compute_lane_center_offsets(len(namespaces), group_width)
        targets: Dict[str, VehiclePhaseTargets] = {}
        member_count = len(namespaces)
        for slot_index, namespace in enumerate(namespaces):
            centered_slot = slot_index - ((member_count - 1) / 2.0)
            across_track = group_center + lane_offsets[slot_index]
            form_up = local_to_world(
                origin_x,
                origin_y,
                -half_height - staging_offset_m - group_id * staging_spacing_m,
                centered_slot * staging_spacing_m,
                heading_rad,
            )
            entry_target = local_to_world(
                origin_x,
                origin_y,
                -half_height - (staging_offset_m / 2.0),
                across_track,
                heading_rad,
            )
            forward_target = local_to_world(
                origin_x,
                origin_y,
                half_height,
                across_track,
                heading_rad,
            )
            backward_target = local_to_world(
                origin_x,
                origin_y,
                -half_height,
                across_track,
                heading_rad,
            )
            targets[namespace] = VehiclePhaseTargets(
                form_up=form_up,
                entry_target=entry_target,
                forward_patrol_target=forward_target,
                backward_patrol_target=backward_target,
            )

        bundles[group_id] = GroupTargetBundle(
            group_id=group_id,
            center_offset=group_center,
            width=group_width,
            targets=targets,
        )

    return bundles


def advance_setup_phase(
    current_phase: str,
    *,
    all_ready: bool,
    all_active_reached: bool,
) -> str:
    """Advance setup phases before the controller enters persistent patrol."""
    if current_phase == PHASE_WAIT_FOR_VEHICLES and all_ready:
        return PHASE_TAKEOFF

    if current_phase == PHASE_TAKEOFF and all_active_reached:
        return PHASE_FORM_UP

    if current_phase == PHASE_FORM_UP and all_active_reached:
        return PHASE_TRANSIT_TO_ENTRY

    if current_phase == PHASE_TRANSIT_TO_ENTRY and all_active_reached:
        return PHASE_PATROL

    return current_phase


def next_patrol_direction(direction: str) -> str:
    """Toggle a patrol direction string."""
    if direction == PATROL_DIRECTION_FORWARD:
        return PATROL_DIRECTION_BACKWARD

    return PATROL_DIRECTION_FORWARD


def active_namespaces(
    namespaces: Iterable[str],
    inactive: Iterable[str],
) -> List[str]:
    """Return namespaces preserving order while filtering inactive entries."""
    inactive_set = set(inactive)
    return [namespace for namespace in namespaces if namespace not in inactive_set]
