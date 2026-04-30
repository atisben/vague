#!/usr/bin/env bash
# install.sh — set up bastack on a new machine
#
# What it does:
#   1. Makes all bin/ scripts executable
#   2. Symlinks bin/ to ~/.local/bin/ (or ~/bin/) so they're on PATH
#   3. Creates the ~/.bastack/ state directory
#   4. Writes a default config
#   5. Optionally symlinks each skill to AI tool skill directories:
#      - ~/.claude/skills/    (Claude Code)
#      - ~/.copilot/skills/   (GitHub Copilot CLI)
#   6. Optionally symlinks CLAUDE.md (global AI instructions) to:
#      - ~/.claude/CLAUDE.md           (Claude Code)
#      - ~/.copilot/copilot-instructions.md  (GitHub Copilot CLI)

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

# ── 5. Symlink skills to AI tool skill directories ───────────────────────────
symlink_skills_to() {
  local dir="$1"
  local label="$2"
  mkdir -p "$dir"
  for skill_dir in "$SKILLS_DIR"/*/; do
    name="$(basename "$skill_dir")"
    link="$dir/$name"
    if [ -L "$link" ] || [ -e "$link" ]; then
      rm -rf "$link"
    fi
    ln -s "$skill_dir" "$link"
    echo "  ✓ $name"
  done
  echo "  ✓ Skills symlinked to $dir ($label)"
}

CLAUDE_SKILLS_DIR="${HOME}/.claude/skills"
COPILOT_SKILLS_DIR="${HOME}/.copilot/skills"

echo ""
echo "Skills are tool-agnostic and work with Claude Code and GitHub Copilot CLI."
read -r -p "Install skills for Claude Code ($CLAUDE_SKILLS_DIR)? (y/n) " ANSWER_CLAUDE
if [ "$ANSWER_CLAUDE" = "y" ]; then
  symlink_skills_to "$CLAUDE_SKILLS_DIR" "Claude Code"
else
  echo "  Skipped Claude Code."
fi

read -r -p "Install skills for GitHub Copilot CLI ($COPILOT_SKILLS_DIR)? (y/n) " ANSWER_COPILOT
if [ "$ANSWER_COPILOT" = "y" ]; then
  symlink_skills_to "$COPILOT_SKILLS_DIR" "GitHub Copilot CLI"
else
  echo "  Skipped GitHub Copilot CLI."
fi

# ── 6. Symlink global AI instructions (CLAUDE.md) ────────────────────────────
INSTRUCTIONS_SRC="$REPO_DIR/CLAUDE.md"

symlink_instructions_to() {
  local target="$1"
  local label="$2"
  local target_dir
  target_dir="$(dirname "$target")"
  mkdir -p "$target_dir"

  if [ -L "$target" ]; then
    local current_dest
    current_dest="$(readlink "$target")"
    if [ "$current_dest" = "$INSTRUCTIONS_SRC" ]; then
      echo "  ✓ Already symlinked ($label) — skipping"
      return
    fi
    rm -f "$target"
  elif [ -f "$target" ]; then
    mv "$target" "${target}.bak"
    echo "  ⚠ Backed up existing file to ${target}.bak"
  fi

  ln -s "$INSTRUCTIONS_SRC" "$target"
  echo "  ✓ CLAUDE.md → $target ($label)"
}

echo ""
echo "CLAUDE.md is the unified global AI instructions file (works with both tools)."
read -r -p "Install global instructions for Claude Code (~/.claude/CLAUDE.md)? (y/n) " ANSWER_CLAUDE_MD
if [ "$ANSWER_CLAUDE_MD" = "y" ]; then
  symlink_instructions_to "${HOME}/.claude/CLAUDE.md" "Claude Code"
else
  echo "  Skipped Claude Code instructions."
fi

read -r -p "Install global instructions for GitHub Copilot CLI (~/.copilot/copilot-instructions.md)? (y/n) " ANSWER_COPILOT_MD
if [ "$ANSWER_COPILOT_MD" = "y" ]; then
  symlink_instructions_to "${HOME}/.copilot/copilot-instructions.md" "GitHub Copilot CLI"
else
  echo "  Skipped GitHub Copilot CLI instructions."
fi

echo ""
echo "bastack installed. Commands available:"
echo "  bs-config, bs-slug, bs-analytics, bs-learnings-search"
echo ""
echo "Skills available:"
echo "  /office-hours, /plan-ceo-review, /plan-eng-review"
echo "  /design-consultation, /design-shotgun, /design-html, /design-review"
echo "  /ship, /review, /investigate, /learn, /retro, /vault"
echo ""
echo "Use them in Claude Code or GitHub Copilot CLI with any slash command."
echo "Run 'bs-analytics' to see usage stats."
