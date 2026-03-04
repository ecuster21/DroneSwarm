"""Shared experiment profiles and metadata helpers."""

from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
from typing import Dict
from typing import Optional


EXPERIMENT_PROFILES = {
    'baseline': {
        'uav_count': 4,
        'update_period_sec': 0.2,
        'use_fault_injection': False,
        'drop_probability': 0.0,
        'delay_mean_ms': 0.0,
        'delay_jitter_ms': 0.0,
        'alpha_switch': 0.75,
        'beta_stale': 1.0,
        'lambda_cost': 1.0,
    },
    'delay': {
        'uav_count': 4,
        'update_period_sec': 0.2,
        'use_fault_injection': True,
        'drop_probability': 0.0,
        'delay_mean_ms': 200.0,
        'delay_jitter_ms': 50.0,
        'alpha_switch': 0.75,
        'beta_stale': 1.0,
        'lambda_cost': 1.0,
    },
    'loss': {
        'uav_count': 4,
        'update_period_sec': 0.2,
        'use_fault_injection': True,
        'drop_probability': 0.2,
        'delay_mean_ms': 0.0,
        'delay_jitter_ms': 0.0,
        'alpha_switch': 0.75,
        'beta_stale': 1.0,
        'lambda_cost': 1.0,
    },
    'stress': {
        'uav_count': 4,
        'update_period_sec': 0.2,
        'use_fault_injection': True,
        'drop_probability': 0.2,
        'delay_mean_ms': 200.0,
        'delay_jitter_ms': 50.0,
        'alpha_switch': 0.75,
        'beta_stale': 1.0,
        'lambda_cost': 1.0,
    },
}


def typed_parameters_for_profile(profile_name: str) -> Dict:
    """Return a typed parameter map for the requested profile."""
    if profile_name not in EXPERIMENT_PROFILES:
        raise KeyError(f'Unknown experiment profile: {profile_name}')
    return dict(EXPERIMENT_PROFILES[profile_name])


def launch_arguments_for_profile(profile_name: str) -> Dict[str, str]:
    """Return launch-compatible string parameters for the requested profile."""
    typed_parameters = typed_parameters_for_profile(profile_name)
    launch_arguments = {}
    for key, value in typed_parameters.items():
        if isinstance(value, bool):
            launch_arguments[key] = 'true' if value else 'false'
        else:
            launch_arguments[key] = str(value)
    return launch_arguments


def build_experiment_record(
    profile_name: str,
    parameters: Optional[Dict] = None,
    run_label: str = '',
    timestamp: Optional[str] = None,
) -> Dict:
    """Build a JSON-serializable experiment record."""
    typed_parameters = typed_parameters_for_profile(profile_name)
    if parameters:
        typed_parameters.update(parameters)

    return {
        'profile_name': profile_name,
        'recorded_at_utc': (
            timestamp
            or datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        ),
        'run_label': run_label,
        'parameters': typed_parameters,
    }


def write_experiment_record(
    profile_name: str,
    output_dir: str,
    parameters: Optional[Dict] = None,
    run_label: str = '',
    timestamp: Optional[str] = None,
) -> Path:
    """Write experiment metadata to disk and return the output path."""
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)

    record = build_experiment_record(
        profile_name=profile_name,
        parameters=parameters,
        run_label=run_label,
        timestamp=timestamp,
    )
    suffix = f'_{run_label}' if run_label else ''
    timestamp_token = record['recorded_at_utc'].replace(':', '-').replace('.', '-')
    filename = f"{profile_name}{suffix}_{timestamp_token}.json"
    file_path = output_path / filename
    file_path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    return file_path
