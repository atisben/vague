---
name: vague-my-skill
version: 1.0.0
description: One-line description of what this skill does.
sdk_commands:
  - vague context
  - vague memory-log
requires_slug: true
---

# My Skill

[Skill prompt content — instructions for the LLM]

## Preamble

```bash
eval "$(vague context --shell --skill vague-my-skill)"
```

Always pass `--skill <name>`. The preamble prints this project's MEMORY
block, and `--skill` ranks this skill's memories first.

## Steps

1. Run the preamble above. It sets `$SLUG`, `$BRANCH`, `$PROACTIVE`, `$TELEMETRY` and prints the ranked memories.
2. Do work...
3. Log a learning, if one emerged. The preamble printed the command, so name only this skill's trigger here.

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about vague-my-skill` (see the Memory guideline).
