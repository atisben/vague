---
name: vague-my-skill
version: 1.0.0
description: One-line description of what this skill does.
sdk_commands:
  - vague context
  - vague learnings-log
requires_slug: true
requires_planning: false
---

# My Skill

[Skill prompt content — instructions for the LLM]

## Preamble

```bash
eval "$(vague context --shell --skill vague-my-skill)"
```

Always pass `--skill <name>` — it records the usage event that feeds
`vague status`, `vague analytics-show`, and `/ops-retro`.

## Steps

1. Run the preamble above — it sets `$SLUG`, `$BRANCH`, `$PROACTIVE`, `$TELEMETRY`.
2. Do work...
3. Log learning:
```bash
vague learnings-log '{"skill":"my-skill","type":"pitfall","key":"...","insight":"...","confidence":7,"source":"observed","ts":"2024-01-01T00:00:00"}'
```
4. Log timeline:
```bash
vague timeline-log '{"skill":"my-skill","event":"completed","branch":"'"$BRANCH"'","session":"'"$SESSION_ID"'"}'
```
