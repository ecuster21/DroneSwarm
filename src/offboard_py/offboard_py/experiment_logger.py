#!/usr/bin/env python3

"""ROS 2 node that writes a metadata record for each experiment launch."""

from pathlib import Path

import rclpy
from rclpy.node import Node

from offboard_py.experiment_profiles import write_experiment_record


class ExperimentLogger(Node):
    """Persist the active experiment conditions to a JSON manifest."""

    def __init__(self) -> None:
        """Read parameters, write metadata once, then stay alive."""
        super().__init__('experiment_logger')
        self.profile_name = str(
            self.declare_parameter('profile_name', 'baseline').value
        )
        self.output_dir = str(
            self.declare_parameter('output_dir', 'experiment_results').value
        )
        self.run_label = str(
            self.declare_parameter('run_label', '').value
        )
        self._record_written = False
        self._write_record()

    def _write_record(self) -> None:
        """Write the experiment metadata to disk if it has not been written yet."""
        if self._record_written:
            return

        parameters = {
            'uav_count': int(self.declare_parameter('uav_count', 4).value),
            'update_period_sec': float(
                self.declare_parameter('update_period_sec', 0.2).value
            ),
            'use_fault_injection': bool(
                self.declare_parameter('use_fault_injection', False).value
            ),
            'drop_probability': float(
                self.declare_parameter('drop_probability', 0.0).value
            ),
            'delay_mean_ms': float(
                self.declare_parameter('delay_mean_ms', 0.0).value
            ),
            'delay_jitter_ms': float(
                self.declare_parameter('delay_jitter_ms', 0.0).value
            ),
            'alpha_switch': float(
                self.declare_parameter('alpha_switch', 0.75).value
            ),
            'beta_stale': float(
                self.declare_parameter('beta_stale', 1.0).value
            ),
            'lambda_cost': float(
                self.declare_parameter('lambda_cost', 1.0).value
            ),
        }

        try:
            file_path = write_experiment_record(
                profile_name=self.profile_name,
                output_dir=self.output_dir,
                parameters=parameters,
                run_label=self.run_label,
            )
        except OSError as exc:
            self.get_logger().error(f'Failed to write experiment record: {exc}')
            return

        self._record_written = True
        self.get_logger().info(
            f'Wrote experiment record to {Path(file_path).resolve()}'
        )


def main(args=None) -> None:
    """Run the experiment metadata logger."""
    rclpy.init(args=args)
    node = ExperimentLogger()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
