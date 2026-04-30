---
name: vague-my-skill
version: 1.0.0
description: One-line description of what this skill does.
sdk_commands:
  - vague init
  - vague learnings-log
requires_slug: true
requires_planning: false
---

# My Skill

[Skill prompt content — instructions for the LLM]

## Steps

1. Init: `CONTEXT=$(vague init)`
2. Parse context:
```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
```
3. Do work...
4. Log learning:
```bash
vague learnings-log '{"skill":"my-skill","type":"pitfall","key":"...","insight":"...","confidence":7,"source":"observed","ts":"2024-01-01T00:00:00"}'
```
5. Log timeline:
```bash
vague timeline-log '{"skill":"my-skill","event":"completed","branch":"'"$BRANCH"'","session":"'"$SESSION_ID"'"}'
```
