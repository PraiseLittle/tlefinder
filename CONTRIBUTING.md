# Contributing

Use the toolchain owned by the component you change. Core and API are separate Poetry projects and must use the Python selected by global `pyenv`; GUI uses npm and the committed `gui/package-lock.json`.

## Dependency and ownership rules

- Core may import only Core modules and its declared runtime dependencies.
- API may consume public `tlefinder.core` imports but may not import GUI code.
- GUI calls API endpoints through `gui/src/api/client.ts`; it may not import or copy Python search logic.
- Do not add `core/src/tlefinder/__init__.py` or `api/src/tlefinder/__init__.py`; both distributions share the implicit `tlefinder` namespace.
- Tests, fixtures, `conftest.py` files, and private helpers remain inside their owning component.
- Core/API integration assertions belong to API. Browser/API contract assertions belong to GUI and use stubbed HTTP responses.

## Verification

Run `./scripts/verify.ps1` from the repository root for the full monorepo path. For focused changes, use the commands documented in `core/README.md`, `api/README.md`, or `gui/README.md`.

When dependency boundaries or shared repository configuration change, run all three component checks and inspect both Python wheels with `scripts/inspect_wheels.py`.

