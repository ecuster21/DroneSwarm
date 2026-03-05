# Work Log

## 2026-03-04

### Session 1

Completed:

- Added the first AR-GCAA prototype inside `src/offboard_py`.
- Implemented `auction_core.py`, `auction_agent.py`, `task_board.py`, and `network_faults.py`.
- Registered new ROS 2 console entry points in `src/offboard_py/setup.py`.
- Added `std_msgs` dependency in `src/offboard_py/package.xml`.
- Added `test/test_auction_core.py` with four behavior checks.
- Verified `colcon build --packages-select offboard_py`.
- Verified `colcon test --packages-select offboard_py`.

Files changed:

- `src/offboard_py/offboard_py/auction_core.py`
- `src/offboard_py/offboard_py/auction_agent.py`
- `src/offboard_py/offboard_py/task_board.py`
- `src/offboard_py/offboard_py/network_faults.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/package.xml`
- `src/offboard_py/test/test_auction_core.py`

### Session 2

Completed:

- Created project-level documentation files: `README.md`, `Log.md`, and `Memory.md`.
- Added `src/offboard_py/launch/auction_sitl.launch.py` to start `task_board`, per-UAV `auction_agent`, per-UAV `offboard_control`, and optional per-UAV `network_faults`.
- Updated `auction_agent.py` so bid publishing can target either `auction/bid` or `auction/bid_raw`, allowing the relay layer to be inserted cleanly.
- Updated `src/offboard_py/setup.py` to install launch files.
- Added `launch` and `launch_ros` runtime dependencies in `src/offboard_py/package.xml`.
- Verified syntax for `src/offboard_py/offboard_py` and `src/offboard_py/launch` with `python3 -m compileall`.
- Re-ran `colcon build --packages-select offboard_py`.
- Re-ran `colcon test --packages-select offboard_py`.
- Confirmed `colcon test-result --verbose --test-result-base build/offboard_py` reports `0 failures`.

Files changed:

- `README.md`
- `Log.md`
- `Memory.md`
- `src/offboard_py/launch/auction_sitl.launch.py`
- `src/offboard_py/offboard_py/auction_agent.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/package.xml`

Next step:

- Add a reproducible multi-UAV experiment script or launch profile for baseline vs. delayed vs. dropped communication runs.
- Add at least one integration-style test around JSON topic flow and launch argument parsing.

### Session 3

Completed:

- Added three fixed experiment launch profiles for paper-style comparisons:
  `auction_baseline_experiment.launch.py`,
  `auction_delay_experiment.launch.py`,
  and `auction_loss_experiment.launch.py`.
- Reused `auction_sitl.launch.py` through launch inclusion so all three profiles stay aligned with the main stack.
- Added `ament_index_python` runtime dependency for the included launch files.
- Updated `README.md` with the new reproducible experiment commands.

Files changed:

- `src/offboard_py/launch/auction_baseline_experiment.launch.py`
- `src/offboard_py/launch/auction_delay_experiment.launch.py`
- `src/offboard_py/launch/auction_loss_experiment.launch.py`
- `src/offboard_py/package.xml`
- `README.md`
- `Log.md`

Next step:

- Add an integration-style test that validates the experiment launch files can be imported and that their fixed parameters are still what the paper setup expects.
- Add a small result-capture workflow for writing experiment metadata and run conditions alongside future plots.

### Session 4

Completed:

- Added `offboard_py/experiment_profiles.py` to centralize the fixed baseline, delay, and loss experiment configurations.
- Added `offboard_py/experiment_logger.py` and registered a new `experiment_logger` console entry point.
- Updated the three experiment launch files to consume the shared profiles and automatically start `experiment_logger`.
- Added `test/test_experiment_profiles.py` to validate fixed profile values, metadata file creation, and launch file structure.
- Updated `README.md` to document the new experiment manifest output directories.
- Verified syntax with `python3 -m compileall src/offboard_py/offboard_py src/offboard_py/launch`.
- Verified focused tests with
  `PYTHONPATH=src/offboard_py PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/offboard_py/test/test_auction_core.py src/offboard_py/test/test_experiment_profiles.py`.
