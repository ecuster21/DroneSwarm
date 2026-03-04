#!/usr/bin/env python3

"""ROS 2 node that publishes task definitions for the auction agents."""

import json
import time
from typing import Iterable
from typing import List

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from offboard_py.auction_core import Task
from offboard_py.auction_core import task_list_to_json


def _default_tasks() -> List[Task]:
    """Provide a deterministic task layout for SITL bring-up."""
    return [
        Task(task_id='task_1', x=5.0, y=0.0, reward=10.0, radius_m=1.0, priority=1.0),
        Task(task_id='task_2', x=0.0, y=5.0, reward=8.0, radius_m=1.0, priority=1.0),
        Task(task_id='task_3', x=-5.0, y=0.0, reward=12.0, radius_m=1.0, priority=1.2),
        Task(task_id='task_4', x=0.0, y=-5.0, reward=9.0, radius_m=1.0, priority=1.0),
    ]


def _parse_tasks(payload: str) -> List[Task]:
    """Parse a JSON list of tasks, falling back to defaults on empty input."""
    if not payload.strip():
        return _default_tasks()

    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError('tasks_json must describe a JSON array.')

    tasks = [Task.from_dict(item) for item in data if isinstance(item, dict)]
    return tasks or _default_tasks()


class TaskBoard(Node):
    """Publish static and pop-up tasks for multi-agent auction testing."""

    def __init__(self) -> None:
        """Initialize task board parameters and publishers."""
        super().__init__('task_board')
        self.publish_period_sec = float(
            self.declare_parameter('publish_period_sec', 1.0).value
        )
        tasks_json = str(self.declare_parameter('tasks_json', '').value)
        popup_tasks_json = str(self.declare_parameter('popup_tasks_json', '[]').value)
        self.popup_after_sec = float(
            self.declare_parameter('popup_after_sec', 0.0).value
        )

        try:
            self.base_tasks = _parse_tasks(tasks_json)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warning(f'Invalid tasks_json, using defaults: {exc}')
            self.base_tasks = _default_tasks()

        try:
            self.popup_tasks = _parse_tasks(popup_tasks_json) if popup_tasks_json.strip() else []
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warning(f'Invalid popup_tasks_json, ignoring: {exc}')
            self.popup_tasks = []

        self.publisher = self.create_publisher(String, '/task_board/tasks', 10)
        self.start_time = time.monotonic()
        self.create_timer(self.publish_period_sec, self._timer_callback)
        self.get_logger().info(
            (
                f'Task board started with {len(self.base_tasks)} base tasks and '
                f'{len(self.popup_tasks)} popup tasks'
            )
        )

    def _timer_callback(self) -> None:
        """Publish the active task set at a fixed rate."""
        elapsed = time.monotonic() - self.start_time
        active_tasks = list(self._filter_expired(self.base_tasks, elapsed))
        if self.popup_tasks and elapsed >= self.popup_after_sec:
            active_tasks.extend(self._filter_expired(self.popup_tasks, elapsed))

        msg = String()
        msg.data = task_list_to_json(active_tasks)
        self.publisher.publish(msg)

    def _filter_expired(self, tasks: Iterable[Task], elapsed: float) -> List[Task]:
        """Drop tasks whose deadline has already elapsed."""
        active_tasks = []
        for task in tasks:
            if task.deadline_sec > 0.0 and elapsed > task.deadline_sec:
                continue
            active_tasks.append(task)
        return active_tasks


def main(args=None) -> None:
    """Run the shared task board node."""
    rclpy.init(args=args)
    node = TaskBoard()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
