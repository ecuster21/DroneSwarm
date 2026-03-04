# Project Memory

## Long-Lived Rules

- Keep project-level status in `README.md` accurate when architecture or operator workflow changes.
- Append a closing summary to `Log.md` at the end of each work block:
  what was done, which files changed, and what comes next.
- Store only durable guidance in `Memory.md`; do not use it for temporary plans or one-off notes.

## User Preferences

- The user wants persistent project documentation inside the workspace root.
- The user is using this workspace both for implementation and for paper-oriented research iteration.
- Work should continue forward after documentation updates instead of stopping at documentation only.

## Repository Conventions

- Treat this repository as a ROS 2 workspace rooted at `/home/jie/px4_ros_com_ws`.
- Keep source edits under `src/`; do not hand-edit generated `build/`, `install/`, or `log/` artifacts.
- Avoid changing `src/px4_msgs/msg/*.msg` unless intentionally updating vendored upstream message definitions.
- For `offboard_py`, keep Python code PEP 8 compliant and compatible with the existing ament lint tests.

## Current Naming / Structure Conventions

- New ROS 2 execution-layer logic for the auction prototype belongs in `src/offboard_py/offboard_py/`.
- Launch files belong in `src/offboard_py/launch/`.
- Use `snake_case` for modules, functions, topics, and parameters.
- Keep the current topic naming pattern:
  `/task_board/tasks`, `auction/local_state`, `auction/bid_raw`, `auction/bid`, `auction/allocation`, `mission_setpoint`.

## Current Workflow

- Prefer implementing the smallest runnable increment, then validate with `colcon build` and `colcon test`.
- When adding runtime features, also add at least one focused automated check if it can be tested without full PX4 SITL.
- Keep the algorithm layer separate from `offboard_control`; `offboard_control` should stay focused on PX4 setpoint execution.