- Re-ran `colcon build --packages-select offboard_py`.
- Re-ran `colcon test --packages-select offboard_py`.
- Confirmed `colcon test-result --verbose --test-result-base build/offboard_py` reports `0 failures`.

Files changed:

- `src/offboard_py/offboard_py/experiment_profiles.py`
- `src/offboard_py/offboard_py/experiment_logger.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/launch/auction_baseline_experiment.launch.py`
- `src/offboard_py/launch/auction_delay_experiment.launch.py`
- `src/offboard_py/launch/auction_loss_experiment.launch.py`
- `src/offboard_py/test/test_experiment_profiles.py`
- `README.md`
- `Log.md`

Next step:

- Run build and test again after the new shared profile and logger additions.
- If the new tests stay green, add one more integration check for the main `auction_sitl.launch.py` parameter surface.

Updated next step:

- Add one more focused test for `auction_sitl.launch.py` so the main launch parameter surface is also guarded.
- Add an optional runtime metrics recorder for allocation snapshots, so future figures can use structured logs instead of manual topic capture.

### Session 5

Completed:

- Added `offboard_py/metrics_store.py` for JSONL-based runtime metric persistence.
- Added `offboard_py/metrics_recorder.py` and registered the `metrics_recorder` console entry point.
- Updated `auction_sitl.launch.py` to expose metrics-related launch arguments and optionally start one `metrics_recorder` per UAV namespace.
- Updated the three experiment launch profiles to enable metrics and route them into the corresponding experiment result directories.
- Added `test/test_launch_surfaces.py` to guard the `auction_sitl.launch.py` argument surface and verify metrics recorder wiring.
- Added `test/test_metrics_store.py` to verify JSONL metric writes.
- Updated `README.md` to document runtime trace output locations and captured topics.
- Verified syntax with `python3 -m compileall src/offboard_py/offboard_py src/offboard_py/launch`.
- Verified focused tests with
  `PYTHONPATH=src/offboard_py PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/offboard_py/test/test_auction_core.py src/offboard_py/test/test_experiment_profiles.py src/offboard_py/test/test_launch_surfaces.py src/offboard_py/test/test_metrics_store.py`.
- Re-ran `colcon build --packages-select offboard_py`.
- Re-ran `colcon test --packages-select offboard_py`.
- Confirmed `colcon test-result --verbose --test-result-base build/offboard_py` reports `0 failures`.

Files changed:

- `src/offboard_py/offboard_py/metrics_store.py`
- `src/offboard_py/offboard_py/metrics_recorder.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/launch/auction_sitl.launch.py`
- `src/offboard_py/launch/auction_baseline_experiment.launch.py`
- `src/offboard_py/launch/auction_delay_experiment.launch.py`
- `src/offboard_py/launch/auction_loss_experiment.launch.py`
- `src/offboard_py/test/test_launch_surfaces.py`
- `src/offboard_py/test/test_metrics_store.py`
- `README.md`
- `Log.md`

Next step:

- Re-run focused tests plus `colcon build/test` after the new metrics path is wired in.
- Add one more small helper for post-processing these JSON and JSONL artifacts into table-ready summaries.

Updated next step:

- Add a small post-processing helper that converts the experiment manifest plus per-UAV JSONL traces into summary rows for tables.
- If needed, add a dedicated launch profile for a higher-stress scenario (for example combined delay + loss) after the baseline paper figures are stable.

### Session 6

Completed:

- Added `offboard_py/experiment_summary.py` as a post-processing helper and CLI entry point.
- Registered the `experiment_summarizer` console command in `src/offboard_py/setup.py`.
- Added `test/test_experiment_summary.py` to validate manifest discovery, event aggregation, switch counting, and summary file generation.
- Updated `README.md` with the summary command and generated output files.
- Verified syntax with `python3 -m compileall src/offboard_py/offboard_py`.
- Verified focused tests with
  `PYTHONPATH=src/offboard_py PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/offboard_py/test/test_experiment_summary.py src/offboard_py/test/test_metrics_store.py src/offboard_py/test/test_experiment_profiles.py src/offboard_py/test/test_launch_surfaces.py src/offboard_py/test/test_auction_core.py`.
