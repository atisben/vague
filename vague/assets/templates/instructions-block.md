# vague

Personal development workflow toolkit. 21 skills for the full software development lifecycle.

## Skill Routing

When the user's request matches a skill below, invoke it using the Skill tool as your FIRST action. Do NOT answer directly first.

| Trigger | Skill |
|---------|-------|
| "what should I look at", "here's what's on my plate", "where do I start", "triage this" | `/ops-triage` |
| "I have an idea", "is this worth building", "help me think through this" | `/plan-ideation` |
| "think bigger", "expand scope", "strategy review", "is this ambitious enough" | `/plan-ceo` |
| "review the architecture", "engineering review", "lock in the plan" | `/plan-eng` |
| "design system", "brand guidelines", "create DESIGN.md" | `/design-consultation` |
| "explore designs", "show me options", "design variants", "visual brainstorm" | `/design-shotgun` |
| "finalize this design", "turn this into HTML", "build me a page" | `/design-html` |
| "audit the design", "visual QA", "check if it looks good", "design polish" | `/design-review` |
| "ship", "deploy", "push to main", "create a PR", code is ready | `/dev-ship` |
| "review this PR", "code review", "pre-landing review", "check my diff" | `/dev-review` |
| "debug this", "fix this bug", "why is this broken", error / stack trace | `/dev-investigate` |
| "what have we learned", "show learnings", "prune learnings" | `/ops-learn` |
| "weekly retro", "what did we ship", "engineering retrospective" | `/ops-retro` |
| "develop this", "build this feature", "implement this", "orchestrate" | `/dev-develop` |
| "improve skills", "meta review", "skill improvement", "review observations" | `/ops-meta` |
| "save to vault", "note this down", "save this note", "search the vault", "find in vault", "recall from vault" | `/ops-vault` |
| "interview prep", "job hunting", "start interview coaching" | `/iv-kickoff` |
| "research {company}", "decode this JD", "is this role a fit" | `/iv-research` |
| "build stories", "storybank", "story gaps", "retrieval drill" | `/iv-stories` |
| "practice interview", "mock interview", "drill", "debrief" | `/iv-practice` |
| "interview progress", "how am I doing", "readiness check" | `/iv-progress` |

## State

All persistent state lives in `~/.vague/`. Never hardcode paths — always use `$VAGUE_HOME` or the default `~/.vague`.
