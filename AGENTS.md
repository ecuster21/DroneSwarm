# Repository Guidelines

## Project Structure & Module Organization
This repository is a ROS 2 workspace. Keep source packages under `src/`; treat `build/`, `install/`, and `log/` as generated output.

- `src/offboard_py/`: Python `ament_python` package for the offboard control node.
- `src/offboard_py/offboard_py/`: runtime module code, including `offboard_control.py`.
- `src/offboard_py/test/`: lint-style pytest checks (`test_flake8.py`, `test_pep257.py`, `test_copyright.py`).
- `src/px4_msgs/`: CMake-based `ament_cmake` interface package that generates ROS 2 message types from `.msg` files.

Do not hand-edit generated workspace artifacts. Avoid changing `src/px4_msgs/msg/*.msg` unless you are intentionally updating the vendored upstream definitions.

## Build, Test, and Development Commands
Run commands from the workspace root:

- `colcon build --packages-select px4_msgs offboard_py`: build both packages.
- `source install/setup.bash`: load the workspace overlay after a successful build.
- `colcon test --packages-select offboard_py`: run the Python package test suite and ament linters.
- `colcon test-result --verbose`: inspect failures after a test run.
- `ros2 run offboard_py offboard_control`: launch the offboard control node.

When iterating on Python only, rebuilding `offboard_py` is usually enough; rebuild `px4_msgs` after interface changes.

## Coding Style & Naming Conventions
Use 4-space indentation and follow standard ROS 2 Python conventions:

- `snake_case` for modules, functions, and topic helper methods.
- `CamelCase` for classes (for example, `OffboardControl`).
- Keep console entry points in `setup.py` aligned with module names.

`offboard_py` is checked by `ament_flake8` and `ament_pep257`, so keep code PEP 8 compliant and include docstrings where new public modules or functions need them.

## Testing Guidelines
Add tests under `src/offboard_py/test/` with names matching `test_*.py`. Prefer `colcon test` over raw `pytest` so ament linters and ROS 2 test hooks run together. New behavior changes should include at least one automated check or a documented manual validation path.

## Commit & Pull Request Guidelines
The workspace root does not currently include Git metadata, so no repository-wide history is available here. Use short, imperative commit subjects, consistent with the vendored `px4_msgs` history (for example, `Update offboard control retry logic`).

Pull requests should state which package changed, list validation steps (for example, `colcon build` and `colcon test`), and describe any PX4 or ROS 2 runtime assumptions. If a change affects flight behavior or topics, include a brief test scenario and expected vehicle response.