- Re-ran `colcon build --packages-select offboard_py`.
- Re-ran `colcon test --packages-select offboard_py`.
- Confirmed `colcon test-result --verbose --test-result-base build/offboard_py` reports `0 failures`.

Files changed:

- `src/offboard_py/offboard_py/experiment_summary.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/test/test_experiment_summary.py`
- `README.md`
- `Log.md`

Next step:

- Run the new summary tests and then re-run `colcon build/test`.
- After that, decide whether to add a combined delay+loss stress profile or to keep building analysis helpers.

Updated next step:

- Add a combined delay+loss stress experiment profile if we want one more stronger comparison for the paper.
- Or add richer post-processing metrics, such as per-UAV first lock time and per-task occupancy estimates, on top of the current summaries.

### Session 7

Completed:

- Added a new shared `stress` experiment profile combining the current delay and loss settings.
- Added `src/offboard_py/launch/auction_stress_experiment.launch.py` for a fixed delay+loss comparison run.
- Updated `test/test_experiment_profiles.py` to validate the new `stress` profile and launch file.
- Updated `README.md` with the new stress experiment command and output directory.
- Verified syntax with `python3 -m compileall src/offboard_py/offboard_py src/offboard_py/launch`.
- Verified focused tests with
  `PYTHONPATH=src/offboard_py PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/offboard_py/test/test_experiment_profiles.py src/offboard_py/test/test_experiment_summary.py src/offboard_py/test/test_launch_surfaces.py src/offboard_py/test/test_metrics_store.py src/offboard_py/test/test_auction_core.py`.
- Re-ran `colcon build --packages-select offboard_py`.
- Re-ran `colcon test --packages-select offboard_py`.
- Confirmed `colcon test-result --verbose --test-result-base build/offboard_py` reports `0 failures`.

Files changed:

- `src/offboard_py/offboard_py/experiment_profiles.py`
- `src/offboard_py/launch/auction_stress_experiment.launch.py`
- `src/offboard_py/test/test_experiment_profiles.py`
- `README.md`
- `Log.md`

Next step:

- Re-run focused tests plus `colcon build/test` after the new stress profile is added.
- After that, either extend summaries with richer metrics or stop this implementation track and move to actual SITL data collection.

Updated next step:

- The code side is now at a reasonable stopping point; the highest-value next action is actual SITL data collection using `baseline`, `delay`, `loss`, and `stress`.
- If more coding is needed later, the next additions should be richer summary metrics rather than more infrastructure.

### Session 8

Completed:

- Updated `auction_sitl.launch.py` to support a configurable `namespace_prefix`.
- Changed the default namespace prefix to `px4_` so the launch matches common PX4 DDS topics like `/px4_1/...`.
- Updated `test/test_launch_surfaces.py` for the new launch argument.
- Updated `README.md` to document the new default and the `namespace_prefix:=uav` override.
- Verified syntax with `python3 -m compileall src/offboard_py/launch`.
- Verified focused tests with
  `PYTHONPATH=src/offboard_py PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/offboard_py/test/test_launch_surfaces.py src/offboard_py/test/test_experiment_profiles.py src/offboard_py/test/test_experiment_summary.py src/offboard_py/test/test_metrics_store.py src/offboard_py/test/test_auction_core.py`.
- Re-ran `colcon build --packages-select offboard_py`.
- Re-ran `colcon test --packages-select offboard_py`.
- Confirmed `colcon test-result --verbose --test-result-base build/offboard_py` reports `0 failures`.

### Session 9

Completed:

- Updated `experiment_logger.py` so it writes the manifest once and exits immediately.
- This removes the need to wrap `ros2 run offboard_py experiment_logger ...` with `timeout`.
- Corrected the summary workflow guidance: `experiment_summarizer` should be run via `ros2 run offboard_py experiment_summarizer ...` in this ROS 2 workspace layout.
- Fixed `auction_agent.py` to subscribe to PX4 `fmu/out/*` topics with a PX4-compatible QoS profile.
- This addresses the case where `auction/allocation` exists but never publishes because the node never receives `vehicle_local_position`.
- Fixed `auction_agent.py` parameter declaration for `peer_namespaces` by avoiding an ambiguous empty-list default.
- This addresses the likely startup crash where `auction_agent` exits immediately with code 1 during launch.

