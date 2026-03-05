"""Aggregate repeated batch runs into paper-friendly mean/std comparison outputs."""

import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from statistics import stdev
from typing import Dict
from typing import Iterable
from typing import List


NUMERIC_FIELDS = [
    'uav_count',
    'drop_probability',
    'delay_mean_ms',
    'delay_jitter_ms',
    'total_events',
    'allocation_events',
    'bid_events',
    'local_state_events',
    'total_task_switches',
    'runtime_sec',
    'stabilization_sec',
]


def _to_float(value) -> float:
    """Convert CSV cell values into floats safely."""
    if value in (None, ''):
        return 0.0
    return float(value)


def _batch_directories(results_root: str) -> List[Path]:
    """Return batch directories that contain a comparison.csv file."""
    root = Path(results_root).expanduser()
    return sorted(
        path for path in root.glob('batch_*')
        if (path / 'comparison.csv').is_file()
    )


def load_batch_rows(batch_root: str) -> List[Dict]:
    """Load one batch comparison table."""
    batch_path = Path(batch_root).expanduser()
    csv_path = batch_path / 'comparison.csv'
    with csv_path.open('r', newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row['batch_root'] = str(batch_path)
    return rows


def _batch_has_signal(rows: List[Dict]) -> bool:
    """Return True when a batch contains non-zero runtime activity."""
    for row in rows:
        if _to_float(row.get('total_events', 0.0)) > 0.0:
            return True
        if _to_float(row.get('allocation_events', 0.0)) > 0.0:
            return True
        if _to_float(row.get('bid_events', 0.0)) > 0.0:
            return True
        if _to_float(row.get('local_state_events', 0.0)) > 0.0:
            return True
    return False


def collect_study_rows(
    results_root: str,
    batch_dirs: Iterable[str] = (),
) -> List[Dict]:
    """Collect comparison rows from all requested batch directories."""
    if batch_dirs:
        resolved = [Path(path).expanduser() for path in batch_dirs]
    else:
        resolved = _batch_directories(results_root)

    rows: List[Dict] = []
    for batch_dir in resolved:
        batch_rows = load_batch_rows(str(batch_dir))
        if not _batch_has_signal(batch_rows):
            continue
        rows.extend(batch_rows)
    return rows


def aggregate_study_rows(rows: List[Dict]) -> List[Dict]:
    """Aggregate repeated profile rows into mean/std summaries."""
    grouped: Dict[str, List[Dict]] = {}
    for row in rows:
        grouped.setdefault(row['profile_name'], []).append(row)

    aggregated = []
    for profile_name in sorted(grouped):
        samples = grouped[profile_name]
        summary: Dict[str, object] = {
            'profile_name': profile_name,
            'trials': len(samples),
        }
        for field in NUMERIC_FIELDS:
            values = [_to_float(sample.get(field, 0.0)) for sample in samples]
            summary[f'{field}_mean'] = mean(values)
            summary[f'{field}_std'] = stdev(values) if len(values) > 1 else 0.0
        aggregated.append(summary)
    return aggregated


def write_study_csv(results_root: str, rows: List[Dict]) -> Path:
    """Write the aggregate study CSV."""
    root = Path(results_root).expanduser()
    csv_path = root / 'study_comparison.csv'
    if not rows:
        raise ValueError('No aggregate rows available for study output.')

    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def write_study_json(results_root: str, rows: List[Dict], source_batches: List[str]) -> Path:
    """Write the aggregate study JSON."""
    root = Path(results_root).expanduser()
    json_path = root / 'study_comparison.json'
    payload = {
        'source_batches': source_batches,
        'profiles': rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    return json_path


def _metric_bar(rows: List[Dict], metric_name: str, max_width: int = 320) -> str:
    """Render a simple inline SVG bar chart for one aggregate metric."""
    values = [float(row.get(metric_name, 0.0) or 0.0) for row in rows]
    maximum = max(values) if values else 1.0
    if maximum <= 0.0:
        maximum = 1.0

    bar_height = 24
    gap = 12
    width = 620
    height = len(rows) * (bar_height + gap) + 20
    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg">'
    ]
    for index, row in enumerate(rows):
        y = 10 + index * (bar_height + gap)
        value = float(row.get(metric_name, 0.0) or 0.0)
        deviation = float(row.get(metric_name.replace('_mean', '_std'), 0.0) or 0.0)
        bar_width = int((value / maximum) * max_width)
        label = row['profile_name']
        parts.append(
            f'<text x="0" y="{y + 17}" font-size="12" fill="#222">{label}</text>'
        )
        parts.append(
            f'<rect x="140" y="{y}" width="{bar_width}" height="{bar_height}" '
            'fill="#2f7ed8" rx="4" ry="4"></rect>'
        )
        parts.append(
            f'<text x="{150 + bar_width}" y="{y + 17}" font-size="12" fill="#222">'
            f'{value:.2f} +/- {deviation:.2f}</text>'
        )
    parts.append('</svg>')
    return ''.join(parts)


def write_study_html(results_root: str, rows: List[Dict], source_batches: List[str]) -> Path:
    """Write a lightweight HTML report for repeated-batch aggregates."""
    root = Path(results_root).expanduser()
    html_path = root / 'study_comparison_report.html'
    headers = ''.join(f'<th>{key}</th>' for key in rows[0].keys())
    body_rows = ''.join(
        '<tr>' + ''.join(f'<td>{row[key]}</td>' for key in rows[0].keys()) + '</tr>'
        for row in rows
    )
    batch_items = ''.join(f'<li>{Path(path).name}</li>' for path in source_batches)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Repeated Experiment Study Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #f3f6fa; }}
    h2 {{ margin-top: 28px; }}
    .chart {{ margin-bottom: 24px; }}
  </style>
</head>
<body>
  <h1>Repeated Experiment Study Report</h1>
  <p>Source batches:</p>
  <ul>{batch_items}</ul>
  <table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{body_rows}</tbody>
  </table>
  <h2>Mean Total Events</h2>
  <div class="chart">{_metric_bar(rows, 'total_events_mean')}</div>
  <h2>Mean Stabilization Time (s)</h2>
  <div class="chart">{_metric_bar(rows, 'stabilization_sec_mean')}</div>
  <h2>Mean Task Switches</h2>
  <div class="chart">{_metric_bar(rows, 'total_task_switches_mean')}</div>
</body>
</html>
"""
    html_path.write_text(html, encoding='utf-8')
    return html_path


def write_study_outputs(
    results_root: str,
    batch_dirs: Iterable[str] = (),
) -> Dict[str, str]:
    """Collect repeated batches and write aggregate outputs."""
    rows = collect_study_rows(results_root, batch_dirs=batch_dirs)
    if not rows:
        raise FileNotFoundError('No batch comparison.csv files found for study report.')

    source_batches = sorted({row['batch_root'] for row in rows})
    aggregated = aggregate_study_rows(rows)
    csv_path = write_study_csv(results_root, aggregated)
    json_path = write_study_json(results_root, aggregated, source_batches)
    html_path = write_study_html(results_root, aggregated, source_batches)
    return {
        'csv_path': str(csv_path),
        'json_path': str(json_path),
        'html_path': str(html_path),
    }


def main(argv=None) -> int:
    """CLI entry point for repeated-batch aggregation."""
    parser = argparse.ArgumentParser(
        description='Aggregate multiple batch_* comparison.csv files into mean/std outputs.',
    )
    parser.add_argument(
        'results_root',
        help='Root directory containing batch_* experiment result directories.',
    )
    parser.add_argument(
        '--batch-dirs',
        nargs='*',
        default=(),
        help='Optional explicit batch directories to aggregate.',
    )
    args = parser.parse_args(argv)

    outputs = write_study_outputs(
        results_root=args.results_root,
        batch_dirs=args.batch_dirs,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
