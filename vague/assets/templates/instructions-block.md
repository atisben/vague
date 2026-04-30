# vague

Personal development workflow toolkit. 13 skills for the full software development lifecycle.

## Skill Routing

When the user's request matches a skill below, invoke it using the Skill tool as your FIRST action. Do NOT answer directly first.

| Trigger | Skill |
|---------|-------|
| "I have an idea", "is this worth building", "help me think through this" | `/office-hours` |
| "think bigger", "expand scope", "strategy review", "is this ambitious enough" | `/plan-ceo-review` |
| "review the architecture", "engineering review", "lock in the plan" | `/plan-eng-review` |
| "design system", "brand guidelines", "create DESIGN.md" | `/design-consultation` |
| "explore designs", "show me options", "design variants", "visual brainstorm" | `/design-shotgun` |
| "finalize this design", "turn this into HTML", "build me a page" | `/design-html` |
| "audit the design", "visual QA", "check if it looks good", "design polish" | `/design-review` |
| "ship", "deploy", "push to main", "create a PR", code is ready | `/ship` |
| "review this PR", "code review", "pre-landing review", "check my diff" | `/review` |
| "debug this", "fix this bug", "why is this broken", error / stack trace | `/investigate` |
| "what have we learned", "show learnings", "prune learnings" | `/learn` |
| "weekly retro", "what did we ship", "engineering retrospective" | `/retro` |
| "save to vault", "note this down", "save this note", "search the vault", "find in vault", "recall from vault" | `/vault` |

## State

All persistent state lives in `~/.vague/`. Never hardcode paths — always use `$VAGUE_HOME` or the default `~/.vague`.
