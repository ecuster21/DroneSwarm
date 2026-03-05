"""Tests for paper-ready asset generation."""

import csv
import json

from offboard_py.paper_assets import write_paper_assets


def test_write_paper_assets_creates_tables_and_figures(tmp_path):
    """Paper asset generation should produce tables, figures, and a manifest."""
    study_csv = tmp_path / 'study_comparison.csv'
    with study_csv.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                'profile_name',
                'trials',
                'total_events_mean',
                'total_events_std',
                'bid_events_mean',
                'bid_events_std',
                'total_task_switches_mean',
                'total_task_switches_std',
                'stabilization_sec_mean',
                'stabilization_sec_std',
            ],
        )
        writer.writeheader()
        writer.writerows([
            {
                'profile_name': 'baseline',
                'trials': '3',
                'total_events_mean': '100',
                'total_events_std': '2',
                'bid_events_mean': '50',
                'bid_events_std': '1',
                'total_task_switches_mean': '0',
                'total_task_switches_std': '0',
                'stabilization_sec_mean': '1.0',
                'stabilization_sec_std': '0.1',
            },
            {
                'profile_name': 'delay',
                'trials': '3',
                'total_events_mean': '90',
                'total_events_std': '3',
                'bid_events_mean': '48',
                'bid_events_std': '2',
                'total_task_switches_mean': '1.2',
                'total_task_switches_std': '0.4',
                'stabilization_sec_mean': '1.5',
                'stabilization_sec_std': '0.3',
            },
        ])

    output_dir = tmp_path / 'paper_assets'
    outputs = write_paper_assets(str(study_csv), str(output_dir))

    assert (output_dir / 'paper_results_table.md').is_file()
    assert (output_dir / 'paper_results_table.tex').is_file()
    assert (output_dir / 'paper_results_summary.md').is_file()
    assert (output_dir / 'figure_total_events.svg').is_file()
    assert (output_dir / 'figure_bid_events.svg').is_file()
    assert (output_dir / 'figure_stabilization.svg').is_file()
    assert (output_dir / 'figure_task_switches.svg').is_file()
    assert (output_dir / 'paper_figures.html').is_file()
    assert (output_dir / 'paper_assets_manifest.json').is_file()

    markdown = (output_dir / 'paper_results_table.md').read_text(encoding='utf-8')
    assert 'Baseline' in markdown
    assert 'Delay' in markdown

    latex = (output_dir / 'paper_results_table.tex').read_text(encoding='utf-8')
    assert r'\begin{table}' in latex
    assert 'Stabilization (s)' in latex

    html = (output_dir / 'paper_figures.html').read_text(encoding='utf-8')
    assert 'Paper-Ready Results' in html
    assert 'figure_total_events.svg' in html

    manifest = json.loads((output_dir / 'paper_assets_manifest.json').read_text())
    assert outputs['manifest_path'] == str(output_dir / 'paper_assets_manifest.json')
    assert manifest['figures_html'] == str(output_dir / 'paper_figures.html')
