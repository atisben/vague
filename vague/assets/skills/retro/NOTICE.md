# Notice

The `retro` skill merges the `retro` skill from Matt Pocock's skills collection into vague's former `meta` skill. It replaces vague's earlier weekly commit-statistics `/retro`, which was retired.

- **Upstream:** https://github.com/mattpocock/skills (`skills/engineering/retro/SKILL.md`)
- **Commit:** `a7d038f`
- **Licence:** MIT, reproduced in [LICENSE](LICENSE)
- **Write-up:** https://www.aihero.dev/skills-retro

## What vague kept from `meta`

- The observation ledger as an input, the user picking what to apply, and `vague skill-check` after each edit.
- Scaffolding new skills from `new-skill-` observations.
- Memory curation: duplicates, cross-project facts, dead paths.

## What vague changed

- The session log is read with `jq` filters, from the Claude Code projects directory.
- A **Skill defect** category joins upstream's seven, fed by observations.
- Mechanical fixes in the vague repo become rules in `vague/skill_rules.py`.
- Judgement-call standards go where `/dev-review` reads them.
- Upstream's `writing-for-agents` step is dropped: vague's guidelines carry the writing rules.
