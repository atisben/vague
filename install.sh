#!/usr/bin/env bash
# install.sh — set up bastack on a new machine
#
# What it does:
#   1. Makes all bin/ scripts executable
#   2. Symlinks bin/ to ~/.local/bin/ (or ~/bin/) so they're on PATH
#   3. Creates the ~/.bastack/ state directory
#   4. Writes a default config
#   5. Optionally symlinks skills/ to ~/.claude/skills/bastack/
#      so Claude Code can discover them as slash commands

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$REPO_DIR/bin"
SKILLS_DIR="$REPO_DIR/skills"
STATE_DIR="${BASTACK_HOME:-$HOME/.bastack}"

echo "Installing bastack from: $REPO_DIR"
echo ""

# ── 1. Make bin scripts executable ──────────────────────────────────────────
echo "Making bin scripts executable..."
chmod +x "$BIN_DIR"/bs-*
echo "  ✓ bin/ scripts are executable"

# ── 2. Symlink bin/ to PATH ──────────────────────────────────────────────────
TARGET_BIN="${HOME}/.local/bin"
[ -d "$HOME/bin" ] && TARGET_BIN="$HOME/bin"  # prefer ~/bin if it exists

if [ ! -d "$TARGET_BIN" ]; then
  mkdir -p "$TARGET_BIN"
  echo "  Created $TARGET_BIN — add it to your PATH if not already there"
fi

for script in "$BIN_DIR"/bs-*; do
  name="$(basename "$script")"
  link="$TARGET_BIN/$name"
  if [ -L "$link" ] || [ -f "$link" ]; then
    rm -f "$link"
  fi
  ln -s "$script" "$link"
done
echo "  ✓ bin/ symlinked to $TARGET_BIN"

# ── 3. Create state directory ─────────────────────────────────────────────────
mkdir -p \
  "$STATE_DIR/sessions" \
  "$STATE_DIR/analytics" \
  "$STATE_DIR/projects"
echo "  ✓ State directory: $STATE_DIR"

# ── 4. Write default config ──────────────────────────────────────────────────
if [ ! -f "$STATE_DIR/config.yaml" ]; then
  "$BIN_DIR/bs-config" set proactive true
  "$BIN_DIR/bs-config" set telemetry local
  echo "  ✓ Default config written"
else
  echo "  ✓ Config already exists — skipping"
fi

# ── 5. Symlink skills to ~/.claude/skills/bastack/ ───────────────────────────
CLAUDE_SKILLS_DIR="${HOME}/.claude/skills/bastack"
read -r -p "Symlink skills to $CLAUDE_SKILLS_DIR? (y/n) " ANSWER
if [ "$ANSWER" = "y" ]; then
  mkdir -p "$(dirname "$CLAUDE_SKILLS_DIR")"
  if [ -L "$CLAUDE_SKILLS_DIR" ]; then
    rm "$CLAUDE_SKILLS_DIR"
  fi
  ln -s "$SKILLS_DIR" "$CLAUDE_SKILLS_DIR"
  echo "  ✓ Skills symlinked to $CLAUDE_SKILLS_DIR"
else
  echo "  Skipped — you can symlink manually:"
  echo "    ln -s $SKILLS_DIR $CLAUDE_SKILLS_DIR"
fi

echo ""
echo "bastack installed. Commands available:"
echo "  bs-config, bs-slug, bs-analytics, bs-learnings-search"
echo ""
echo "Skills available in Claude Code:"
echo "  /office-hours, /plan-ceo-review, /plan-eng-review"
echo "  /design-consultation, /design-shotgun, /design-html, /design-review"
echo "  /ship, /review, /investigate, /learn, /retro"
echo ""
echo "Run 'bs-analytics' to see usage stats."
