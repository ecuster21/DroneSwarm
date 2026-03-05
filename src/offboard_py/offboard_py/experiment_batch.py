"""Run a batch of experiment profiles sequentially and build comparison outputs."""

import argparse
from datetime import datetime
from datetime import timezone
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Dict
from typing import Iterable
from typing import List

from offboard_py.experiment_profiles import typed_parameters_for_profile
from offboard_py.experiment_report import DEFAULT_PROFILES
from offboard_py.experiment_profiles import write_experiment_record
from offboard_py.experiment_report import write_comparison_outputs
from offboard_py.experiment_summary import summarize_results
from offboard_py.experiment_summary import write_summary_outputs


def _run_label() -> str:
    """Create a stable batch run label."""
    return datetime.now(timezone.utc).strftime('batch_%Y%m%dT%H%M%SZ')


def _launch_arguments(
    profile_name: str,
    results_dir: Path,
    uav_count: int,
    namespace_prefix: str,
) -> List[str]:
    """Build ROS 2 launch arguments for one profile."""
    params = typed_parameters_for_profile(profile_name)
    params['uav_count'] = uav_count
    return [
        f'uav_count:={uav_count}',
        f'namespace_prefix:={namespace_prefix}',
        f'experiment_profile:={profile_name}',
        'enable_metrics:=true',
        f'metrics_output_dir:={results_dir}',
        f'use_fault_injection:={"true" if params["use_fault_injection"] else "false"}',
        f'drop_probability:={params["drop_probability"]}',
        f'delay_mean_ms:={params["delay_mean_ms"]}',
        f'delay_jitter_ms:={params["delay_jitter_ms"]}',
        f'alpha_switch:={params["alpha_switch"]}',
        f'beta_stale:={params["beta_stale"]}',
        f'lambda_cost:={params["lambda_cost"]}',
        f'update_period_sec:={params["update_period_sec"]}',
    ]


def run_profile(
    profile_name: str,
    batch_root: Path,
    duration_sec: float,
    uav_count: int,
    namespace_prefix: str,
) -> Dict:
    """Run one profile for a fixed duration, then summarize its outputs."""
    results_dir = batch_root / profile_name
    results_dir.mkdir(parents=True, exist_ok=True)
    params = typed_parameters_for_profile(profile_name)
    params['uav_count'] = uav_count

    write_experiment_record(
        profile_name=profile_name,
        output_dir=str(results_dir),
        parameters=params,
        run_label='',
    )

    command = [
        'ros2',
        'launch',
        'offboard_py',
        'auction_sitl.launch.py',
        *_launch_arguments(
            profile_name=profile_name,
            results_dir=results_dir,
            uav_count=uav_count,
            namespace_prefix=namespace_prefix,
        ),
    ]
    env = dict(os.environ)
    ros_log_dir = results_dir / 'ros_logs'
    ros_log_dir.mkdir(parents=True, exist_ok=True)
    env['ROS_LOG_DIR'] = str(ros_log_dir)

    process = subprocess.Popen(command, env=env)
    try:
        time.sleep(duration_sec)
    finally:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15.0)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10.0)

    summary = summarize_results(str(results_dir))
    write_summary_outputs(str(results_dir), summary)
    return summary


def run_batch(
    results_root: str,
    profiles: Iterable[str] = DEFAULT_PROFILES,
    duration_sec: float = 60.0,
    uav_count: int = 4,
    namespace_prefix: str = 'px4_',
) -> Dict[str, str]:
    """Run all requested profiles and build a combined comparison report."""
    batch_root = Path(results_root).expanduser() / _run_label()
    batch_root.mkdir(parents=True, exist_ok=True)

    for profile_name in profiles:
        run_profile(
            profile_name=profile_name,
            batch_root=batch_root,
            duration_sec=duration_sec,
            uav_count=uav_count,
            namespace_prefix=namespace_prefix,
        )

    outputs = write_comparison_outputs(
        results_dir=str(batch_root),
        profiles=profiles,
    )
    outputs['batch_root'] = str(batch_root)
    return outputs


def main(argv=None) -> int:
    """CLI entry point for running a full experiment batch."""
    parser = argparse.ArgumentParser(
        description='Run baseline/delay/loss/stress sequentially and build a report.',
    )
    parser.add_argument(
        '--results-root',
        default='experiment_results',
        help='Directory under which a new batch run directory will be created.',
    )
    parser.add_argument(
        '--profiles',
        nargs='*',
        default=DEFAULT_PROFILES,
        help='Profiles to run in sequence.',
    )
    parser.add_argument(
        '--duration-sec',
        type=float,
        default=60.0,
        help='Duration for each profile run.',
    )
    parser.add_argument(
        '--uav-count',
        type=int,
        default=4,
        help='Number of PX4 namespaces to target (for example 4 for px4_1..px4_4).',
    )
    parser.add_argument(
        '--namespace-prefix',
        default='px4_',
        help='Namespace prefix used by the PX4 DDS bridge.',
    )
    args = parser.parse_args(argv)

    outputs = run_batch(
        results_root=args.results_root,
        profiles=args.profiles,
        duration_sec=args.duration_sec,
        uav_count=args.uav_count,
        namespace_prefix=args.namespace_prefix,
    )
    print(outputs)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
