import json
from pathlib import Path

from offboard_py.experiment_report import collect_profile_rows
from offboard_py.experiment_report import write_comparison_outputs


def _write_summary(root: Path, profile_name: str, total_events: int, switches: int) -> None:
    profile_dir = root / profile_name
    profile_dir.mkdir(parents=True, exist_ok=True)
    summary_path = profile_dir / f'{profile_name}_summary.json'
    summary_path.write_text(json.dumps({
        'profile_name': profile_name,
        'parameters': {
            'uav_count': 4,
            'drop_probability': 0.0,
            'delay_mean_ms': 0.0,
            'delay_jitter_ms': 0.0,
        },
        'topic_counts': {
            'auction/allocation': total_events // 2,
            'auction/bid': total_events // 3,
            'auction/local_state': total_events // 4,
        },
        'total_events': total_events,
        'total_task_switches': switches,
        'runtime_sec': 60.0,
        'stabilization_sec': 20.0,
    }) + '\n')


def test_collect_profile_rows_and_write_outputs(tmp_path):
    for index, profile_name in enumerate(['baseline', 'delay', 'loss', 'stress'], start=1):
        _write_summary(tmp_path, profile_name, total_events=10 * index, switches=index)

    rows = collect_profile_rows(str(tmp_path))
    outputs = write_comparison_outputs(str(tmp_path))

    assert len(rows) == 4
    assert rows[0]['profile_name'] == 'baseline'
    assert Path(outputs['csv_path']).exists()
    assert Path(outputs['html_path']).exists()
    assert 'comparison.csv' in outputs['csv_path']
