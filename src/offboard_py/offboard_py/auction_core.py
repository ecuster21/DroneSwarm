"""Core logic for an asynchronous robust auction allocator."""

from dataclasses import asdict
from dataclasses import dataclass
import json
import math
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional


def _normalize_id(value, default_value: str) -> str:
    """Normalize ids so comparisons remain stable across JSON payloads."""
    if value is None:
        return default_value
    return str(value)


def _coerce_float(value, default_value: float = 0.0) -> float:
    """Convert arbitrary JSON values into floats."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default_value


def _coerce_int(value, default_value: int = 0) -> int:
    """Convert arbitrary JSON values into integers."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default_value


def _distance(x0: float, y0: float, x1: float, y1: float) -> float:
    """Compute the planar distance between two points."""
    return math.hypot(x1 - x0, y1 - y0)


@dataclass
class Task:
    """Serializable task description shared by the task board."""

    task_id: str
    x: float
    y: float
    z: float = 0.0
    reward: float = 1.0
    deadline_sec: float = 0.0
    radius_m: float = 1.0
    priority: float = 1.0

    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        """Create a task from a loosely-typed JSON object."""
        return cls(
            task_id=_normalize_id(data.get('task_id'), 'task'),
            x=_coerce_float(data.get('x')),
            y=_coerce_float(data.get('y')),
            z=_coerce_float(data.get('z')),
            reward=_coerce_float(data.get('reward'), 1.0),
            deadline_sec=_coerce_float(data.get('deadline_sec')),
            radius_m=max(0.0, _coerce_float(data.get('radius_m'), 1.0)),
            priority=max(0.1, _coerce_float(data.get('priority'), 1.0)),
        )

    def to_dict(self) -> Dict:
        """Serialize the task into a JSON-friendly dictionary."""
        return asdict(self)


@dataclass
class AgentAuctionState:
    """Compact local agent state used by the auction core."""

    agent_id: str
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    current_task_id: Optional[str] = None
    locked: bool = False
    stamp_ms: int = 0

    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentAuctionState':
        """Create an agent state from JSON payload data."""
        return cls(
            agent_id=_normalize_id(data.get('agent_id'), 'agent'),
            x=_coerce_float(data.get('x')),
            y=_coerce_float(data.get('y')),
            vx=_coerce_float(data.get('vx')),
            vy=_coerce_float(data.get('vy')),
            current_task_id=(
                _normalize_id(data.get('current_task_id'), '')
                if data.get('current_task_id') not in (None, '')
                else None
            ),
            locked=bool(data.get('locked', False)),
            stamp_ms=_coerce_int(data.get('stamp_ms')),
        )

    def to_dict(self) -> Dict:
        """Serialize the agent state into a JSON-friendly dictionary."""
        return asdict(self)


@dataclass
class BidMessage:
    """Best-known bid published by an agent."""

    agent_id: str
    candidate_task_id: Optional[str]
    utility: float
    sequence_id: int
    stamp_ms: int
    info_age_ms: int = 0

    @classmethod
    def from_dict(cls, data: Dict) -> 'BidMessage':
        """Create a bid from JSON payload data."""
        task_id = data.get('candidate_task_id')
        return cls(
            agent_id=_normalize_id(data.get('agent_id'), 'agent'),
            candidate_task_id=(
                _normalize_id(task_id, '') if task_id not in (None, '') else None
            ),
            utility=_coerce_float(data.get('utility')),
            sequence_id=_coerce_int(data.get('sequence_id')),
            stamp_ms=_coerce_int(data.get('stamp_ms')),
            info_age_ms=max(0, _coerce_int(data.get('info_age_ms'))),
        )

    def to_dict(self) -> Dict:
        """Serialize the bid into a JSON-friendly dictionary."""
        return asdict(self)


@dataclass
class AllocationSnapshot:
    """Allocation decision emitted by the auction core."""

    agent_id: str
    winner_task_id: Optional[str]
    utility: float
    source: str
    state: str
    stamp_ms: int

    def to_dict(self) -> Dict:
        """Serialize the allocation into a JSON-friendly dictionary."""
        return asdict(self)


@dataclass
class AuctionDecision:
    """Full decision bundle produced by one auction step."""

    bid: BidMessage
    snapshot: AllocationSnapshot
    state: AgentAuctionState


