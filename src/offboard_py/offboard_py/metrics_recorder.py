#!/usr/bin/env python3

"""ROS 2 node that records auction topics as JSONL events."""

from functools import partial

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from offboard_py.metrics_store import MetricsLogWriter


class MetricsRecorder(Node):
    """Persist selected string topics for later plotting and analysis."""

    def __init__(self) -> None:
        """Initialize subscriptions and create the JSONL writer."""
        super().__init__('metrics_recorder')
        self.profile_name = str(
            self.declare_parameter('profile_name', 'ad_hoc').value
        )
        self.output_dir = str(
            self.declare_parameter('output_dir', 'experiment_results/ad_hoc').value
        )
        self.session_label = str(
            self.declare_parameter('session_label', '').value
        )
        source_topics = self.declare_parameter(
            'source_topics',
            ['auction/allocation', 'auction/bid', 'auction/local_state'],
        ).value
        self.source_topics = [str(topic) for topic in source_topics]
        namespace = self.get_namespace().strip('/')
        self.writer = MetricsLogWriter(
            output_dir=self.output_dir,
            profile_name=self.profile_name,
            namespace=namespace,
            session_label=self.session_label,
        )

        for topic in self.source_topics:
            self.create_subscription(
                String,
                topic,
                partial(self._record_message, topic),
                10,
            )

        self.get_logger().info(
            (
                f'Recording topics {self.source_topics} to '
                f'{self.writer.file_path.resolve()}'
            )
        )

    def _record_message(self, topic: str, msg: String) -> None:
        """Append one topic event to the recorder file."""
        try:
            self.writer.append(source_topic=topic, payload=msg.data)
        except OSError as exc:
            self.get_logger().error(f'Failed to write metric event: {exc}')


def main(args=None) -> None:
    """Run the runtime metrics recorder."""
    rclpy.init(args=args)
    node = MetricsRecorder()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
