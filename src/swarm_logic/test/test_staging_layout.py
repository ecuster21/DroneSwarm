"""Tests for staging layout geometry."""

from swarm_logic.planner import generate_grouped_phase_targets


def test_staging_layout_has_four_rows_and_five_columns():
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

    row_positions = set()
    for bundle in bundles.values():
        first_namespace = next(iter(bundle.targets))
        row_positions.add(round(bundle.targets[first_namespace].form_up.x, 6))

    column_positions = {
        round(targets.form_up.y, 6)
        for targets in bundles[0].targets.values()
    }

    assert len(row_positions) == 4
    assert len(column_positions) == 5
