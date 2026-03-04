#!/usr/bin/env python3

"""ROS 2 topic relay that injects delay, jitter, and packet drops."""

import random
import time
from typing import List
from typing import Tuple

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class NetworkFaultInjector(Node):
    """Relay string messages while simulating unreliable communication."""

    def __init__(self) -> None:
        """Initialize the configurable fault-injection relay."""
        super().__init__('network_faults')
        self.input_topic = str(
            self.declare_parameter('input_topic', '/auction/raw').value
        )
        self.output_topic = str(
            self.declare_parameter('output_topic', '/auction/faulty').value
        )
        self.drop_probability = min(
            1.0,
            max(0.0, float(self.declare_parameter('drop_probability', 0.0).value)),
        )
        self.delay_mean_ms = max(
            0.0,
            float(self.declare_parameter('delay_mean_ms', 0.0).value),
        )
        self.delay_jitter_ms = max(
            0.0,
            float(self.declare_parameter('delay_jitter_ms', 0.0).value),
        )
        self.max_queue_size = max(
            1,
            int(self.declare_parameter('max_queue_size', 100).value),
        )
        seed = int(self.declare_parameter('random_seed', 7).value)
        self._random = random.Random(seed)
        self._pending_messages: List[Tuple[float, int, str]] = []
        self._message_counter = 0

        self.publisher = self.create_publisher(String, self.output_topic, 10)
        self.create_subscription(String, self.input_topic, self._input_callback, 10)
        self.create_timer(0.02, self._flush_pending)
        self.get_logger().info(
            (
                f'Network fault injector relaying {self.input_topic} -> '
                f'{self.output_topic} with drop={self.drop_probability:.2f}, '
                f'delay={self.delay_mean_ms:.1f}ms +/- {self.delay_jitter_ms:.1f}ms'
            )
        )

    def _input_callback(self, msg: String) -> None:
        """Store or drop incoming messages according to the configured fault model."""
        if self._random.random() < self.drop_probability:
            return

        delay_ms = self.delay_mean_ms
        if self.delay_jitter_ms > 0.0:
            delay_ms += self._random.uniform(-self.delay_jitter_ms, self.delay_jitter_ms)
        delay_ms = max(0.0, delay_ms)

        release_time = time.monotonic() + (delay_ms / 1000.0)
        self._message_counter += 1
        self._pending_messages.append((release_time, self._message_counter, msg.data))
        if len(self._pending_messages) > self.max_queue_size:
            self._pending_messages.pop(0)
        self._flush_pending()

    def _flush_pending(self) -> None:
        """Publish all messages whose artificial delay has elapsed."""
        if not self._pending_messages:
            return

        now = time.monotonic()
        ready = [
            item for item in self._pending_messages
            if item[0] <= now
        ]
        if not ready:
            return

        self._pending_messages = [
            item for item in self._pending_messages
            if item[0] > now
        ]
        ready.sort(key=lambda item: (item[0], item[1]))
        for _, _, payload in ready:
            msg = String()
            msg.data = payload
            self.publisher.publish(msg)


def main(args=None) -> None:
    """Run the network fault injection relay."""
    rclpy.init(args=args)
    node = NetworkFaultInjector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
