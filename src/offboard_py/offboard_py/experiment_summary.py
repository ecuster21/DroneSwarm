"""Post-process experiment manifests and metric traces into table-ready summaries."""

import argparse
import csv
from datetime import datetime
from pathlib import Path
import json
from typing import Dict
from typing import Iterable
from typing import Optional


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO timestamp and return `None` on invalid input."""
    if not value:
        return None
    normalized = value.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _safe_json_loads(payload: str):
    """Best-effort JSON parsing helper used for event payloads."""
    try:
        return json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def find_latest_manifest(results_dir: str) -> Path:
    """Find the latest experiment manifest in a result directory."""
    root = Path(results_dir).expanduser()
    manifest_paths = []
    for candidate in root.glob('*.json'):
        if candidate.name.endswith('_summary.json'):
            continue
        manifest_paths.append(candidate)

    if not manifest_paths:
        raise FileNotFoundError(f'No experiment manifest found in {root}')
    return max(manifest_paths, key=lambda item: item.stat().st_mtime)


def load_manifest(manifest_path: str) -> Dict:
    """Load one experiment manifest JSON file."""
    path = Path(manifest_path).expanduser()
    return json.loads(path.read_text())


def iter_metric_events(metric_files: Iterable[Path]) -> Iterable[Dict]:
    """Yield parsed metric events from JSONL files."""
    for file_path in metric_files:
        with file_path.open(encoding='utf-8') as stream:
            for line in stream:
                stripped = line.strip()
                if not stripped:
                    continue
                event = _safe_json_loads(stripped)
                if isinstance(event, dict):
                    yield event


def summarize_results(results_dir: str, manifest_path: Optional[str] = None) -> Dict:
    """Summarize one experiment result directory into aggregate metrics."""
    root = Path(results_dir).expanduser()
    manifest_file = (
        Path(manifest_path).expanduser()
        if manifest_path is not None
        else find_latest_manifest(results_dir)
    )
    manifest = load_manifest(str(manifest_file))
    metric_files = sorted(root.rglob('*.jsonl'))

    by_topic = {}
    per_namespace_events = {}
    per_namespace_switches = {}
    last_winner_by_namespace = {}
    first_event_time = None
    last_event_time = None
    latest_switch_time = None
    total_events = 0

    for event in iter_metric_events(metric_files):
        total_events += 1
        topic = str(event.get('source_topic', 'unknown'))
        namespace = str(event.get('namespace', 'global'))
        by_topic[topic] = by_topic.get(topic, 0) + 1
        per_namespace_events[namespace] = per_namespace_events.get(namespace, 0) + 1

        event_time = _parse_timestamp(event.get('recorded_at_utc'))
        if event_time is not None:
            if first_event_time is None or event_time < first_event_time:
                first_event_time = event_time
            if last_event_time is None or event_time > last_event_time:
                last_event_time = event_time

        if topic.endswith('auction/allocation'):
            payload = _safe_json_loads(event.get('payload', ''))
            winner_task_id = None
            if isinstance(payload, dict):
                winner_task_id = payload.get('winner_task_id')

            previous_winner = last_winner_by_namespace.get(namespace)
            if previous_winner != winner_task_id:
                if previous_winner is not None:
                    per_namespace_switches[namespace] = (
                        per_namespace_switches.get(namespace, 0) + 1
                    )
                last_winner_by_namespace[namespace] = winner_task_id
                if event_time is not None:
                    latest_switch_time = event_time

    runtime_sec = 0.0
    stabilization_sec = 0.0
    if first_event_time is not None and last_event_time is not None:
        runtime_sec = max(
            0.0,
            (last_event_time - first_event_time).total_seconds(),
        )
    if first_event_time is not None and latest_switch_time is not None:
        stabilization_sec = max(
            0.0,
            (latest_switch_time - first_event_time).total_seconds(),
        )

    summary = {
        'profile_name': manifest.get('profile_name', 'unknown'),
        'manifest_path': str(manifest_file),
        'metric_files': [str(file_path) for file_path in metric_files],
        'metric_file_count': len(metric_files),
        'parameters': manifest.get('parameters', {}),
        'run_label': manifest.get('run_label', ''),
        'recorded_at_utc': manifest.get('recorded_at_utc'),
        'total_events': total_events,
        'topic_counts': dict(sorted(by_topic.items())),
        'per_namespace_events': dict(sorted(per_namespace_events.items())),
        'per_namespace_switches': dict(sorted(per_namespace_switches.items())),
        'total_task_switches': sum(per_namespace_switches.values()),
        'namespace_count': len(per_namespace_events),
        'runtime_sec': runtime_sec,
        'stabilization_sec': stabilization_sec,
        'first_event_utc': (
            first_event_time.isoformat().replace('+00:00', 'Z')
            if first_event_time is not None else None
        ),
        'last_event_utc': (
            last_event_time.isoformat().replace('+00:00', 'Z')
            if last_event_time is not None else None
        ),
    }
    return summary


def summary_row(summary: Dict) -> Dict:
    """Reduce a full summary into a single CSV-friendly row."""
    parameters = summary.get('parameters', {})
    topic_counts = summary.get('topic_counts', {})
    return {
        'profile_name': summary.get('profile_name', 'unknown'),
        'run_label': summary.get('run_label', ''),
        'uav_count': parameters.get('uav_count', ''),
        'use_fault_injection': parameters.get('use_fault_injection', ''),
        'drop_probability': parameters.get('drop_probability', ''),
        'delay_mean_ms': parameters.get('delay_mean_ms', ''),
        'delay_jitter_ms': parameters.get('delay_jitter_ms', ''),
        'total_events': summary.get('total_events', 0),
        'allocation_events': topic_counts.get('auction/allocation', 0),
        'bid_events': topic_counts.get('auction/bid', 0),
        'local_state_events': topic_counts.get('auction/local_state', 0),
        'namespace_count': summary.get('namespace_count', 0),
        'total_task_switches': summary.get('total_task_switches', 0),
        'runtime_sec': summary.get('runtime_sec', 0.0),
        'stabilization_sec': summary.get('stabilization_sec', 0.0),
    }


def write_summary_outputs(
    results_dir: str,
    summary: Dict,
    manifest_path: Optional[str] = None,
) -> Dict[str, str]:
    """Write both JSON and CSV summaries next to the experiment manifest."""
    root = Path(results_dir).expanduser()
    manifest_file = (
        Path(manifest_path).expanduser()
        if manifest_path is not None
        else Path(summary['manifest_path'])
    )
    stem = manifest_file.stem
    json_path = root / f'{stem}_summary.json'
    csv_path = root / f'{stem}_summary.csv'

    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    row = summary_row(summary)
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)

    return {
        'json_path': str(json_path),
        'csv_path': str(csv_path),
    }


def main(argv=None) -> int:
    """CLI entry point for summarizing one experiment result directory."""
    parser = argparse.ArgumentParser(
        description='Summarize one experiment result directory.',
    )
    parser.add_argument(
        'results_dir',
        help='Directory containing the experiment manifest and per-UAV JSONL traces.',
    )
    parser.add_argument(
        '--manifest',
        dest='manifest_path',
        default=None,
        help='Optional explicit manifest path. Defaults to the latest manifest in results_dir.',
    )
    args = parser.parse_args(argv)

    summary = summarize_results(
        results_dir=args.results_dir,
        manifest_path=args.manifest_path,
    )
    outputs = write_summary_outputs(
        results_dir=args.results_dir,
        summary=summary,
        manifest_path=args.manifest_path,
    )
    print(json.dumps({
        'summary': summary_row(summary),
        'outputs': outputs,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
