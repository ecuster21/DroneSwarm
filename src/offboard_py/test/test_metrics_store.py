from offboard_py.metrics_store import MetricsLogWriter


def test_metrics_log_writer_appends_jsonl_events(tmp_path):
    writer = MetricsLogWriter(
        output_dir=str(tmp_path),
        profile_name='baseline',
        namespace='uav1',
        session_label='trial_1',
        timestamp='2026-03-04T00:00:00Z',
    )

    event = writer.append(
        source_topic='auction/allocation',
        payload='{"winner":"task_1"}',
        timestamp='2026-03-04T00:00:01Z',
    )
    content = writer.file_path.read_text()

    assert writer.file_path.name.startswith(
        'baseline_uav1_trial_1_2026-03-04T00-00-00Z'
    )
    assert event['namespace'] == 'uav1'
    assert event['source_topic'] == 'auction/allocation'
    assert '"profile_name": "baseline"' in content
    assert '"payload": "{\\"winner\\":\\"task_1\\"}"' in content
