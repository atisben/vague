# Telemetry

vague telemetry is **100% local**. Nothing is sent to any server.

---

## What Is Logged

### skill-usage.md
Written to `~/.vague/analytics/skill-usage.md` when `telemetry` is not `"off"`.

```yaml
---
entries:
  - skill: ship
    ts: "2025-04-08T09:25:00Z"
    repo: owner-myrepo
---
```

Fields: `skill`, `ts` (ISO 8601), `repo` (slug — no absolute paths, no branch names).

### timeline.md
Written to `~/.vague/projects/{slug}/timeline.md` by skills via `vague timeline-log`.

```yaml
---
entries:
  - skill: ship
    event: started
    branch: feat/auth
    session: "12345-1712566800"
    ts: "2025-04-08T09:00:00Z"
  - skill: ship
    event: completed
    branch: feat/auth
    session: "12345-1712566800"
    outcome: success
    ts: "2025-04-08T09:25:00Z"
---
```

Timeline data is used locally by `/retro` to track session history and skill usage patterns. It never leaves your machine.

### learnings.md
Written to `~/.vague/projects/{slug}/learnings.md` when a skill calls `vague learnings-log`.

Contains your project's accumulated engineering insights. Surfaced automatically by `vague init` at the start of every skill invocation. Never leaves your machine.

---

## Configuration

```bash
vague config-set telemetry local   # log locally (default)
vague config-set telemetry off     # no logging at all
vague config-get telemetry         # check current value
```

When `telemetry` is `"off"`:
- `skill-usage.md` is NOT written
- `vague analytics-show` will show no data
- Timeline and learnings are still written (they're structural, not telemetry)

---

## What Is Never Logged

- File paths (beyond the project slug)
- Code content
- User input or conversation text
- API keys, tokens, secrets
- Personal information
