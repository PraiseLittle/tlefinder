# Phase 1 - Repo Preparation and TDD Guardrails

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Prepare the repository for a test-first implementation of the new application described by `ARCHITECTURE.md` and `REQUIREMENT.md`.

## Tasks

- [x] Freeze the new-application structure before writing feature code.
  - [x] Use `tlefinder` as the new application root.
  - [x] Create the Python source tree under `tlefinder/src`.
  - [x] Create the target core package under `tlefinder/src/tlefinder/core`.
  - [x] Keep all new application code in the new `tlefinder` package.
- [x] Create the target test structure before adding new implementation code.
  - [x] Create `tlefinder/tests/unit` and `tlefinder/tests/fixtures`.
  - [x] Add `tlefinder/tests/conftest.py` with shared factories for station data, search windows, and search criteria.
  - [x] Add a first discovery test proving that the future core package can be imported without Flask.
- [x] Upgrade the development toolchain for repeatable test-first work.
  - [x] Use the Python version selected by global `pyenv` configuration.
  - [x] Manage dependencies and commands with Poetry.
  - [x] Create the new application project metadata under `tlefinder/pyproject.toml`.
  - [x] Add or confirm the dev dependencies needed by the architecture: `pytest`, `pytest-cov`, `freezegun`, and `respx`.
  - [x] Add explicit runtime dependencies that are part of the target core but not yet declared, especially `numpy` and `httpx` if chosen for TLE retrieval.
  - [x] Configure `pytest` collection, markers, and a default command for local execution.
- [x] Define the first expected behaviors before implementation starts.
  - [x] Add a minimal import test for the new `tlefinder` package.
  - [x] Add placeholder tests for the shared request and response models.
  - [x] Add placeholder tests for the first core validation rules that will be implemented in phase 2.
- [x] Prepare the repository layout for the later phases.
  - [x] Create placeholder modules matching the architecture: `models.py`, `errors.py`, `validation.py`, `time_utils.py`, `tle_repository.py`, `pass_analysis.py`, `filtering.py`, `scoring.py`, `ranking.py`, and `engine.py`.
  - [x] Add package `__init__.py` files where needed.
  - [x] Keep placeholders import-safe so `pytest` can run before the modules are implemented.

## Done When

- [x] `pytest` discovers the new test layout successfully.
- [x] The future core package exists under `tlefinder/src/tlefinder/core`.
- [x] No phase 1 task depends on behavior from a pre-existing prototype.
