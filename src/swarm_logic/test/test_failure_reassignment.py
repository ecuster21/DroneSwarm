"""Tests for group-local lane reassignment behavior."""

from swarm_logic.planner import generate_grouped_phase_targets


def test_reassignment_only_changes_the_affected_group():
    full_groups = [
        [f'px4_{index}' for index in range(1, 6)],
        [f'px4_{index}' for index in range(6, 11)],
        [f'px4_{index}' for index in range(11, 16)],
        [f'px4_{index}' for index in range(16, 21)],
    ]
    reduced_groups = [
        [f'px4_{index}' for index in range(1, 5)],
        [f'px4_{index}' for index in range(6, 11)],
        [f'px4_{index}' for index in range(11, 16)],
        [f'px4_{index}' for index in range(16, 21)],
    ]

    full_targets = generate_grouped_phase_targets(
        full_groups,
        origin_x=50.0,
        origin_y=0.0,
        width_m=80.0,
        height_m=120.0,
        heading_rad=0.0,
        staging_offset_m=20.0,
        staging_spacing_m=6.0,
    )
    reduced_targets = generate_grouped_phase_targets(
        reduced_groups,
        origin_x=50.0,
        origin_y=0.0,
        width_m=80.0,
        height_m=120.0,
        heading_rad=0.0,
        staging_offset_m=20.0,
        staging_spacing_m=6.0,
    )

    assert (
        reduced_targets[0].targets['px4_1'].forward_patrol_target.y
        > full_targets[0].targets['px4_1'].forward_patrol_target.y
    )
    assert (
        reduced_targets[1].targets['px4_6'].forward_patrol_target.y
        == full_targets[1].targets['px4_6'].forward_patrol_target.y
    )
