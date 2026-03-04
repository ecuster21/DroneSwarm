# Repository Guidelines

## Project Structure & Module Organization
`gcaa/` is the main Python package. Keep core simulation and allocation logic in `gcaa/core/`, greedy auction routines in `gcaa/algorithms/`, and shared helpers in `gcaa/tools/`. Put Python tests in `gcaa/tests/` and name them alongside the module they cover. Treat `gcaa/simulations/` as generated output, not hand-edited source. `docs/` contains installation notes, `scripts/` contains release helpers, and `matlab/`, `paper/`, `img/`, and `mov/` are research and documentation assets rather than the primary Python development surface.

## Build, Test, and Development Commands
Create an isolated environment first, then install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Use `pip install .['all']` when you need the full development and testing toolchain used in CI. Run the default test suite with `pytest gcaa`. Match CI with `pytest gcaa --cov=gcaa --cov-branch --cov-report=xml --cov-config=coverage.conf`. During iteration, `pytest gcaa -m "not slow"` skips tests marked `slow`.

## Coding Style & Naming Conventions
Target Python 3.11+ and follow standard PEP 8 conventions: 4-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and concise docstrings where behavior is not obvious. The project declares `black`, `isort`, and `flake8` as development tools; run them before opening a PR if you touched Python code. Prefer small, focused functions and keep NumPy-heavy logic explicit rather than overly compact.

## Testing Guidelines
This repository uses `pytest` with doctests enabled (`--doctest-modules`). Add or update tests in `gcaa/tests/` for every bug fix or feature change, and use the `test_<feature>.py` / `test_<behavior>()` naming pattern already in the suite. CI enforces coverage reporting and currently fails below 5% overall coverage; new work should include meaningful assertions instead of relying on that low floor.

## Commit & Pull Request Guidelines
This checkout does not include `.git` history, so commit style cannot be verified locally. Use short, imperative commit subjects such as `Fix task completion indexing`, keep each commit scoped to one logical change, and add context in the body when needed. Follow `.github/PULL_REQUEST_TEMPLATE.md`: link the issue when applicable, confirm tests were added and passed, and include a concise description of the behavior change.
