"""Tests for grouped lane allocation helpers."""

from swarm_logic.planner import compute_group_center_offsets
from swarm_logic.planner import compute_lane_center_offsets


def test_group_centers_and_group_lane_centers_are_evenly_spaced():
    group_offsets = compute_group_center_offsets(4, 80.0)
    lane_offsets = compute_lane_center_offsets(5, 20.0)

    assert group_offsets == [-30.0, -10.0, 10.0, 30.0]
    assert lane_offsets == [-8.0, -4.0, 0.0, 4.0, 8.0]