Files changed:

- `src/offboard_py/offboard_py/experiment_logger.py`
- `src/offboard_py/offboard_py/auction_agent.py`
- `README.md`
- `Log.md`

Next step:

- Rebuild `offboard_py` so the installed console entry point picks up the new one-shot behavior.

Files changed:

- `src/offboard_py/launch/auction_sitl.launch.py`
- `src/offboard_py/test/test_launch_surfaces.py`
- `README.md`
- `Log.md`

Next step:

- Re-run focused tests plus `colcon build/test` after the namespace update.
- Then the user can run the stack against `/px4_1/...` topics directly, most likely with `uav_count:=1` for the current setup.

### Session 10

Completed:

- Fixed `task_board.py` so `popup_tasks_json: '[]'` no longer silently expands to the default 4 tasks.
- Added `offboard_py/task_catalog.py` so task parsing helpers can be tested without importing ROS runtime dependencies.
- Added `offboard_py/experiment_report.py` to build `comparison.csv` and `comparison_report.html`.
- Added `offboard_py/experiment_batch.py` to run `baseline`, `delay`, `loss`, and `stress` sequentially.
- Registered the new `experiment_reporter` and `experiment_batch_runner` console commands.
- Added tests for task parsing and comparison report generation.
- Updated `README.md` with the new batch-runner and comparison-report workflow.
- Verified focused tests with
  `PYTHONPATH=src/offboard_py PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest ...`
  covering the expanded report and task helpers.
- Re-ran `colcon build --packages-select offboard_py`.
- Re-ran `colcon test --packages-select offboard_py`.
- Confirmed `colcon test-result --verbose --test-result-base build/offboard_py` reports `0 failures`.

Files changed:

- `src/offboard_py/offboard_py/task_board.py`
- `src/offboard_py/offboard_py/task_catalog.py`
- `src/offboard_py/offboard_py/experiment_report.py`
- `src/offboard_py/offboard_py/experiment_batch.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/test/test_task_board.py`
- `src/offboard_py/test/test_experiment_report.py`
- `README.md`
- `Log.md`

Next step:

- Re-run focused tests plus `colcon build/test`.
- For full paper-style data collection, ask the user to bring up 4 PX4 vehicles with DDS (`/px4_1` to `/px4_4`) and then run the batch runner.

Updated next step:

- For full paper-style data collection, the user should now bring up 4 PX4 vehicles with DDS (`/px4_1` to `/px4_4`).
- Once those are online, run the batch runner to collect all four profiles and generate the comparison outputs automatically.

### Session 11

Completed:

- Ran the full 4-UAV batch experiment against live PX4 DDS namespaces `/px4_1` through `/px4_4`.
- Executed `ros2 run offboard_py experiment_batch_runner --duration-sec 60 --uav-count 4 --namespace-prefix px4_`.
- Completed all four profiles: `baseline`, `delay`, `loss`, and `stress`.
- Generated per-profile manifests and summaries under `experiment_results/batch_20260304T140404Z/`.
- Generated comparison outputs:
  `experiment_results/batch_20260304T140404Z/comparison.csv`
  and
  `experiment_results/batch_20260304T140404Z/comparison_report.html`.
- Confirmed the batch runner exited with code `0`.
- Updated `README.md` with the latest measured 4-UAV comparison table and result paths.

Key measured results:

- `baseline`: `total_events=3570`, `total_task_switches=0`, `stabilization_sec=0.807760`
- `delay`: `total_events=3549`, `total_task_switches=3`, `stabilization_sec=1.400154`
- `loss`: `total_events=3284`, `bid_events=920`, `stabilization_sec=1.827905`
- `stress`: `total_events=3294`, `bid_events=906`, `total_task_switches=2`, `stabilization_sec=1.073516`

Files changed:

- `README.md`
- `Log.md`

Next step:

