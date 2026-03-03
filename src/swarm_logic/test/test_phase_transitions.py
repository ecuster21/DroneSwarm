"""Tests for the setup phase transition helper."""

from swarm_logic.planner import PHASE_FORM_UP
from swarm_logic.planner import PHASE_PATROL
from swarm_logic.planner import PHASE_TAKEOFF
from swarm_logic.planner import PHASE_TRANSIT_TO_ENTRY
from swarm_logic.planner import PHASE_WAIT_FOR_VEHICLES
from swarm_logic.planner import advance_setup_phase


def test_setup_phase_transitions_follow_the_expected_order():
    phase = PHASE_WAIT_FOR_VEHICLES
    phase = advance_setup_phase(
        phase,
        all_ready=False,
        all_active_reached=False,
    )
    assert phase == PHASE_WAIT_FOR_VEHICLES

    phase = advance_setup_phase(
        phase,
        all_ready=True,
        all_active_reached=False,
    )
    assert phase == PHASE_TAKEOFF

    phase = advance_setup_phase(
        phase,
        all_ready=True,
        all_active_reached=False,
    )
    assert phase == PHASE_TAKEOFF

    phase = advance_setup_phase(
        phase,
        all_ready=True,
        all_active_reached=True,
    )
    assert phase == PHASE_FORM_UP

    phase = advance_setup_phase(
        phase,
        all_ready=True,
        all_active_reached=True,
    )
    assert phase == PHASE_TRANSIT_TO_ENTRY

    phase = advance_setup_phase(
        phase,
        all_ready=True,
        all_active_reached=True,
    )
    assert phase == PHASE_PATROL
