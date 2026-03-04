from offboard_py.auction_core import AgentAuctionState
from offboard_py.auction_core import AsyncAuctionConfig
from offboard_py.auction_core import AsyncAuctionCore
from offboard_py.auction_core import BidMessage
from offboard_py.auction_core import Task


def make_state(current_task_id=None, locked=False):
    return AgentAuctionState(
        agent_id='uav_1',
        x=0.0,
        y=0.0,
        vx=0.0,
        vy=0.0,
        current_task_id=current_task_id,
        locked=locked,
        stamp_ms=0,
    )


def test_neighbor_bid_sequence_ordering():
    core = AsyncAuctionCore('uav_1')
    new_bid = BidMessage(
        agent_id='uav_2',
        candidate_task_id='task_a',
        utility=4.0,
        sequence_id=2,
        stamp_ms=200,
    )
    old_bid = BidMessage(
        agent_id='uav_2',
        candidate_task_id='task_b',
        utility=9.0,
        sequence_id=1,
        stamp_ms=300,
    )

    assert core.update_neighbor_bid(new_bid) is True
    assert core.update_neighbor_bid(old_bid) is False
    assert core.neighbor_bids['uav_2'].candidate_task_id == 'task_a'


def test_prune_neighbor_bids_removes_stale_entries():
    core = AsyncAuctionCore(
        'uav_1',
        AsyncAuctionConfig(stale_timeout_ms=100, stale_drop_ms=200),
    )
    bid = BidMessage(
        agent_id='uav_2',
        candidate_task_id='task_a',
        utility=4.0,
        sequence_id=1,
        stamp_ms=0,
    )

    core.update_neighbor_bid(bid)
    core.prune_neighbor_bids(250)

    assert core.neighbor_bids == {}


def test_locked_agent_keeps_existing_assignment():
    core = AsyncAuctionCore(
        'uav_1',
        AsyncAuctionConfig(lock_distance_m=0.5),
    )
    tasks = [
        Task(task_id='task_a', x=0.1, y=0.0, reward=10.0, radius_m=0.5),
        Task(task_id='task_b', x=5.0, y=0.0, reward=5.0, radius_m=0.5),
    ]

    first = core.step(make_state(), tasks, now_ms=10)
    second = core.step(
        make_state(current_task_id=first.snapshot.winner_task_id, locked=True),
        tasks,
        now_ms=20,
    )

    assert first.snapshot.winner_task_id == 'task_a'
    assert second.snapshot.winner_task_id == 'task_a'
    assert second.snapshot.source == 'locked'
    assert second.snapshot.state == AsyncAuctionCore.MODE_LOCKED


def test_switch_penalty_prevents_small_reassignment():
    core = AsyncAuctionCore(
        'uav_1',
        AsyncAuctionConfig(
            alpha_switch=0.1,
            switch_hysteresis=0.5,
            lock_distance_m=0.1,
        ),
    )
    initial_tasks = [
        Task(task_id='task_a', x=1.0, y=0.0, reward=6.0),
        Task(task_id='task_b', x=1.0, y=0.0, reward=5.0),
    ]
    updated_tasks = [
        Task(task_id='task_a', x=1.0, y=0.0, reward=6.0),
        Task(task_id='task_b', x=1.0, y=0.0, reward=6.4),
    ]

    first = core.step(make_state(), initial_tasks, now_ms=10)
    second = core.step(
        make_state(current_task_id=first.snapshot.winner_task_id),
        updated_tasks,
        now_ms=20,
    )

    assert first.snapshot.winner_task_id == 'task_a'
    assert second.snapshot.winner_task_id == 'task_a'
    assert second.snapshot.source == 'hysteresis'
