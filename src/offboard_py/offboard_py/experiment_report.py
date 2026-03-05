"""Build comparison tables and a simple HTML report from experiment summaries."""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import List


DEFAULT_PROFILES = ['baseline', 'delay', 'loss', 'stress']


def load_profile_summary(results_dir: str, profile_name: str) -> Dict:
    """Load the latest summary JSON for a profile directory."""
    profile_dir = Path(results_dir).expanduser() / profile_name
    summary_files = sorted(profile_dir.glob('*_summary.json'))
    if not summary_files:
        raise FileNotFoundError(
            f'No summary JSON found for profile "{profile_name}" in {profile_dir}'
        )
    return json.loads(summary_files[-1].read_text())


def collect_profile_rows(
    results_dir: str,
    profiles: Iterable[str] = DEFAULT_PROFILES,
) -> List[Dict]:
    """Collect one CSV-friendly row per profile from existing summaries."""
    rows = []
    for profile_name in profiles:
        summary = load_profile_summary(results_dir, profile_name)
        topic_counts = summary.get('topic_counts', {})
        parameters = summary.get('parameters', {})
        rows.append({
            'profile_name': profile_name,
            'uav_count': parameters.get('uav_count', ''),
            'drop_probability': parameters.get('drop_probability', ''),
            'delay_mean_ms': parameters.get('delay_mean_ms', ''),
            'delay_jitter_ms': parameters.get('delay_jitter_ms', ''),
            'total_events': summary.get('total_events', 0),
            'allocation_events': topic_counts.get('auction/allocation', 0),
            'bid_events': topic_counts.get('auction/bid', 0),
            'local_state_events': topic_counts.get('auction/local_state', 0),
            'total_task_switches': summary.get('total_task_switches', 0),
            'runtime_sec': summary.get('runtime_sec', 0.0),
            'stabilization_sec': summary.get('stabilization_sec', 0.0),
        })
    return rows


def write_comparison_csv(results_dir: str, rows: List[Dict]) -> Path:
    """Write a comparison CSV covering all requested profiles."""
    results_path = Path(results_dir).expanduser()
    csv_path = results_path / 'comparison.csv'
    if not rows:
        raise ValueError('No rows available for comparison report.')

    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def _metric_bar(rows: List[Dict], metric_name: str, max_width: int = 320) -> str:
    """Render a simple inline SVG bar chart for one metric."""
    values = [float(row.get(metric_name, 0.0) or 0.0) for row in rows]
    maximum = max(values) if values else 1.0
    if maximum <= 0.0:
        maximum = 1.0

    bar_height = 24
    gap = 12
    width = 520
    height = len(rows) * (bar_height + gap) + 20
    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg">'
    ]
    for index, row in enumerate(rows):
        y = 10 + index * (bar_height + gap)
        value = float(row.get(metric_name, 0.0) or 0.0)
        bar_width = int((value / maximum) * max_width)
        label = row['profile_name']
        parts.append(
            f'<text x="0" y="{y + 17}" font-size="12" fill="#222">{label}</text>'
        )
        parts.append(
            f'<rect x="110" y="{y}" width="{bar_width}" height="{bar_height}" '
            'fill="#2f7ed8" rx="4" ry="4"></rect>'
        )
        parts.append(
            f'<text x="{120 + bar_width}" y="{y + 17}" font-size="12" fill="#222">'
            f'{value:.2f}</text>'
        )
    parts.append('</svg>')
    return ''.join(parts)


def write_html_report(results_dir: str, rows: List[Dict]) -> Path:
    """Write a lightweight HTML report with a table and inline SVG charts."""
    results_path = Path(results_dir).expanduser()
    html_path = results_path / 'comparison_report.html'
    table_headers = ''.join(
        f'<th>{key}</th>' for key in rows[0].keys()
    )
    table_rows = ''.join(
        '<tr>' + ''.join(f'<td>{row[key]}</td>' for key in rows[0].keys()) + '</tr>'
        for row in rows
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Experiment Comparison Report</title>
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
  <h1>Experiment Comparison Report</h1>
  <table>
    <thead><tr>{table_headers}</tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
  <h2>Total Events</h2>
  <div class="chart">{_metric_bar(rows, 'total_events')}</div>
  <h2>Total Task Switches</h2>
  <div class="chart">{_metric_bar(rows, 'total_task_switches')}</div>
  <h2>Stabilization Time (s)</h2>
  <div class="chart">{_metric_bar(rows, 'stabilization_sec')}</div>
</body>
</html>
"""
    html_path.write_text(html, encoding='utf-8')
    return html_path


def write_comparison_outputs(
    results_dir: str,
    profiles: Iterable[str] = DEFAULT_PROFILES,
) -> Dict[str, str]:
    """Create both CSV and HTML comparison outputs for the selected profiles."""
    rows = collect_profile_rows(results_dir, profiles=profiles)
    csv_path = write_comparison_csv(results_dir, rows)
    html_path = write_html_report(results_dir, rows)
    return {
        'csv_path': str(csv_path),
        'html_path': str(html_path),
    }


def main(argv=None) -> int:
    """CLI entry point for building a comparison report."""
    parser = argparse.ArgumentParser(
        description='Build a comparison report from per-profile experiment summaries.',
    )
    parser.add_argument(
        'results_dir',
        help=(
            'Batch result directory containing subdirectories such as '
            'baseline/delay/loss/stress.'
        ),
    )
    parser.add_argument(
        '--profiles',
        nargs='*',
        default=DEFAULT_PROFILES,
        help='Profiles to include in the comparison report.',
    )
    args = parser.parse_args(argv)

    outputs = write_comparison_outputs(
        results_dir=args.results_dir,
        profiles=args.profiles,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
