"""Tests for repeated-batch experiment aggregation."""

import csv
import json

from offboard_py.experiment_study import aggregate_study_rows
from offboard_py.experiment_study import collect_study_rows
from offboard_py.experiment_study import write_study_outputs


def _write_batch_csv(root, batch_name, rows):
    """Create a minimal batch directory with comparison.csv."""
    batch_dir = root / batch_name
    batch_dir.mkdir()
    csv_path = batch_dir / 'comparison.csv'
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return batch_dir


def test_aggregate_study_rows_computes_mean_and_std():
    """Aggregate rows should compute per-profile means and standard deviations."""
    rows = [
        {'profile_name': 'baseline', 'total_events': '100', 'stabilization_sec': '1.0'},
        {'profile_name': 'baseline', 'total_events': '110', 'stabilization_sec': '1.2'},
        {'profile_name': 'delay', 'total_events': '90', 'stabilization_sec': '2.0'},
        {'profile_name': 'delay', 'total_events': '80', 'stabilization_sec': '2.4'},
    ]
    aggregated = aggregate_study_rows(rows)
    baseline = next(row for row in aggregated if row['profile_name'] == 'baseline')
    delay = next(row for row in aggregated if row['profile_name'] == 'delay')

    assert baseline['trials'] == 2
    assert baseline['total_events_mean'] == 105
    assert round(baseline['total_events_std'], 6) == round(7.0710678118654755, 6)
    assert delay['stabilization_sec_mean'] == 2.2
    assert round(delay['stabilization_sec_std'], 6) == round(0.2828427124746193, 6)


def test_write_study_outputs_scans_batch_directories(tmp_path):
    """Study outputs should scan batch_* directories and write aggregate files."""
    common_fields = {
        'uav_count': '4',
        'drop_probability': '0.0',
        'delay_mean_ms': '0.0',
        'delay_jitter_ms': '0.0',
        'allocation_events': '10',
        'bid_events': '10',
        'local_state_events': '10',
        'total_task_switches': '0',
        'runtime_sec': '60.0',
    }
    _write_batch_csv(tmp_path, 'batch_1', [
        {
            'profile_name': 'baseline',
            'total_events': '100',
            'stabilization_sec': '1.0',
            **common_fields,
        },
        {
            'profile_name': 'delay',
            'total_events': '80',
            'stabilization_sec': '2.0',
            **common_fields,
        },
    ])
    _write_batch_csv(tmp_path, 'batch_2', [
        {
            'profile_name': 'baseline',
            'total_events': '120',
            'stabilization_sec': '1.4',
            **common_fields,
        },
        {
            'profile_name': 'delay',
            'total_events': '70',
            'stabilization_sec': '2.4',
            **common_fields,
        },
    ])

    rows = collect_study_rows(str(tmp_path))
    assert len(rows) == 4

    outputs = write_study_outputs(str(tmp_path))
    csv_path = tmp_path / 'study_comparison.csv'
    json_path = tmp_path / 'study_comparison.json'
    html_path = tmp_path / 'study_comparison_report.html'

    assert outputs['csv_path'] == str(csv_path)
    assert outputs['json_path'] == str(json_path)
    assert outputs['html_path'] == str(html_path)

    csv_text = csv_path.read_text(encoding='utf-8')
    assert 'baseline' in csv_text
    assert 'delay' in csv_text

    payload = json.loads(json_path.read_text(encoding='utf-8'))
    assert len(payload['source_batches']) == 2
    assert len(payload['profiles']) == 2

    html_text = html_path.read_text(encoding='utf-8')
    assert 'Repeated Experiment Study Report' in html_text
    assert 'Mean Stabilization Time (s)' in html_text


def test_collect_study_rows_skips_zero_signal_batches(tmp_path):
    """Batches with only zero-valued summaries should be ignored."""
    zero_fields = {
        'uav_count': '4',
        'drop_probability': '0.0',
        'delay_mean_ms': '0.0',
        'delay_jitter_ms': '0.0',
        'total_events': '0',
        'allocation_events': '0',
        'bid_events': '0',
        'local_state_events': '0',
        'total_task_switches': '0',
        'runtime_sec': '0.0',
        'stabilization_sec': '0.0',
    }
    _write_batch_csv(tmp_path, 'batch_0', [
        {'profile_name': 'baseline', **zero_fields},
    ])
    _write_batch_csv(tmp_path, 'batch_1', [
        {
            'profile_name': 'baseline',
            **{
                **zero_fields,
                'total_events': '10',
                'allocation_events': '3',
            },
        },
    ])

    rows = collect_study_rows(str(tmp_path))
    assert len(rows) == 1
    assert rows[0]['batch_root'].endswith('batch_1')
