# Notice

The `dev-review` skill is adapted from the `code-review` skill in Matt Pocock's skills collection.

- **Upstream:** https://github.com/mattpocock/skills (`skills/engineering/code-review/SKILL.md`)
- **Commit:** `7739eae`
- **Licence:** MIT, reproduced in [LICENSE](LICENSE)
- **Write-up:** https://www.aihero.dev/skills-code-review

## What vague changed

- Renamed to `dev-review`, so it does not shadow Claude Code's built-in `/code-review`.
- Replaced the issue-tracker setup step with the `gh` CLI and the `plan-eng` plan as spec sources.
- Added the vague and project `CLAUDE.md` files to the standards sources.
- Added a rule that sub-agents never invoke skills, and a verification pass over every finding.
