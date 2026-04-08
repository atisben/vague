#!/usr/bin/env bash
# _preamble.sh — shared bastack preamble, sourced by every SKILL.md
#
# After sourcing, the following are available:
#   $SLUG        — sanitized project slug (from git remote or dirname)
#   $BRANCH      — current git branch
#   $PROACTIVE   — "true" | "false"
#   $TELEMETRY   — "local" | "off"
#   $SESSION_ID  — unique session identifier
#
# Env override: BASTACK_HOME (default: ~/.bastack)

BASTACK_HOME="${BASTACK_HOME:-$HOME/.bastack}"
_BS_BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../bin" && pwd)"

# 1. Session tracking
mkdir -p "$BASTACK_HOME/sessions"
touch "$BASTACK_HOME/sessions/$PPID"
find "$BASTACK_HOME/sessions" -mmin +120 -type f -exec rm {} + 2>/dev/null || true

# 2. Config
PROACTIVE="$("$_BS_BIN/bs-config" get proactive 2>/dev/null || echo "true")"
TELEMETRY="$("$_BS_BIN/bs-config" get telemetry 2>/dev/null || echo "local")"

# 3. Context
BRANCH="$(git branch --show-current 2>/dev/null || echo "unknown")"
SESSION_ID="$-$(date +%s)"
eval "$("$_BS_BIN/bs-slug" 2>/dev/null)" || true
SLUG="${SLUG:-$(basename "$PWD")}"

echo "BRANCH:    $BRANCH"
echo "SLUG:      $SLUG"
echo "PROACTIVE: $PROACTIVE"
echo "TELEMETRY: $TELEMETRY"

# 4. Learnings — surface top 3 if project has > 5 entries
_LEARN_FILE="$BASTACK_HOME/projects/$SLUG/learnings.jsonl"
if [ -f "$_LEARN_FILE" ]; then
  _LEARN_COUNT="$(wc -l < "$_LEARN_FILE" | tr -d ' ')"
  echo "LEARNINGS: $_LEARN_COUNT entries"
  if [ "$_LEARN_COUNT" -gt 5 ] 2>/dev/null; then
    "$_BS_BIN/bs-learnings-search" --limit 3 2>/dev/null || true
  fi
else
  echo "LEARNINGS: 0"
fi

# 5. Analytics — log skill usage (only if telemetry is on)
_SKILL_NAME="${BS_SKILL_NAME:-unknown}"
if [ "$TELEMETRY" != "off" ]; then
  mkdir -p "$BASTACK_HOME/analytics"
  echo "{\"skill\":\"$_SKILL_NAME\",\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"repo\":\"$SLUG\"}" \
    >> "$BASTACK_HOME/analytics/skill-usage.jsonl" 2>/dev/null || true
fi

# 6. Timeline — record skill start (always local, background)
"$_BS_BIN/bs-timeline-log" \
  "{\"skill\":\"$_SKILL_NAME\",\"event\":\"started\",\"branch\":\"$BRANCH\",\"session\":\"$SESSION_ID\"}" \
  2>/dev/null &
