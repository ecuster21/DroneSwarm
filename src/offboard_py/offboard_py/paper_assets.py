"""Build paper-ready tables and figures from the repeated-study CSV."""

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import List


PROFILE_LABELS = {
    'baseline': 'Baseline',
    'delay': 'Delay',
    'loss': 'Loss',
    'stress': 'Stress',
}


def load_study_rows(study_csv_path: str) -> List[Dict]:
    """Load aggregate study rows from CSV."""
    csv_path = Path(study_csv_path).expanduser()
    with csv_path.open('r', newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def _to_float(value) -> float:
    """Convert numeric string values into floats."""
    if value in (None, ''):
        return 0.0
    return float(value)


def _profile_label(profile_name: str) -> str:
    """Map internal profile names to paper labels."""
    return PROFILE_LABELS.get(profile_name, profile_name)


def _mean_std(
    row: Dict,
    field: str,
    decimals: int = 2,
    separator: str = ' +/- ',
) -> str:
    """Format a mean ± std cell."""
    mean_value = _to_float(row[f'{field}_mean'])
    std_value = _to_float(row[f'{field}_std'])
    return (
        f'{mean_value:.{decimals}f}'
        + separator
        + f'{std_value:.{decimals}f}'
    )


def write_markdown_table(output_dir: str, rows: List[Dict]) -> Path:
    """Write a Markdown table suitable for quick paper drafting."""
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / 'paper_results_table.md'

    lines = [
        '# Paper Results Table',
        '',
        '| Scenario | Trials | Total Events | Bid Events | Task Switches | Stabilization (s) |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in rows:
        lines.append(
            '| '
            + _profile_label(row['profile_name'])
            + f" | {int(_to_float(row['trials']))}"
            + f" | {_mean_std(row, 'total_events', 2, separator=' +/- ')}"
            + f" | {_mean_std(row, 'bid_events', 2, separator=' +/- ')}"
            + f" | {_mean_std(row, 'total_task_switches', 2, separator=' +/- ')}"
            + f" | {_mean_std(row, 'stabilization_sec', 3, separator=' +/- ')} |"
        )
    md_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return md_path


def write_latex_table(output_dir: str, rows: List[Dict]) -> Path:
    """Write a LaTeX table for direct paper inclusion."""
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / 'paper_results_table.tex'
    latex_pm = ' $\\pm$ '

    lines = [
        r'\begin{table}[t]',
        r'\centering',
        r'\caption{Repeated 4-UAV experiment results over 3 trials.}',
        r'\label{tab:repeated-study-results}',
        r'\begin{tabular}{lccccc}',
        r'\hline',
        r'Scenario & Trials & Total Events & Bid Events & Task Switches & Stabilization (s) \\',
        r'\hline',
    ]
    for row in rows:
        lines.append(
            f"{_profile_label(row['profile_name'])}"
            + f" & {int(_to_float(row['trials']))}"
            + f" & {_mean_std(row, 'total_events', 2, separator=latex_pm)}"
            + f" & {_mean_std(row, 'bid_events', 2, separator=latex_pm)}"
            + f" & {_mean_std(row, 'total_task_switches', 2, separator=latex_pm)}"
            + f" & {_mean_std(row, 'stabilization_sec', 3, separator=latex_pm)} \\\\"
        )
    lines.extend([
        r'\hline',
        r'\end{tabular}',
        r'\end{table}',
        '',
    ])
    tex_path.write_text('\n'.join(lines), encoding='utf-8')
    return tex_path


def _svg_bar_chart(
    rows: List[Dict],
    mean_field: str,
    std_field: str,
    title: str,
    x_label: str,
    color: str,
) -> str:
    """Render a standalone SVG horizontal bar chart with error bars."""
    left_margin = 160
    top_margin = 54
    chart_width = 520
    bar_height = 30
    gap = 20
    width = 840
    height = top_margin + len(rows) * (bar_height + gap) + 80

    max_value = max(
        _to_float(row[mean_field]) + _to_float(row[std_field]) for row in rows
    )
    if max_value <= 0.0:
        max_value = 1.0

    def x_pos(value: float) -> float:
        return left_margin + (value / max_value) * chart_width

    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg">',
        '<rect width="100%" height="100%" fill="#fffdf8"></rect>',
        f'<text x="{left_margin}" y="26" font-size="20" fill="#1e293b" '
        'font-family="Georgia, serif">'
        f'{html.escape(title)}</text>',
        f'<text x="{left_margin}" y="46" font-size="11" fill="#475569" '
        'font-family="Arial, sans-serif">'
        f'{html.escape(x_label)}</text>',
        f'<line x1="{left_margin}" y1="{height - 40}" x2="{left_margin + chart_width}" '
        f'y2="{height - 40}" stroke="#cbd5e1" stroke-width="1"></line>',
    ]

    tick_count = 5
    for tick in range(tick_count + 1):
        value = (max_value / tick_count) * tick
        x = x_pos(value)
        parts.append(
            f'<line x1="{x:.2f}" y1="{height - 40}" x2="{x:.2f}" y2="{height - 34}" '
            'stroke="#94a3b8" stroke-width="1"></line>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{height - 18}" text-anchor="middle" '
            'font-size="10" fill="#64748b" font-family="Arial, sans-serif">'
            f'{value:.1f}</text>'
        )

    for index, row in enumerate(rows):
        y = top_margin + index * (bar_height + gap)
        center_y = y + bar_height / 2
        label = _profile_label(row['profile_name'])
        mean_value = _to_float(row[mean_field])
        std_value = _to_float(row[std_field])
        bar_end = x_pos(mean_value)
        err_end = x_pos(mean_value + std_value)
        parts.append(
            f'<text x="{left_margin - 14}" y="{center_y + 4:.2f}" text-anchor="end" '
            'font-size="13" fill="#0f172a" font-family="Arial, sans-serif">'
            f'{html.escape(label)}</text>'
        )
        parts.append(
            f'<rect x="{left_margin}" y="{y}" width="{bar_end - left_margin:.2f}" '
            f'height="{bar_height}" fill="{color}" rx="6" ry="6"></rect>'
        )
        parts.append(
            f'<line x1="{bar_end:.2f}" y1="{center_y:.2f}" x2="{err_end:.2f}" '
            f'y2="{center_y:.2f}" stroke="#334155" stroke-width="2"></line>'
        )
        parts.append(
            f'<line x1="{err_end:.2f}" y1="{center_y - 7:.2f}" x2="{err_end:.2f}" '
            f'y2="{center_y + 7:.2f}" stroke="#334155" stroke-width="2"></line>'
        )
        parts.append(
            f'<text x="{err_end + 10:.2f}" y="{center_y + 4:.2f}" '
            'font-size="12" fill="#334155" font-family="Arial, sans-serif">'
            f'{mean_value:.2f} +/- {std_value:.2f}</text>'
        )

    parts.append('</svg>')
    return ''.join(parts)


def write_svg_chart(
    output_dir: str,
    filename: str,
    rows: List[Dict],
    mean_field: str,
    std_field: str,
    title: str,
    x_label: str,
    color: str,
) -> Path:
    """Write one standalone SVG chart."""
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(
        _svg_bar_chart(
            rows=rows,
            mean_field=mean_field,
            std_field=std_field,
            title=title,
            x_label=x_label,
            color=color,
        ),
        encoding='utf-8',
    )
    return path


def write_summary_text(output_dir: str, rows: List[Dict]) -> Path:
    """Write a short paper-facing summary."""
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / 'paper_results_summary.md'

    baseline = next(row for row in rows if row['profile_name'] == 'baseline')
    base_stab = _to_float(baseline['stabilization_sec_mean'])
    base_bids = _to_float(baseline['bid_events_mean'])

    lines = [
        '# Paper Result Summary',
        '',
        'This summary is derived from `experiment_results/study_comparison.csv`.',
        '',
    ]
    for row in rows:
        if row['profile_name'] == 'baseline':
            continue
        stab = _to_float(row['stabilization_sec_mean'])
        bids = _to_float(row['bid_events_mean'])
        task_switches = _to_float(row['total_task_switches_mean'])
        stab_delta = ((stab - base_stab) / base_stab) * 100.0 if base_stab else 0.0
        bid_delta = ((bids - base_bids) / base_bids) * 100.0 if base_bids else 0.0
        lines.append(
            f"- {_profile_label(row['profile_name'])}: "
            f"stabilization {stab_delta:+.2f}%, "
            f"bid propagation {bid_delta:+.2f}%, "
            f"mean task switches {task_switches:.2f}."
        )
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def write_figures_html(output_dir: str, rows: List[Dict], figure_paths: Iterable[Path]) -> Path:
    """Write a single HTML page that embeds all paper figures and the compact table."""
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / 'paper_figures.html'

    table_headers = (
        '<tr>'
        '<th>Scenario</th><th>Trials</th><th>Total Events</th><th>Bid Events</th>'
        '<th>Task Switches</th><th>Stabilization (s)</th>'
        '</tr>'
    )
    table_rows = ''.join(
        '<tr>'
        f'<td>{html.escape(_profile_label(row["profile_name"]))}</td>'
        f'<td>{int(_to_float(row["trials"]))}</td>'
        f'<td>{html.escape(_mean_std(row, "total_events", 2))}</td>'
        f'<td>{html.escape(_mean_std(row, "bid_events", 2))}</td>'
        f'<td>{html.escape(_mean_std(row, "total_task_switches", 2))}</td>'
        f'<td>{html.escape(_mean_std(row, "stabilization_sec", 3))}</td>'
        '</tr>'
        for row in rows
    )
    figures = ''.join(
        '<section class="figure">'
        f'<img src="{html.escape(path.name)}" alt="{html.escape(path.stem)}">'
        '</section>'
        for path in figure_paths
    )
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Paper Figures</title>
  <style>
    body {{ margin: 24px; background: #f8fafc; color: #0f172a; }}
    h1, h2 {{ font-family: Georgia, serif; }}
    p, td, th {{ font-family: Arial, sans-serif; }}
    .panel {{
      background: white;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 18px;
      margin-bottom: 20px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
    th {{ background: #f8fafc; }}
    img {{ width: 100%; height: auto; display: block; }}
    .figure {{ margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>Paper-Ready Results</h1>
    <p>Compact repeated-trial summary table and standalone figures for direct screenshotting.</p>
  </div>
  <div class="panel">
    <h2>Compact Result Table</h2>
    <table>
      <thead>{table_headers}</thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
  <div class="panel">
    <h2>Figures</h2>
    {figures}
  </div>
</body>
</html>
"""
    html_path.write_text(html_text, encoding='utf-8')
    return html_path


def write_paper_assets(study_csv_path: str, output_dir: str) -> Dict[str, str]:
    """Generate table and figure assets for the paper."""
    rows = load_study_rows(study_csv_path)
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = write_markdown_table(str(out_dir), rows)
    latex_path = write_latex_table(str(out_dir), rows)
    summary_path = write_summary_text(str(out_dir), rows)

    figure_specs = [
        (
            'figure_total_events.svg',
            'total_events_mean',
            'total_events_std',
            'Mean Total Events Across 4-UAV Trials',
            'Event count (mean ± std)',
            '#0f766e',
        ),
        (
            'figure_bid_events.svg',
            'bid_events_mean',
            'bid_events_std',
            'Mean Bid Propagation Across 4-UAV Trials',
            'Bid events (mean ± std)',
            '#b45309',
        ),
        (
            'figure_stabilization.svg',
            'stabilization_sec_mean',
            'stabilization_sec_std',
            'Mean Stabilization Time Across 4-UAV Trials',
            'Stabilization time in seconds (mean ± std)',
            '#1d4ed8',
        ),
        (
            'figure_task_switches.svg',
            'total_task_switches_mean',
            'total_task_switches_std',
            'Mean Task Reassignments Across 4-UAV Trials',
            'Task switches (mean ± std)',
            '#be123c',
        ),
    ]
    figure_paths = [
        write_svg_chart(
            output_dir=str(out_dir),
            filename=filename,
            rows=rows,
            mean_field=mean_field,
            std_field=std_field,
            title=title,
            x_label=x_label,
            color=color,
        )
        for filename, mean_field, std_field, title, x_label, color in figure_specs
    ]
    html_path = write_figures_html(str(out_dir), rows, figure_paths)

    manifest_path = out_dir / 'paper_assets_manifest.json'
    payload = {
        'study_csv_path': str(Path(study_csv_path).expanduser()),
        'markdown_table': str(markdown_path),
        'latex_table': str(latex_path),
        'summary': str(summary_path),
        'figures_html': str(html_path),
        'figures': [str(path) for path in figure_paths],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')

    return {
        'manifest_path': str(manifest_path),
        'markdown_table': str(markdown_path),
        'latex_table': str(latex_path),
        'summary': str(summary_path),
        'figures_html': str(html_path),
        'figures_dir': str(out_dir),
    }


def main(argv=None) -> int:
    """CLI entry point for paper asset generation."""
    parser = argparse.ArgumentParser(
        description='Build paper-ready tables and figure assets from study_comparison.csv.',
    )
    parser.add_argument(
        '--study-csv',
        default='experiment_results/study_comparison.csv',
        help='Path to the repeated-study CSV.',
    )
    parser.add_argument(
        '--output-dir',
        default='experiment_results/paper_assets',
        help='Directory where paper-ready assets will be written.',
    )
    args = parser.parse_args(argv)

    outputs = write_paper_assets(
        study_csv_path=args.study_csv,
        output_dir=args.output_dir,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
