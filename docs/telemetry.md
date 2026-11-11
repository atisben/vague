# Telemetry

vague telemetry is **100% local**. Nothing is sent to any server.

---

## What Is Logged

### project.md
Written to `~/.vague/projects/{slug}/project.md` by `vague context --skill`.
Records the repo's **absolute path on your machine** and a `last_seen`
timestamp — this is what lets `vague status` run git checks across projects.
Structural state (like timeline), so it is written even when `telemetry` is
`"off"`. Delete the file to forget a project's location.

### timeline.md
Written to `~/.vague/projects/{slug}/timeline.md` by skills via `vague timeline-log`.

```yaml
---
entries:
  - skill: dev-ship
    event: started
    branch: feat/auth
    session: "12345-1712566800"
    ts: "2025-04-08T09:00:00Z"
  - skill: dev-ship
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

### events/YYYY-MM.jsonl
Written to `~/.vague/events/YYYY-MM.jsonl` (one file per month, one JSON line per event). It records vague usage only: which skill started, and which vague state file a `vague` command read or wrote.

Skill starts come from `vague log-event`, which a Claude Code hook runs with the hook payload on stdin. Context events come from `vague` itself.

A skill started in a worktree:

```json
{"ts":"2026-11-11T11:37:37Z","session":"s1","event":"skill_start","cwd":"/Users/me/repo-wt","repo":"me-repo","branch":"feat/x","root":"/Users/me/repo-wt","main_root":"/Users/me/repo","is_worktree":true,"runtime":".claude-personal","skill":"dev-ship","source":"slash"}
```

A state file read by `vague learnings-search`:

```json
{"ts":"2026-11-11T11:38:02Z","session":"s1","event":"context_read","cwd":"/Users/me/repo-wt","repo":"me-repo","branch":"feat/x","root":"/Users/me/repo-wt","main_root":"/Users/me/repo","is_worktree":true,"runtime":".claude-personal","path":"/Users/me/.vague/projects/me-repo/learnings.md","command":"learnings-search"}
```

Fields on every event:

| Field | Meaning |
|---|---|
| `ts` | UTC timestamp |
| `session` | Claude Code session id |
| `event` | `skill_start`, `context_read` or `context_write` |
| `cwd` | Working directory of the call |
| `repo` | Label from the `origin` URL, shared by all worktrees |
| `branch` | Current branch, or `unknown` |
| `root` | Git toplevel of `cwd` (the checkout or worktree path) |
| `main_root` | Main checkout, the identity of the repo |
| `is_worktree` | True for a linked worktree |
| `runtime` | Basename of `$CLAUDE_CONFIG_DIR`, else `claude` |

Fields that depend on the event:

| `event` | Written by | Extra fields |
|---|---|---|
| `skill_start` | Hook: PostToolUse on the Skill tool, or a prompt starting with `/name` | `skill`, `source` (`tool` or `slash`), `agent_id` when a subagent made the call |
| `context_read` | `vague` itself, not a hook | `path`, `command` |
| `context_write` | `vague` itself, not a hook | `path`, `command` |

`root` is the checkout or worktree path and `main_root` is the main checkout, so a worktree event links to its repo by `main_root` while `root` tells the worktrees apart. Outside a repo, or on a bare repo, both paths are `cwd`. Git resolves symlinks in these paths, so they may differ from `cwd` (`/private/var` vs `/var` on macOS). Use `main_root` for identity, not `repo`.

`context_read` and `context_write` record which state file a `vague` subcommand read or wrote (`learnings.md`, `observations.md`, `timeline.md`, `project.md`, `config.md`, planning files, and the assets directory for `skill-add`). `path` is absolute and symlink-resolved. `command` is the subcommand name, for example `learnings-log`. A reader links a skill to the context it pulled in and wrote back by joining on `session`.

- **No hook needed for context events.** Do not add one.
- **Outside Claude Code nothing is logged.** The `session` value comes from `$CLAUDE_CODE_SESSION_ID`, which Claude Code sets for its Bash tool and which equals the hook payload's `session_id`. A command run in a plain terminal writes no line.
- **Reads of a missing file are skipped,** and the same file is logged once per command and kind. `vague status` logs at most 50 reads per call.
- `telemetry: off` disables all events, and a failure to write one never changes a command's output or exit code.

#### Not logged

- Any project file path: Write, Edit, Read, Grep and Glob calls write nothing.
- File contents and tool output.
- Bash commands.
- Prompt text beyond the `/name` of a skill.
- Search patterns and queries.
- Session start, turn end and session end signals.

`vague log-event` ignores every other hook or tool silently. It never prints, never fails, and always exits 0.

#### Wiring the hook

A *hook* is a command Claude Code runs on an event and feeds a JSON payload on stdin. `vague log-event` is that command. `vague install` does **not** add the hooks yet, so add them by hand to `settings.json` in your Claude config dir (for example `~/.claude-personal/settings.json`):

```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "vague log-event" }] }],
    "PostToolUse": [{ "matcher": "Skill", "hooks": [{ "type": "command", "command": "vague log-event" }] }]
  }
}
```

The `PostToolUse` matcher limits the hook to Skill tool calls. If `vague` is not on the hook's `PATH`, use the absolute path, for example `~/.local/bin/vague log-event`.

#### Known limits

- **No skill-end signal.** No hook fires when a skill finishes. A reader infers the end: a run lasts until its last vague event or the next skill start.
- **Files a skill writes with Claude's own tools are not logged,** by design. Only vague's own state files appear.

---

## Configuration

```bash
vague config-set telemetry local   # log locally (default)
vague config-set telemetry off     # no logging at all
vague config-get telemetry         # check current value
```

When `telemetry` is `"off"`:
- Timeline, learnings, and project.md are still written (they're structural, not telemetry)
- `vague log-event` writes nothing to `events/`

---

## What Is Never Logged

- File contents, Bash commands, tool output
- Any project file path (only vague's own state files appear, as `context_read` / `context_write`)
- Grep and Glob patterns, and any search query
- Prompt text, except the skill name of a leading `/name`
- Code content
- User input or conversation text
- API keys, tokens, secrets
- Personal information
