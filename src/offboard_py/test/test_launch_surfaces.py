import ast
from pathlib import Path


def _parse_launch_file(filename):
    launch_path = Path(__file__).resolve().parents[1] / 'launch' / filename
    return ast.parse(launch_path.read_text())


def test_auction_sitl_launch_arguments_match_expected_surface():
    tree = _parse_launch_file('auction_sitl.launch.py')
    declared_arguments = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'DeclareLaunchArgument'
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            declared_arguments.append(node.args[0].value)

    assert declared_arguments == [
        'uav_count',
        'namespace_prefix',
        'update_period_sec',
        'use_fault_injection',
        'drop_probability',
        'delay_mean_ms',
        'delay_jitter_ms',
        'alpha_switch',
        'beta_stale',
        'lambda_cost',
        'enable_metrics',
        'metrics_output_dir',
        'experiment_profile',
    ]


def test_auction_sitl_launch_uses_metrics_recorder_node():
    tree = _parse_launch_file('auction_sitl.launch.py')
    metrics_recorder_seen = False

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'Node'
        ):
            for keyword in node.keywords:
                if (
                    keyword.arg == 'executable'
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value == 'metrics_recorder'
                ):
                    metrics_recorder_seen = True

    assert metrics_recorder_seen is True
