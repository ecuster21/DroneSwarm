import ast
from pathlib import Path

from offboard_py.experiment_profiles import EXPERIMENT_PROFILES
from offboard_py.experiment_profiles import build_experiment_record
from offboard_py.experiment_profiles import write_experiment_record


def _parse_launch_module(filename):
    launch_path = Path(__file__).resolve().parents[1] / 'launch' / filename
    return ast.parse(launch_path.read_text())


def test_experiment_profiles_match_expected_values():
    assert EXPERIMENT_PROFILES['baseline']['use_fault_injection'] is False
    assert EXPERIMENT_PROFILES['baseline']['uav_count'] == 4

    assert EXPERIMENT_PROFILES['delay']['use_fault_injection'] is True
    assert EXPERIMENT_PROFILES['delay']['delay_mean_ms'] == 200.0
    assert EXPERIMENT_PROFILES['delay']['delay_jitter_ms'] == 50.0

    assert EXPERIMENT_PROFILES['loss']['use_fault_injection'] is True
    assert EXPERIMENT_PROFILES['loss']['drop_probability'] == 0.2

    assert EXPERIMENT_PROFILES['stress']['use_fault_injection'] is True
    assert EXPERIMENT_PROFILES['stress']['drop_probability'] == 0.2
    assert EXPERIMENT_PROFILES['stress']['delay_mean_ms'] == 200.0
    assert EXPERIMENT_PROFILES['stress']['delay_jitter_ms'] == 50.0


def test_build_experiment_record_contains_profile_metadata():
    record = build_experiment_record('delay', run_label='trial_a')

    assert record['profile_name'] == 'delay'
    assert record['run_label'] == 'trial_a'
    assert record['parameters']['delay_mean_ms'] == 200.0


def test_write_experiment_record_persists_json(tmp_path):
    output_path = write_experiment_record(
        profile_name='loss',
        output_dir=str(tmp_path),
        run_label='trial_b',
        timestamp='2026-03-04T00:00:00Z',
    )

    content = output_path.read_text()

    assert output_path.name.startswith('loss_trial_b_2026-03-04T00-00-00Z')
    assert '"profile_name": "loss"' in content
    assert '"drop_probability": 0.2' in content


def test_experiment_launch_files_expose_profile_names():
    launch_files = {
        'auction_baseline_experiment.launch.py': 'baseline',
        'auction_delay_experiment.launch.py': 'delay',
        'auction_loss_experiment.launch.py': 'loss',
        'auction_stress_experiment.launch.py': 'stress',
    }

    for filename, profile_name in launch_files.items():
        tree = _parse_launch_module(filename)
        profile_name_value = None
        has_generate_function = False

        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == 'PROFILE_NAME'
                and isinstance(node.value, ast.Constant)
            ):
                profile_name_value = node.value.value
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == 'generate_launch_description'
            ):
                has_generate_function = True

        assert profile_name_value == profile_name
        assert has_generate_function is True
