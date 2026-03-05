"""Pure helpers for default and popup task definitions."""

import json
from typing import List

from offboard_py.auction_core import Task


def default_tasks() -> List[Task]:
    """Provide a deterministic task layout for SITL bring-up."""
    return [
        Task(task_id='task_1', x=5.0, y=0.0, reward=10.0, radius_m=1.0, priority=1.0),
        Task(task_id='task_2', x=0.0, y=5.0, reward=8.0, radius_m=1.0, priority=1.0),
        Task(task_id='task_3', x=-5.0, y=0.0, reward=12.0, radius_m=1.0, priority=1.2),
        Task(task_id='task_4', x=0.0, y=-5.0, reward=9.0, radius_m=1.0, priority=1.0),
    ]


def parse_tasks(payload: str, use_defaults_when_empty: bool = True) -> List[Task]:
    """Parse a JSON list of tasks, optionally falling back to defaults."""
    if not payload.strip():
        return default_tasks() if use_defaults_when_empty else []

    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError('tasks_json must describe a JSON array.')

    tasks = [Task.from_dict(item) for item in data if isinstance(item, dict)]
    if tasks:
        return tasks
    return default_tasks() if use_defaults_when_empty else []
