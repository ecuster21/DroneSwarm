import json

from offboard_py.experiment_summary import find_latest_manifest
from offboard_py.experiment_summary import summarize_results
from offboard_py.experiment_summary import summary_row
from offboard_py.experiment_summary import write_summary_outputs


def test_summarize_results_aggregates_events_and_switches(tmp_path):
    manifest = {
        'profile_name': 'baseline',
        'recorded_at_utc': '2026-03-04T00:00:00Z',
        'run_label': 'trial_1',
        'parameters': {
            'uav_count': 2,
            'use_fault_injection': False,
            'drop_probability': 0.0,
            'delay_mean_ms': 0.0,
            'delay_jitter_ms': 0.0,
        },
    }
    manifest_path = tmp_path / 'baseline_manifest.json'
    manifest_path.write_text(json.dumps(manifest) + '\n')

    uav1_dir = tmp_path / 'uav1'
    uav1_dir.mkdir()
    uav1_metrics = uav1_dir / 'uav1_metrics.jsonl'
    uav1_metrics.write_text(
        '\n'.join([
            json.dumps({
                'recorded_at_utc': '2026-03-04T00:00:01Z',
                'profile_name': 'baseline',
                'namespace': 'uav1',
                'source_topic': 'auction/allocation',
                'payload': json.dumps({'winner_task_id': 'task_1'}),
            }),
            json.dumps({
                'recorded_at_utc': '2026-03-04T00:00:02Z',
                'profile_name': 'baseline',
                'namespace': 'uav1',
                'source_topic': 'auction/allocation',
                'payload': json.dumps({'winner_task_id': 'task_2'}),
            }),
            json.dumps({
                'recorded_at_utc': '2026-03-04T00:00:03Z',
                'profile_name': 'baseline',
                'namespace': 'uav1',
                'source_topic': 'auction/bid',
                'payload': '{}',
            }),
        ]) + '\n'
    )

    uav2_dir = tmp_path / 'uav2'
    uav2_dir.mkdir()
    uav2_metrics = uav2_dir / 'uav2_metrics.jsonl'
    uav2_metrics.write_text(
        json.dumps({
            'recorded_at_utc': '2026-03-04T00:00:04Z',
            'profile_name': 'baseline',
            'namespace': 'uav2',
            'source_topic': 'auction/local_state',
            'payload': '{}',
        }) + '\n'
    )

    summary = summarize_results(str(tmp_path))
    row = summary_row(summary)

    assert summary['profile_name'] == 'baseline'
    assert summary['metric_file_count'] == 2
    assert summary['total_events'] == 4
    assert summary['topic_counts']['auction/allocation'] == 2
    assert summary['topic_counts']['auction/bid'] == 1
    assert summary['topic_counts']['auction/local_state'] == 1
    assert summary['per_namespace_switches']['uav1'] == 1
    assert summary['total_task_switches'] == 1
    assert summary['namespace_count'] == 2
    assert summary['runtime_sec'] == 3.0
    assert summary['stabilization_sec'] == 1.0
    assert row['allocation_events'] == 2
    assert row['total_task_switches'] == 1


def test_write_summary_outputs_creates_json_and_csv(tmp_path):
    manifest_path = tmp_path / 'baseline_manifest.json'
    manifest_path.write_text(json.dumps({
        'profile_name': 'baseline',
        'recorded_at_utc': '2026-03-04T00:00:00Z',
        'run_label': '',
        'parameters': {},
    }) + '\n')
    summary = {
        'profile_name': 'baseline',
        'manifest_path': str(manifest_path),
        'metric_files': [],
        'metric_file_count': 0,
        'parameters': {},
        'run_label': '',
        'recorded_at_utc': '2026-03-04T00:00:00Z',
        'total_events': 0,
        'topic_counts': {},
        'per_namespace_events': {},
        'per_namespace_switches': {},
        'total_task_switches': 0,
        'namespace_count': 0,
        'runtime_sec': 0.0,
        'stabilization_sec': 0.0,
        'first_event_utc': None,
        'last_event_utc': None,
    }

    outputs = write_summary_outputs(str(tmp_path), summary)

    assert outputs['json_path'].endswith('baseline_manifest_summary.json')
    assert outputs['csv_path'].endswith('baseline_manifest_summary.csv')
    assert 'profile_name' in (tmp_path / 'baseline_manifest_summary.csv').read_text()


def test_find_latest_manifest_ignores_summary_json(tmp_path):
    older = tmp_path / 'older.json'
    older.write_text('{}\n')
    summary = tmp_path / 'older_summary.json'
    summary.write_text('{}\n')
    newer = tmp_path / 'newer.json'
    newer.write_text('{}\n')

    assert find_latest_manifest(str(tmp_path)).name == 'newer.json'