- Extract the comparison CSV into the paper's result table and use `comparison_report.html` as the immediate chart artifact.
- If needed, add a second batch with a longer duration or repeated trials to compute averages and variance bars.

### Session 12

Completed:

- Added `offboard_py/experiment_study.py` to aggregate repeated `batch_*` runs into mean/std outputs.
- Registered the new `experiment_study_reporter` console command.
- Added `test_experiment_study.py` to validate cross-batch aggregation and zero-signal batch filtering.
- Ran focused tests for the new aggregation path.
- Rebuilt `offboard_py`.
- Ran 2 additional full 4-UAV live batch experiments with:
  `ros2 run offboard_py experiment_batch_runner --duration-sec 60 --uav-count 4 --namespace-prefix px4_`
- Generated two new valid batch directories:
  `experiment_results/batch_20260304T142728Z`
  and
  `experiment_results/batch_20260304T143351Z`
- Regenerated the cross-batch aggregate outputs:
  `experiment_results/study_comparison.csv`
  `experiment_results/study_comparison.json`
  `experiment_results/study_comparison_report.html`
- Fixed the aggregate tool to skip failed or zero-signal batch directories, which excluded the earlier invalid `batch_20260304T140317Z`.
- Updated `README.md` with the repeated 3-trial 4-UAV study results and output paths.

Key repeated-trial results (3 valid batches):

- `baseline`: `total_events_mean=3570.00`, `bid_events_mean=1190.00`, `stabilization_sec_mean=0.805408`
- `delay`: `total_events_mean=3556.33`, `bid_events_mean=1183.00`, `stabilization_sec_mean=1.072235`
- `loss`: `total_events_mean=3298.33`, `bid_events_mean=925.00`, `stabilization_sec_mean=1.348180`
- `stress`: `total_events_mean=3284.00`, `bid_events_mean=902.67`, `stabilization_sec_mean=0.904953`

Paper-facing comparison versus `baseline`:

- `delay`: stabilization `+33.13%`
- `loss`: bid propagation `-22.27%`, stabilization `+67.39%`
- `stress`: bid propagation `-24.15%`, stabilization `+12.36%`

Files changed:

- `src/offboard_py/offboard_py/experiment_study.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/test/test_experiment_study.py`
- `README.md`
- `Log.md`

Next step:

- Use `study_comparison.csv` as the main experiment table for the paper.
- If stronger statistical support is needed, run 2 to 3 more batches and regenerate the study report for 5 to 6 total trials.

### Session 13

Completed:

- Added `offboard_py/paper_assets.py` to convert `study_comparison.csv` into paper-ready deliverables.
- Registered the new `experiment_paper_assets` console command.
- Added `test_paper_assets.py` to validate generated tables, figures, and manifest output.
- Rebuilt `offboard_py`.
- Generated the final paper asset bundle under `experiment_results/paper_assets/`.
- Produced:
  `paper_results_table.md`
  `paper_results_table.tex`
  `paper_results_summary.md`
  `figure_total_events.svg`
  `figure_bid_events.svg`
  `figure_stabilization.svg`
  `figure_task_switches.svg`
  `paper_figures.html`
- Adjusted the export formatting so:
  Markdown uses ASCII `+/-`
  and LaTeX uses `$\pm$`.
- Updated `README.md` with the paper-asset workflow and final output paths.

Files changed:

- `src/offboard_py/offboard_py/paper_assets.py`
- `src/offboard_py/setup.py`
- `src/offboard_py/test/test_paper_assets.py`
- `README.md`
- `Log.md`

Next step:

- Use `paper_results_table.tex` directly in the paper.
- Use `paper_figures.html` for screenshot export, or import the standalone SVG files into the paper figure workflow.

### Session 14

Completed:

- Saved the full paper draft as a standalone Markdown file at the workspace root.
- The draft includes the complete article body, repeated-trial result table, and links to the generated paper assets.

Files changed:

- `AR_GCAA_Paper_Draft.md`
- `Log.md`

Next step:

- If needed, convert `AR_GCAA_Paper_Draft.md` into an English paper draft or a full LaTeX manuscript structure.
