# vague

Personal development workflow toolkit. `vague install` writes the skill routing table into each Claude profile's `CLAUDE.md`, between the `vague:start` and `vague:end` markers.

## Skills Location

Skills are in each Claude profile's `skills/` directory (each skill symlinked to this package's bundled `assets/skills/` by `vague install`). Edits to the bundled assets propagate live; re-run `vague install` only to add new runtimes or relink after reinstalling the package.

## State

All persistent state lives in `~/.vague/`. Never hardcode paths — always use `$VAGUE_HOME` or the default `~/.vague`.

## Testing

```bash
uv run pytest
```

## Development Best Practices

These conventions apply to **all** skills that touch code in a Python project. Skills like `/plan-eng`, `/dev-implement`, `/dev-ship`, and `/dev-investigate` should assume and enforce them.

### Environment: `uv`
- Always run Python commands through `uv` so they use the project's pinned environment:
  - `uv run pytest` for tests
  - `uv run python <script>` for scripts
  - `uv add <pkg>` / `uv remove <pkg>` for dependency changes (never edit `pyproject.toml` deps by hand if `uv` is available)
- Never rely on a globally-installed interpreter or a manually-activated venv when `uv` is present.

### Testing: `pytest` + TDD
- `pytest` is the test runner. New behavior gets a failing test **first**, then implementation (see `/plan-eng` Section 3).
- Run the full suite with `uv run pytest` before considering any task done.
- Use descriptive test names (`test_<behavior>_<condition>`). Test behavior, not implementation details.
- Prefer fixtures and factories over ad-hoc setup; keep them in `tests/conftest.py` or a dedicated `tests/fixtures/` module.

### Pre-commit
- Every repo should have a `.pre-commit-config.yaml`. If one doesn't exist, propose adding it before shipping non-trivial changes.
- Install hooks once per clone: `pre-commit install`.
- Before committing, run `pre-commit run --all-files` and fix everything it flags. Never bypass with `--no-verify` without an explicit reason logged in the commit body.
- CI should run the same hooks; local pre-commit failures must block the commit, not be deferred.

### Definition of Done
A change is only done when:
1. New/changed behavior has a test that fails without the change and passes with it.
2. `uv run pytest` is green.
3. `pre-commit run --all-files` is green.
4. The diff has been re-read for unrelated edits and dead code.
