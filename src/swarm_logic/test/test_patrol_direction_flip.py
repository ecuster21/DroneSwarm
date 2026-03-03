"""Tests for patrol direction toggling."""

from swarm_logic.planner import PATROL_DIRECTION_BACKWARD
from swarm_logic.planner import PATROL_DIRECTION_FORWARD
from swarm_logic.planner import next_patrol_direction


def test_patrol_direction_flips_between_forward_and_backward():
    direction = PATROL_DIRECTION_FORWARD
    direction = next_patrol_direction(direction)
    assert direction == PATROL_DIRECTION_BACKWARD

    direction = next_patrol_direction(direction)
    assert direction == PATROL_DIRECTION_FORWARD
