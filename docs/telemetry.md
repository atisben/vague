# Telemetry

vague telemetry is **100% local**. Nothing is sent to any server.

---

## What Is Logged

### memory.jsonl
Written to `~/.vague/memory.jsonl` by `vague memory-log`. It is not telemetry: it holds what the model chose to remember. Each line is one memory with 8 fields: `ts`, `scope` (a project slug or `global`), `key`, `kind` (`learning` or `observation`), `text`, `files`, `skill` and `status`. Lines are only appended. A reader keeps the latest line per `scope` and `key`.

The preamble prints at most 1,500 tokens of it, for this scope plus `global`. Observations never load in the preamble. Only `/meta` reads them. It never leaves your machine.

### scratch/<scope>.jsonl
Written to `~/.vague/scratch/<scope>.jsonl` by `vague memory-log --scratch`. It uses the same record and the same fold as the ledger. Agents on one project share it, and notes older than 7 days are hidden from the preamble and from search.

### events/YYYY-MM.jsonl
Written to `~/.vague/events/YYYY-MM.jsonl` (one file per month, one JSON line per event). It records vague usage only: which skill started, and which memories a `vague` command served or wrote.

Skill starts come from `vague log-event`, which a Claude Code hook runs with the hook payload on stdin. Context events come from `vague` itself.

A skill started in a worktree:

```json
{"ts":"2026-11-11T11:37:37Z","session":"s1","event":"skill_start","cwd":"/Users/me/repo-wt","repo":"me-repo","branch":"feat/x","root":"/Users/me/repo-wt","main_root":"/Users/me/repo","is_worktree":true,"runtime":".claude-personal","skill":"dev-ship","source":"slash"}
```

Two memories served by `vague memory-search`:

```json
{"ts":"2026-11-11T11:38:02Z","session":"s1","event":"context_read","cwd":"/Users/me/repo-wt","repo":"me-repo","branch":"feat/x","root":"/Users/me/repo-wt","main_root":"/Users/me/repo","is_worktree":true,"runtime":".claude-personal","path":"memory.jsonl","command":"memory-search","ids":["me-repo/tests-need-docker","global/verify-subagent-claims"]}
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
| `context_read` | `vague` itself, not a hook | `path`, `command`, optional `ids` |
| `context_write` | `vague` itself, not a hook | `path`, `command`, optional `ids` |

`root` is the checkout or worktree path and `main_root` is the main checkout, so a worktree event links to its repo by `main_root` while `root` tells the worktrees apart. Outside a repo, or on a bare repo, both paths are `cwd`. Git resolves symlinks in these paths, so they may differ from `cwd` (`/private/var` vs `/var` on macOS). Use `main_root` for identity, not `repo`.

`context_read` and `context_write` record which state file a `vague` subcommand read or wrote: `memory.jsonl`, a `scratch/<scope>.jsonl`, `config.md`, or the assets directory for `skill-add`. For the ledger and scratchpads, `path` is the constant relative name (`memory.jsonl` or `scratch/<scope>.jsonl`). For other files, `path` is absolute and symlink-resolved. For memory, `ids` names the memories served or written. `command` is the subcommand name, for example `memory-log`. A reader links a skill to the context it pulled in and wrote back by joining on `session`.

- **No hook needed for context events.** Do not add one.
- **Outside Claude Code the session is `unknown`.** The `session` value comes from `$CLAUDE_CODE_SESSION_ID`, which Claude Code sets for its Bash tool and which equals the hook payload's `session_id`. A command run in a plain terminal or by another agent still writes its line, with `session: "unknown"`, so the usage graph stays complete.
- **`ids` names the memories.** The `memory-*` commands and the preamble add `ids`, a list of `scope/key` names of the memories served or written. Keys are names chosen by the model, never memory text or the memory's `files`.
- **Reads of a missing file are skipped,** and the same file is logged once per command and kind. `vague status` logs no reads: it serves no memory text.
- `telemetry: off` disables all events, and a failure to write one never changes a command's output or exit code.

#### Not logged

- Any project file path from a hook: Write, Edit, Read, Grep and Glob calls write nothing. Only a path a skill passes to `memory-log --files` is stored, in the ledger.
- File contents and tool output.
- Bash commands.
- Prompt text beyond the `/name` of a skill.
- Search patterns and queries.
- Session start, turn end and session end signals.

`vague log-event` ignores every other hook or tool silently. It never prints, never fails, and always exits 0.

#### Wiring the hook

A *hook* is a command Claude Code runs on an event and feeds a JSON payload on stdin. `vague log-event` is that command. `vague install` adds these hooks to `settings.json` in every Claude config dir it installs into (for example `~/.claude-personal/settings.json`). It is idempotent, keeps your other settings and hooks, and skips a file that is not valid JSON. `vague uninstall` removes only vague's hooks. The entry it writes:

```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "vague log-event" }] }],
    "PostToolUse": [{ "matcher": "Skill", "hooks": [{ "type": "command", "command": "vague log-event" }] }]
  }
}
```

The `PostToolUse` matcher limits the hook to Skill tool calls. The installer writes the absolute path of `vague` when it finds one, because a hook's `PATH` may not include it. A hook you added by hand is recognised, so nothing is duplicated.

#### Known limits

- **No skill-end signal.** No hook fires when a skill finishes. A reader infers the end: a run lasts until its last vague event or the next skill start.
- **Files a skill writes with Claude's own tools are not logged by any hook,** by design. A skill reports a file it wrote by passing `--files` to `vague memory-log`, and only then does the file reach the usage graph. The path may be inside the repo (stored repo-relative) or outside it (stored absolute, for example an Obsidian note). `vague ui` flags files under `~/Obsidian` (override with `VAGUE_VAULT`) and lists them in "Written to Obsidian". Only skills that choose to report appear.

---

## Configuration

```bash
vague config-set telemetry local   # log locally (default)
vague config-set telemetry off     # no logging at all
vague config-get telemetry         # check current value
```

When `telemetry` is `"off"`:
- `memory.jsonl` and the scratchpad are still written (they're structural, not telemetry)
- `vague log-event` writes nothing to `events/`

---

## What Is Never Logged

- File contents, Bash commands, tool output
- Any project file path, unless a vague skill reports it with `memory-log --files` (events carry only vague's own state and memory keys, as `context_read` / `context_write`)
- Grep and Glob patterns, and any search query
- Prompt text, except the skill name of a leading `/name`
- Code content
- User input or conversation text
- API keys, tokens, secrets
- Personal information
