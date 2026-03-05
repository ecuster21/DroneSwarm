# px4_ros_com_ws

This workspace now contains two coordinated tracks:

- `src/offboard_py`: the ROS 2 execution layer for PX4 offboard control plus the new asynchronous auction prototype.
- `task-allocation-auctions-main`: the original GCAA paper codebase used as the algorithmic reference and comparison baseline.

## Current Focus

The current implementation direction is an `AR-GCAA` prototype:

- asynchronous local rebidding instead of globally synchronized rounds
- timestamped neighbor bids with stale-data aging and drop rules
- task-switch penalties plus hysteresis to suppress assignment thrashing
- a ROS 2 integration path that can drive existing `mission_setpoint` consumers

## Implemented Components

Under `src/offboard_py/offboard_py`:

- `offboard_control.py`: existing PX4 setpoint executor
- `auction_core.py`: pure-Python asynchronous auction logic
- `auction_agent.py`: per-UAV ROS 2 wrapper around the auction core
- `task_board.py`: shared task publisher for static and popup tasks
- `network_faults.py`: topic relay for delay/jitter/drop injection
- `experiment_profiles.py`: fixed paper-style experiment profiles
- `experiment_logger.py`: writes experiment manifests for each launched profile
- `metrics_store.py`: JSONL helpers for runtime metric persistence
- `metrics_recorder.py`: subscribes to auction topics and stores runtime traces
- `experiment_summary.py`: turns manifests plus JSONL traces into summary JSON and CSV
- `experiment_report.py`: builds comparison CSV and HTML reports across profiles
- `experiment_batch.py`: runs baseline/delay/loss/stress sequentially

Under `src/offboard_py/launch`:

- `auction_sitl.launch.py`: bring-up for a small multi-UAV SITL stack
- `auction_baseline_experiment.launch.py`: fixed baseline profile, no injected faults
- `auction_delay_experiment.launch.py`: fixed delay profile, 200 ms mean delay with 50 ms jitter
- `auction_loss_experiment.launch.py`: fixed packet-loss profile, 20% drop rate
- `auction_stress_experiment.launch.py`: fixed stress profile, delay and packet loss combined

## Topic Model

- `/task_board/tasks`: JSON array of tasks
- `/<uav_ns>/auction/local_state`: JSON local agent state
- `/<uav_ns>/auction/bid_raw`: raw bid output when fault injection is enabled
- `/<uav_ns>/auction/bid`: relayed bid output after simulated network effects
- `/<uav_ns>/auction/allocation`: local allocation snapshot
- `/<uav_ns>/mission_setpoint`: final target consumed by `offboard_control`

## Basic Workflow

1. Build the package:
   `colcon build --packages-select offboard_py`
2. Source the workspace:
   `source install/setup.bash`
3. Launch the stack:
   `ros2 launch offboard_py auction_sitl.launch.py`

Reproducible experiment profiles:

- Baseline:
  `ros2 launch offboard_py auction_baseline_experiment.launch.py`
- Delay:
  `ros2 launch offboard_py auction_delay_experiment.launch.py`
- Packet loss:
  `ros2 launch offboard_py auction_loss_experiment.launch.py`
- Stress:
  `ros2 launch offboard_py auction_stress_experiment.launch.py`

Each experiment profile also writes a JSON manifest under:

- `experiment_results/baseline/`
- `experiment_results/delay/`
- `experiment_results/loss/`
- `experiment_results/stress/`

The manifest stores the profile name, timestamp, and fixed run parameters so
future plots and tables can be traced back to the exact launch conditions.

When metrics are enabled, each UAV also writes JSONL traces under the same
experiment tree, for example:

- `experiment_results/baseline/px4_1/`
- `experiment_results/delay/px4_2/`

These traces currently capture:

- `auction/allocation`
- `auction/bid`
- `auction/local_state`

To summarize one experiment directory into table-ready files:

`python3 -m offboard_py.experiment_summary experiment_results/baseline`

Or in the ROS 2 workspace style after the workspace is sourced:

`ros2 run offboard_py experiment_summarizer experiment_results/baseline`

This writes:

- `<manifest_stem>_summary.json`
- `<manifest_stem>_summary.csv`

The CSV row includes the main paper-friendly fields:

- fault settings
- event counts
- namespace count
- total task switches
- runtime duration
- stabilization proxy time

To build a comparison report after all four profile summaries exist:

`ros2 run offboard_py experiment_reporter experiment_results/<batch_dir>`

This writes:

- `comparison.csv`
- `comparison_report.html`

To run a full batch automatically once PX4 `px4_1..px4_4` are online:

`ros2 run offboard_py experiment_batch_runner --duration-sec 60 --uav-count 4`

This creates a new batch directory under `experiment_results/`, runs
`baseline`, `delay`, `loss`, and `stress` in sequence, then writes:

- per-profile manifests
- per-profile summaries
- `comparison.csv`
- `comparison_report.html`

To aggregate multiple completed `batch_*` directories into repeated-trial
mean/std outputs:

`ros2 run offboard_py experiment_study_reporter experiment_results`

This writes:

- `study_comparison.csv`
- `study_comparison.json`
- `study_comparison_report.html`

To generate paper-ready tables and standalone figures from the repeated-study
CSV:

