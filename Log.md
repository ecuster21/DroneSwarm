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
