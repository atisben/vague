# Telemetry

bastack telemetry is **100% local**. Nothing is sent to any server.

---

## What Is Logged

### skill-usage.jsonl
Written to `~/.bastack/analytics/skill-usage.jsonl` when `telemetry` is not `"off"`.

```json
{"skill": "ship", "ts": "2025-04-08T09:25:00Z", "repo": "owner-myrepo"}
```

Fields: `skill`, `ts` (ISO 8601), `repo` (slug — no absolute paths, no branch names in this file).

### timeline.jsonl
Written to `~/.bastack/projects/{slug}/timeline.jsonl` always (not gated by telemetry config).

```json
{"skill": "ship", "event": "started", "branch": "feat/auth", "session": "12345-1712566800", "ts": "..."}
{"skill": "ship", "event": "completed", "branch": "feat/auth", "session": "12345-1712566800", "outcome": "success", "ts": "..."}
```

Timeline data is used locally by `/retro` to track plan completion and session duration. It never leaves your machine.

### learnings.jsonl
Written to `~/.bastack/projects/{slug}/learnings.jsonl` when a skill calls `bs-learnings-log`.

Contains your project's accumulated engineering insights. Never leaves your machine.

---

## Configuration

```bash
bs-config set telemetry local   # log locally (default)
bs-config set telemetry off     # no logging at all
bs-config list                  # check current config
```

When `telemetry` is `"off"`:
- `skill-usage.jsonl` is NOT written
- `bs-analytics` will show no data
- Timeline and learnings are still written (they're structural, not telemetry)

---

## What Is Never Logged

- File paths (beyond the project slug)
- Code content
- User input or conversation text
- API keys, tokens, secrets
- Personal information
