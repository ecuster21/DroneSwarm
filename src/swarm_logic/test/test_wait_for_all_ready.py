"""Tests for waiting until all vehicles are ready."""

from swarm_logic.planner import PHASE_FORM_UP
from swarm_logic.planner import PHASE_TAKEOFF
from swarm_logic.planner import PHASE_WAIT_FOR_VEHICLES
from swarm_logic.planner import advance_setup_phase


def test_wait_for_all_ready_requires_all_ready_before_form_up():
    phase = advance_setup_phase(
        PHASE_WAIT_FOR_VEHICLES,
        all_ready=False,
        all_active_reached=False,
    )
    assert phase == PHASE_WAIT_FOR_VEHICLES

    phase = advance_setup_phase(
        PHASE_WAIT_FOR_VEHICLES,
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
