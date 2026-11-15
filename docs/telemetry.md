# Telemetry

vague telemetry is **100% local**. Nothing is sent to any server. This page is the one place that says what vague records, what it never records, and how to turn each part off.

| Record | File | On by default | Turn it off |
|---|---|---|---|
| Memories | `~/.vague/memory.jsonl` | Yes, it is state, not telemetry | n/a |
| Usage events | `~/.vague/events/YYYY-MM.jsonl` | Yes | `vague config-set telemetry off` |
| Debug log | `~/.vague/logs/vague.log` | No | Leave `VAGUE_LOG` unset |

---

## What Is Logged

### memory.jsonl
Written to `~/.vague/memory.jsonl` by `vague memory-log`. It is not telemetry: it holds what the model chose to remember. Each line is one memory with 8 fields: `ts`, `scope` (a project slug or `global`), `key`, `kind` (`learning`, `observation`, `note` or `doc`), `text`, `files`, `skill` and `status`. Lines are only appended. A reader keeps the latest line per `scope` and `key`.

The four kinds share the ledger:

| Kind | Written with | Lifetime |
|---|---|---|
| `learning` | `vague memory-log <key> "<fact>"` | Forever |
| `observation` | `--about <skill>` | Until `/retro` actions it |
| `note` | `--scratch`: a working note agents on one project share | Hidden from the preamble and from search after 7 days |
| `doc` | `--doc --files <absolute path>`: a pointer to a document a skill wrote | Forever |

The preamble prints at most 1,500 tokens of it, for this scope plus `global`, including the newest 5 `doc` pointers. Observations never load in the preamble. Only `/retro` reads them. It never leaves your machine.

### events/YYYY-MM.jsonl
Written to `~/.vague/events/YYYY-MM.jsonl` (one file per month, one JSON line per event). It records vague usage only: which skill started, which files Claude wrote while a skill ran, and which memories a `vague` command served or wrote.

Skill starts and file writes come from `vague log-event`, which a Claude Code hook runs with the hook payload on stdin. No agent has to cooperate, so no model can skip the step. Context events come from `vague` itself. Capture is best-effort: a failed write is swallowed, and the command's output still prints.

`vague status` reads these events back: each project's path and last activity, plus git checks across all your projects. `/triage` runs it as its first step.

A skill started in a worktree:

```json
{"ts":"2026-11-11T11:37:37Z","session":"s1","event":"skill_start","cwd":"/Users/me/repo-wt","repo":"me-repo","branch":"feat/x","root":"/Users/me/repo-wt","main_root":"/Users/me/repo","is_worktree":true,"runtime":".claude-personal","skill":"dev-ship","source":"slash"}
```

A file Claude wrote while `dev-ship` was the latest skill of the session:

```json
{"ts":"2026-11-11T11:37:50Z","session":"s1","event":"file_write","cwd":"/Users/me/repo-wt","repo":"me-repo","branch":"feat/x","root":"/Users/me/repo-wt","main_root":"/Users/me/repo","is_worktree":true,"runtime":".claude-personal","skill":"dev-ship","path":"/Users/me/repo-wt/CHANGELOG.md"}
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
| `event` | `skill_start`, `file_write`, `context_read` or `context_write` |
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
| `file_write` | Hook: PostToolUse on Write or Edit, only after a skill started in the same session | `skill` (the latest skill started in the session), `path` (absolute, symlink-resolved) |
| `context_read` | `vague` itself, not a hook | `path`, `command`, optional `ids` |
| `context_write` | `vague` itself, not a hook | `path`, `command`, optional `ids` |

`root` is the checkout or worktree path and `main_root` is the main checkout, so a worktree event links to its repo by `main_root` while `root` tells the worktrees apart. Outside a repo, or on a bare repo, both paths are `cwd`. Git resolves symlinks in these paths, so they may differ from `cwd` (`/private/var` vs `/var` on macOS). Use `main_root` for identity, not `repo`.

`context_read` and `context_write` record which state file a `vague` subcommand read or wrote: `memory.jsonl` or `config.env`. For the ledger, `path` is the constant relative name `memory.jsonl`. For other files, `path` is absolute and symlink-resolved. For memory, `ids` names the memories served or written. `command` is the subcommand name, for example `memory-log`. A reader links a skill to the context it pulled in and wrote back by joining on `session`.

`file_write` names the path Claude wrote with its Write or Edit tool, never the contents. A skill sends no end signal, so the last skill started in the session owns every later write. A write in a session with no skill start logs nothing. The hook reads only the current month file to find that skill, so a session that crosses a month boundary loses attribution.

- **No hook needed for context events.** Do not add one.
- **Outside Claude Code the session is `unknown`.** The `session` value comes from `$CLAUDE_CODE_SESSION_ID`, which Claude Code sets for its Bash tool and which equals the hook payload's `session_id`. A command run in a plain terminal or by another agent still writes its line, with `session: "unknown"`, so the usage graph stays complete.
- **`ids` names the memories.** The `memory-*` commands and the preamble add `ids`, a list of `scope/key` names of the memories served or written. Keys are names chosen by the model, never memory text or the memory's `files`.
- **Reads of a missing file are skipped,** and the same file is logged once per command and kind. `vague status` logs no reads: it serves no memory text.
- `telemetry=off` disables all events, and a failure to write one never changes a command's output or exit code.

`vague log-event` ignores every other hook or tool silently. It never prints to stdout and exits 0 on any failure, with one exception covered in the next section.

#### Skill check on skill edits

When a Write or Edit touches a file inside a bundled skill (`vague/assets/skills/<name>/`), `vague log-event` also runs the `vague skill-check` rules on that skill. The hook resolves symlinks first, so an edit through the installed link (`~/.claude-personal/skills/<name>`) is checked too. A `SKILL.md` anywhere else on disk is never checked.

| Result | What the hook does |
|---|---|
| No findings | Prints nothing, exits 0 |
| Findings | Prints them to stderr, exits 2 |
| The check itself fails | Logs a warning to the vague log, exits 0 |

Exit code 2 makes Claude Code hand stderr back to Claude, so Claude sees the findings and can fix the skill in the same turn. The stderr output for one finding:

```
vague skill-check: 1 finding(s) in retro
/Users/me/vague/vague/assets/skills/retro/SKILL.md: frontmatter: missing required field `description`
```

The check runs even with `telemetry=off`, because it is a guard, not telemetry. The event is still logged first, so a failing check never drops the `file_write` line.

#### Design check while /impeccable runs

`/impeccable` declares its own `PostToolUse` hook in its frontmatter, so the hook exists only in a session that invoked the skill. It runs `vague design-check --hook` on each UI file Claude edits, scans for eight AI-design tells, and returns findings the same way: stderr and exit 2. It records nothing. Run `vague design-check <paths>` to scan by hand.

#### Wiring the hook

A *hook* is a command Claude Code runs on an event and feeds a JSON payload on stdin. `vague log-event` is that command. `vague install` adds these hooks to `settings.json` in every Claude config dir it installs into (for example `~/.claude-personal/settings.json`). It is idempotent, keeps your other settings and hooks, and skips a file that is not valid JSON. `vague uninstall` removes only vague's hooks. The entry it writes:

```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "vague log-event" }] }],
    "PostToolUse": [{ "matcher": "Skill|Write|Edit", "hooks": [{ "type": "command", "command": "vague log-event" }] }]
  }
}
```

The `PostToolUse` matcher `Skill|Write|Edit` limits the hook to Skill, Write and Edit tool calls. Re-running `vague install` replaces an older `Skill`-only matcher. The installer writes the absolute path of `vague` when it finds one, because a hook's `PATH` may not include it. A hook you added by hand is recognised, so nothing is duplicated.

#### Known limits

- **No skill-end signal.** No hook fires when a skill finishes. A reader infers the end: a run lasts until its last vague event or the next skill start.
- **Only Write and Edit count as file writes.** A file a skill creates through Bash or NotebookEdit logs no `file_write` event. A skill can still report such a file with `vague memory-log <key> "<summary>" --doc --files <path>`, and the file then reaches the usage graph. The path may be inside the repo (stored repo-relative) or outside it (stored absolute, for example an Obsidian note). `vague ui` flags files under `~/Obsidian` (override with `VAGUE_VAULT`) and lists them in "Written to Obsidian". Only skills that choose to report appear.

---

## Configuration

```bash
vague config-set telemetry local   # log locally (default)
vague config-set telemetry off     # no logging at all
vague config-get telemetry         # check current value
# config-set writes one line, telemetry=<value>, in ~/.vague/config.env
```

When `telemetry` is `"off"`:
- `memory.jsonl` is still written, notes and doc pointers included (it is structural, not telemetry)
- `vague log-event` writes nothing to `events/`
- `vague log-event` still runs the skill check on bundled skill edits

---

## Debug Log

`vague` can log every command it runs (name, duration, exit code) plus any internal errors that would otherwise be swallowed. It is **off by default**. Turn it on with the `VAGUE_LOG` environment variable:

```bash
export VAGUE_LOG=debug   # debug | info | warning | error (unset = off)
```

Logs go to a rotating file, `~/.vague/logs/vague.log` (1 MB, 3 backups). A file is the right sink: each skill step spawns a short-lived `vague` process, and the runtime captures its stderr into the model's context. The file persists across those calls, so you can watch one stream:

```bash
tail -f ~/.vague/logs/vague.log
```

```text
2026-06-04 14:45:19 pid=19944 INFO vague start command=context
2026-06-04 14:45:19 pid=19944 INFO vague end command=context exit=0 duration_ms=26.6
```

Set `VAGUE_LOG` in your shell profile so every `vague` process the agent spawns inherits it. When you run `vague` by hand, add `VAGUE_LOG_STDERR=1` to echo the log to your terminal too.

---

## What Is Never Logged

- File contents, code, tool output, and what a Write or Edit wrote
- Any project file path outside a skill run: a Write or Edit with no earlier skill start in the session writes nothing. During a skill, only the path of a file Claude writes with Write or Edit is logged, as `file_write`. A skill can also report a path with `memory-log --files`.
- Read, Grep and Glob calls, at any time, and the paths of files Claude only reads
- Bash commands
- Search patterns and queries
- Prompt text, except the skill name of a leading `/name`
- Session start, turn end and session end signals
- User input or conversation text
- API keys, tokens, secrets, and personal information