@dataclass
class AsyncAuctionConfig:
    """Tunable parameters for the asynchronous robust auction."""

    lambda_cost: float = 1.0
    alpha_switch: float = 0.75
    beta_stale: float = 1.0
    stale_timeout_ms: int = 1000
    stale_drop_ms: int = 5000
    lock_distance_m: float = 1.0
    switch_hysteresis: float = 0.25


class AsyncAuctionCore:
    """Minimal asynchronous auction engine for one agent."""

    MODE_ACTIVE = 'ACTIVE'
    MODE_LOCKED = 'LOCKED'
    MODE_STALE = 'STALE'

    def __init__(
        self,
        agent_id: str,
        config: Optional[AsyncAuctionConfig] = None,
    ) -> None:
        """Initialize the per-agent auction state."""
        self.agent_id = _normalize_id(agent_id, 'agent')
        self.config = config or AsyncAuctionConfig()
        self.current_task_id: Optional[str] = None
        self.current_utility = 0.0
        self.sequence_id = 0
        self.mode = self.MODE_ACTIVE
        self.neighbor_bids: Dict[str, BidMessage] = {}

    def update_neighbor_bid(self, bid: BidMessage) -> bool:
        """Merge a neighbor bid if it is newer than the cached copy."""
        if bid.agent_id == self.agent_id:
            return False

        current_bid = self.neighbor_bids.get(bid.agent_id)
        if current_bid is None:
            self.neighbor_bids[bid.agent_id] = bid
            return True

        if bid.sequence_id < current_bid.sequence_id:
            return False

        if (
            bid.sequence_id == current_bid.sequence_id
            and bid.stamp_ms <= current_bid.stamp_ms
        ):
            return False

        self.neighbor_bids[bid.agent_id] = bid
        return True

    def prune_neighbor_bids(self, now_ms: int) -> None:
        """Drop bids that are too old to trust."""
        expired_agents = []
        for agent_id, bid in self.neighbor_bids.items():
            if now_ms - bid.stamp_ms > self.config.stale_drop_ms:
                expired_agents.append(agent_id)

        for agent_id in expired_agents:
            del self.neighbor_bids[agent_id]

    def step(
        self,
        agent_state: AgentAuctionState,
        tasks: Iterable[Task],
        now_ms: int,
    ) -> AuctionDecision:
        """Compute the next asynchronous auction decision."""
        self.prune_neighbor_bids(now_ms)
        task_list = list(tasks)
        tasks_by_id = {task.task_id: task for task in task_list}

        if self.current_task_id not in tasks_by_id:
            self.current_task_id = None
            self.current_utility = 0.0
            self.mode = self.MODE_ACTIVE

        if (
            agent_state.locked
            and self.current_task_id is not None
            and self.current_task_id in tasks_by_id
        ):
            return self._build_locked_decision(
                agent_state,
                tasks_by_id[self.current_task_id],
                now_ms,
            )

        if not task_list:
            return self._build_idle_decision(agent_state, now_ms)

        utilities = {
            task.task_id: self._compute_task_utility(
                agent_state,
                task,
                tasks_by_id,
                now_ms,
                apply_switch_penalty=True,
            )
            for task in task_list
        }

        selected_task_id = max(utilities, key=utilities.get)
        selected_utility = utilities[selected_task_id]
        selected_source = 'local'

        if self.current_task_id is not None and self.current_task_id in tasks_by_id:
            current_task_utility = self._compute_task_utility(
                agent_state,
                tasks_by_id[self.current_task_id],
                tasks_by_id,
                now_ms,
                apply_switch_penalty=False,
            )
            should_keep_current = (
                selected_task_id != self.current_task_id
                and selected_utility
                <= current_task_utility + self.config.switch_hysteresis
            )
            if should_keep_current:
                selected_task_id = self.current_task_id
                selected_utility = current_task_utility
                selected_source = 'hysteresis'

        previous_task_id = self.current_task_id
        previous_utility = self.current_utility
        previous_mode = self.mode

        self.current_task_id = selected_task_id
        self.current_utility = selected_utility
        self.mode = self._determine_mode(agent_state, tasks_by_id[selected_task_id], now_ms)
        if self.mode == self.MODE_STALE:
            selected_source = 'stale_fallback'

        if (
            previous_task_id != self.current_task_id
            or abs(previous_utility - self.current_utility) > 1e-6
            or previous_mode != self.mode
        ):
            self.sequence_id += 1

        state = self._build_state(agent_state, now_ms)
        bid = BidMessage(
            agent_id=self.agent_id,
            candidate_task_id=self.current_task_id,
            utility=self.current_utility,
            sequence_id=self.sequence_id,
            stamp_ms=now_ms,
            info_age_ms=self._max_neighbor_age(now_ms),
        )
        snapshot = AllocationSnapshot(
            agent_id=self.agent_id,
            winner_task_id=self.current_task_id,
            utility=self.current_utility,
            source=selected_source,
            state=self.mode,
            stamp_ms=now_ms,
        )
        return AuctionDecision(bid=bid, snapshot=snapshot, state=state)

    def _build_idle_decision(
        self,
        agent_state: AgentAuctionState,
        now_ms: int,
    ) -> AuctionDecision:
        """Build a no-task decision when the task board is empty."""
        previous_task_id = self.current_task_id
        previous_utility = self.current_utility
        previous_mode = self.mode
        self.current_task_id = None
        self.current_utility = 0.0
        self.mode = self.MODE_ACTIVE
        if (
            previous_task_id is not None
            or abs(previous_utility) > 1e-6
            or previous_mode != self.mode
        ):
            self.sequence_id += 1

        state = self._build_state(agent_state, now_ms)
        bid = BidMessage(
            agent_id=self.agent_id,
            candidate_task_id=None,
            utility=0.0,
            sequence_id=self.sequence_id,
            stamp_ms=now_ms,
            info_age_ms=self._max_neighbor_age(now_ms),
        )
        snapshot = AllocationSnapshot(
            agent_id=self.agent_id,
            winner_task_id=None,
            utility=0.0,
            source='idle',
            state=self.mode,
            stamp_ms=now_ms,
        )
        return AuctionDecision(bid=bid, snapshot=snapshot, state=state)

    def _build_locked_decision(
        self,
        agent_state: AgentAuctionState,
        task: Task,
        now_ms: int,
    ) -> AuctionDecision:
        """Republish the current assignment without rebidding logic."""
        self.mode = self.MODE_LOCKED
        state = self._build_state(agent_state, now_ms)
        bid = BidMessage(
            agent_id=self.agent_id,
            candidate_task_id=self.current_task_id,
            utility=self.current_utility,
            sequence_id=self.sequence_id,
            stamp_ms=now_ms,
            info_age_ms=self._max_neighbor_age(now_ms),
        )
        snapshot = AllocationSnapshot(
            agent_id=self.agent_id,
            winner_task_id=task.task_id,
            utility=self.current_utility,
            source='locked',
            state=self.mode,
            stamp_ms=now_ms,
        )
        return AuctionDecision(bid=bid, snapshot=snapshot, state=state)

    def _build_state(self, agent_state: AgentAuctionState, now_ms: int) -> AgentAuctionState:
        """Return the latest externally visible agent state."""
        return AgentAuctionState(
            agent_id=self.agent_id,
            x=agent_state.x,
            y=agent_state.y,
            vx=agent_state.vx,
            vy=agent_state.vy,
            current_task_id=self.current_task_id,
            locked=self.mode == self.MODE_LOCKED,
            stamp_ms=now_ms,
        )

    def _determine_mode(
        self,
        agent_state: AgentAuctionState,
        task: Task,
        now_ms: int,
    ) -> str:
        """Determine whether the agent is active, stale, or locked."""
        distance_to_task = _distance(agent_state.x, agent_state.y, task.x, task.y)
        lock_distance = max(task.radius_m, self.config.lock_distance_m)
        if distance_to_task <= lock_distance:
            return self.MODE_LOCKED

        stale_agents = 0
        for bid in self.neighbor_bids.values():
            if now_ms - bid.stamp_ms > self.config.stale_timeout_ms:
                stale_agents += 1
        if stale_agents:
            return self.MODE_STALE
        return self.MODE_ACTIVE

    def _compute_task_utility(
        self,
        agent_state: AgentAuctionState,
        task: Task,
        tasks_by_id: Dict[str, Task],
        now_ms: int,
        apply_switch_penalty: bool,
    ) -> float:
        """Compute the robust utility for a candidate task."""
        occupancy = 1 + self._estimated_occupancy(task.task_id, now_ms)
        reward_term = self._reward_term(task)
        marginal_reward = reward_term / occupancy
        motion_cost = _distance(agent_state.x, agent_state.y, task.x, task.y)
        switch_cost = 0.0
        if apply_switch_penalty:
            switch_cost = self._switch_cost(agent_state, task, tasks_by_id)
        stale_risk = self._stale_risk(task.task_id, now_ms)
        return (
            marginal_reward
            - self.config.lambda_cost * motion_cost
            - self.config.alpha_switch * switch_cost
            - self.config.beta_stale * stale_risk
        )

    def _reward_term(self, task: Task) -> float:
        """Compute the task reward with a mild urgency boost."""
        urgency_boost = 1.0
        if task.deadline_sec > 0.0:
            urgency_boost += min(1.0, 1.0 / max(task.deadline_sec, 1.0))
        return max(0.0, task.reward) * max(0.1, task.priority) * urgency_boost

    def _estimated_occupancy(self, task_id: str, now_ms: int) -> int:
        """Estimate how many neighbor agents are already selecting a task."""
        count = 0
        for bid in self.neighbor_bids.values():
            if now_ms - bid.stamp_ms > self.config.stale_drop_ms:
                continue
            if bid.candidate_task_id == task_id:
                count += 1
        return count

    def _switch_cost(
        self,
        agent_state: AgentAuctionState,
        next_task: Task,
        tasks_by_id: Dict[str, Task],
    ) -> float:
        """Compute the penalty for switching away from the current task."""
        if self.current_task_id is None or self.current_task_id == next_task.task_id:
            return 0.0

        penalty = 1.0
        previous_task = tasks_by_id.get(self.current_task_id)
        if previous_task is not None:
            penalty += 0.5 * _distance(
                previous_task.x,
                previous_task.y,
                next_task.x,
                next_task.y,
            )
        else:
            penalty += 0.25 * _distance(
                agent_state.x,
                agent_state.y,
                next_task.x,
                next_task.y,
            )

        speed = math.hypot(agent_state.vx, agent_state.vy)
        if speed > 1e-6:
            desired_heading = math.atan2(next_task.y - agent_state.y, next_task.x - agent_state.x)
            current_heading = math.atan2(agent_state.vy, agent_state.vx)
            angle_delta = abs(math.atan2(
                math.sin(desired_heading - current_heading),
                math.cos(desired_heading - current_heading),
            ))
            penalty += angle_delta / math.pi

        return penalty

    def _stale_risk(self, task_id: str, now_ms: int) -> float:
        """Estimate the uncertainty caused by delayed neighbor bids."""
        if not self.neighbor_bids:
            return 0.0

        relevant_ages = []
        fallback_ages = []
        for bid in self.neighbor_bids.values():
            age_ms = max(0, now_ms - bid.stamp_ms)
            if age_ms > self.config.stale_drop_ms:
                continue

            normalized_age = min(age_ms / max(self.config.stale_drop_ms, 1), 1.0)
            fallback_ages.append(normalized_age)
            if bid.candidate_task_id == task_id:
                relevant_ages.append(normalized_age)

        ages = relevant_ages or fallback_ages
        if not ages:
            return 0.0
        return sum(ages) / len(ages)

    def _max_neighbor_age(self, now_ms: int) -> int:
        """Report the largest retained neighbor bid age."""
        if not self.neighbor_bids:
            return 0
        return max(0, max(now_ms - bid.stamp_ms for bid in self.neighbor_bids.values()))


def task_list_to_json(tasks: Iterable[Task]) -> str:
    """Serialize a list of tasks into a JSON string."""
    return json.dumps([task.to_dict() for task in tasks], sort_keys=True)


def task_list_from_json(data: str) -> List[Task]:
    """Deserialize a JSON string into a list of tasks."""
    if not data:
        return []
    payload = json.loads(data)
    if not isinstance(payload, list):
        return []
    return [Task.from_dict(item) for item in payload if isinstance(item, dict)]


def bid_to_json(bid: BidMessage) -> str:
    """Serialize a bid message into a JSON string."""
    return json.dumps(bid.to_dict(), sort_keys=True)


def bid_from_json(data: str) -> BidMessage:
    """Deserialize a JSON string into a bid message."""
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError('Bid payload must be a JSON object.')
    return BidMessage.from_dict(payload)


def agent_state_to_json(agent_state: AgentAuctionState) -> str:
    """Serialize an agent auction state into a JSON string."""
    return json.dumps(agent_state.to_dict(), sort_keys=True)


def allocation_to_json(snapshot: AllocationSnapshot) -> str:
    """Serialize an allocation snapshot into a JSON string."""
    return json.dumps(snapshot.to_dict(), sort_keys=True)
