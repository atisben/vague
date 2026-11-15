# Notice

The `dev-implement` skill merges two skills from Matt Pocock's skills collection into vague's former `dev-develop` skill.

- **Upstream:** https://github.com/mattpocock/skills
  - `skills/engineering/implement/SKILL.md` at commit `6d6a5b9`: the inline path, test-first at seams, and the commit before review.
  - `skills/engineering/implement-spec/SKILL.md` at commit `a496f55`: the task graph and frontier, context pointers, one worktree and one fresh implementer per ticket, the merger subagent, and the final review with one fresh fixer.
- **Licence:** MIT, reproduced in [LICENSE](LICENSE)
- **Write-ups:** https://www.aihero.dev/skills-implement and https://www.aihero.dev/skills-implement-spec

## What vague kept from `dev-develop`

- The `plan-eng` plan as the default input, and the user approving the graph.
- The deviation rules R1 to R4.
- Passing memory to subagents, and `--scratch` notes between them.

## What vague changed

- One skill with a size gate, instead of two skills.
- `/dev-review` replaces upstream's `code-review`. Baseline smells go to the user before any fix.
- Worktrees are created with `git worktree add`, so the skill does not depend on one runtime.
- No issue-tracker setup step. Tickets come from `gh` or `glab`. Closing tickets and the PR stay with `/dev-ship`.
