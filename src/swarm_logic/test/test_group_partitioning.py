"""Tests for splitting the survey area into group subregions."""

from swarm_logic.planner import generate_grouped_phase_targets


def test_groups_are_partitioned_into_four_subregions():
    groups = [
        [f'px4_{index}' for index in range(1, 6)],
        [f'px4_{index}' for index in range(6, 11)],
        [f'px4_{index}' for index in range(11, 16)],
        [f'px4_{index}' for index in range(16, 21)],
    ]
    bundles = generate_grouped_phase_targets(
        groups,
        origin_x=50.0,
        origin_y=0.0,
        width_m=80.0,
        height_m=120.0,
        heading_rad=0.0,
        staging_offset_m=20.0,
        staging_spacing_m=6.0,
    )

    assert len(bundles) == 4
    assert bundles[0].width == 20.0
    assert bundles[1].center_offset == -10.0
    assert bundles[2].center_offset == 10.0
    assert bundles[3].center_offset == 30.0

    for group_id, bundle in bundles.items():
        left_bound = bundle.center_offset - (bundle.width / 2.0)
        right_bound = bundle.center_offset + (bundle.width / 2.0)
        for phase_targets in bundle.targets.values():
            local_y = phase_targets.forward_patrol_target.y
            assert left_bound <= local_y <= right_bound