`ros2 run offboard_py experiment_paper_assets --study-csv experiment_results/study_comparison.csv --output-dir experiment_results/paper_assets`

This writes:

- `paper_results_table.md`
- `paper_results_table.tex`
- `paper_results_summary.md`
- `figure_total_events.svg`
- `figure_bid_events.svg`
- `figure_stabilization.svg`
- `figure_task_switches.svg`
- `paper_figures.html`

Useful launch overrides:

- `uav_count:=1`
- `namespace_prefix:=px4_`
- `uav_count:=3`
- `drop_probability:=0.2`
- `delay_mean_ms:=200`
- `delay_jitter_ms:=80`
- `use_fault_injection:=false`

By default the launch now targets PX4 DDS namespaces like `px4_1`, `px4_2`, ...
If your setup uses `uav1`, `uav2`, ... instead, override:

`namespace_prefix:=uav`

## Validation Status

- `colcon build --packages-select offboard_py`: passing
- `colcon test --packages-select offboard_py`: passing
- `test/test_auction_core.py`: covers sequence ordering, stale pruning, lock retention, and switch suppression
- `test/test_experiment_profiles.py`: covers fixed experiment configs, metadata writing, and launch module imports
- `stress` profile combines the current delay and loss settings for a stronger comparison
- `test/test_launch_surfaces.py`: guards the main launch argument surface and metrics recorder wiring
- `test/test_metrics_store.py`: covers JSONL metric persistence
- `test/test_experiment_summary.py`: covers result aggregation and summary file generation
- `test/test_task_board.py`: ensures popup tasks do not silently duplicate defaults
- `test/test_experiment_report.py`: covers comparison CSV and HTML report generation
- launch profiles compile and install with the package

## Latest 4-UAV Batch Result

- Batch root:
  `experiment_results/batch_20260304T140404Z`
- Comparison table:
  `experiment_results/batch_20260304T140404Z/comparison.csv`
- HTML report with inline bar charts:
  `experiment_results/batch_20260304T140404Z/comparison_report.html`

Current measured comparison from the 4-UAV run:

| profile | total_events | allocation_events | bid_events | local_state_events | total_task_switches | runtime_sec | stabilization_sec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 3570 | 1190 | 1190 | 1190 | 0 | 61.230193 | 0.807760 |
| delay | 3549 | 1184 | 1181 | 1184 | 3 | 61.226264 | 1.400154 |
| loss | 3284 | 1182 | 920 | 1182 | 0 | 59.827779 | 1.827905 |
| stress | 3294 | 1194 | 906 | 1194 | 2 | 61.273497 | 1.073516 |

Quick takeaways:

- `delay` increased task switching (`3`) and slowed stabilization versus `baseline`.
- `loss` reduced bid propagation most strongly (`920` bid events) and had the slowest stabilization.
- `stress` reduced bid traffic similarly to `loss`, but stabilized faster than `loss` in this run.

## Latest Repeated 4-UAV Study Result

- Aggregate table:
  `experiment_results/study_comparison.csv`
- Aggregate JSON:
  `experiment_results/study_comparison.json`
- Aggregate HTML report:
  `experiment_results/study_comparison_report.html`

This aggregate currently uses 3 valid 4-UAV batches:

- `batch_20260304T140404Z`
- `batch_20260304T142728Z`
- `batch_20260304T143351Z`

Current repeated-trial mean and standard deviation:

| profile | trials | total_events_mean | total_events_std | bid_events_mean | bid_events_std | task_switch_mean | task_switch_std | stabilization_mean_s | stabilization_std_s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 3 | 3570.00 | 9.00 | 1190.00 | 3.00 | 0.00 | 0.00 | 0.805408 | 0.004623 |
| delay | 3 | 3556.33 | 16.29 | 1183.00 | 5.29 | 1.67 | 1.15 | 1.072235 | 0.299183 |
| loss | 3 | 3298.33 | 22.28 | 925.00 | 6.24 | 0.67 | 1.15 | 1.348180 | 0.428052 |
| stress | 3 | 3284.00 | 22.72 | 902.67 | 7.57 | 1.33 | 1.15 | 0.904953 | 0.251027 |

Repeated-trial takeaways:

- `delay` raises mean stabilization time by about `33.13%` versus `baseline`.
- `loss` cuts mean bid propagation by about `22.27%` and raises stabilization by about `67.39%`.
- `stress` cuts mean bid propagation by about `24.15%`, but only raises stabilization by about `12.36%` versus `baseline`.

## Paper Asset Paths

- `experiment_results/paper_assets/paper_results_table.md`
- `experiment_results/paper_assets/paper_results_table.tex`
- `experiment_results/paper_assets/paper_results_summary.md`
- `experiment_results/paper_assets/figure_total_events.svg`
- `experiment_results/paper_assets/figure_bid_events.svg`
- `experiment_results/paper_assets/figure_stabilization.svg`
- `experiment_results/paper_assets/figure_task_switches.svg`
- `experiment_results/paper_assets/paper_figures.html`

## Working Agreement

- This file should reflect the current architecture and operator-facing usage.
- `Log.md` should be updated at the end of each work block with exact changes and next steps.
- `Memory.md` should only store long-lived rules, preferences, and repeatable workflow conventions.
