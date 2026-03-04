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

- `experiment_results/baseline/uav1/`
- `experiment_results/delay/uav2/`

These traces currently capture:

- `auction/allocation`
- `auction/bid`
- `auction/local_state`

To summarize one experiment directory into table-ready files:

`python3 -m offboard_py.experiment_summary experiment_results/baseline`

Or after the workspace is sourced:

`experiment_summarizer experiment_results/baseline`

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

Useful launch overrides:

- `uav_count:=3`
- `drop_probability:=0.2`
- `delay_mean_ms:=200`
- `delay_jitter_ms:=80`
- `use_fault_injection:=false`

## Validation Status

- `colcon build --packages-select offboard_py`: passing
- `colcon test --packages-select offboard_py`: passing
- `test/test_auction_core.py`: covers sequence ordering, stale pruning, lock retention, and switch suppression
- `test/test_experiment_profiles.py`: covers fixed experiment configs, metadata writing, and launch module imports
- `stress` profile combines the current delay and loss settings for a stronger comparison
- `test/test_launch_surfaces.py`: guards the main launch argument surface and metrics recorder wiring
- `test/test_metrics_store.py`: covers JSONL metric persistence
- `test/test_experiment_summary.py`: covers result aggregation and summary file generation
- launch profiles compile and install with the package

## Working Agreement

- This file should reflect the current architecture and operator-facing usage.
- `Log.md` should be updated at the end of each work block with exact changes and next steps.
- `Memory.md` should only store long-lived rules, preferences, and repeatable workflow conventions.
