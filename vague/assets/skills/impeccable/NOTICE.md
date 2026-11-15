# Notice

The `impeccable` skill, its `reference/` playbooks, and the agents `impeccable-finish-reviewer` and `impeccable-motion-reviewer` are adapted from Impeccable by Paul Bakaus.

- **Upstream:** https://github.com/pbakaus/impeccable
- **Commit:** `2b86d9c` (skill version 4.9.1)
- **Licence:** Apache License 2.0, reproduced in [LICENSE](LICENSE)

Every adapted file carries a one-line comment that names the upstream commit and points to this notice.

## Upstream Notice

The upstream `NOTICE.md` reads:

> # Third-Party Notices
>
> This project includes content derived from third-party work, used under the terms of its original license.
>
> ## Platform Design Skills
>
> The `skill/reference/ios.md` and `skill/reference/android.md` platform reference files are distilled from ehmo's `platform-design-skills` (Apple Human Interface Guidelines and Material Design 3 rules), rewritten in Impeccable's voice.
>
> **Original work:** https://github.com/ehmo/platform-design-skills
> **Original license:** MIT
> **Author:** ehmo

vague does not include `ios.md` or `android.md`. The notice is kept as upstream wrote it.

## Changes in vague

vague modified the upstream files as follows:

- **No engine.** The Rust engine and its shell and `.cmd` launchers are not vendored. Every engine call (`context`, `detect`, `signals`, `concept-seed`, `motion-capture`, `critique-storage`, `audit-storage`, `pin`) is removed or rewritten as a step Claude does with its own tools.
- **No live mode, no image generation.** The `live` and `generate` commands, the browser overlay, the design hooks and generated image comps are gone.
- **The brief lives in vague memory.** Upstream reads and writes `PRODUCT.md`, `DESIGN.md` and a hidden state directory in the user's project. vague keeps the brief as `design-*` learnings in its memory ledger, and the task direction as a `direction.md` file under `/tmp/vague-comps/`, pointed at by a short `design-direction` scratch note. It writes nothing into the user's project except the UI files the user asked to change.
- **Dropped playbooks.** `live`, `live-setup`, `generate`, `hooks`, `doctor`, `foundations`, `component-review`, `new-work-comp`, `craft`, `ios`, `android`, `adapt.native`, `audit.native`, `init`, `document` and `pin`, plus the degraded fallbacks `documenter`, `asset-producer` and `manual-edit-applier`. Native iOS and Android guidance is not included.
- **New and rewritten playbooks.** `brief` replaces `init` and `document`. `new-work`, `critique`, `visualize` and `region-map` are rewritten. `visualize` and `region-map` draft three static HTML mockups instead of generated images, and turn the chosen mockup's sections into a checklist.
- **Two of five agents kept.** `impeccable-finish-reviewer` and `impeccable-motion-reviewer` are kept as read-only reviewers. `impeccable-documenter`, `impeccable-asset-producer` and `impeccable-manual-edit-applier` are dropped.
- **Reports go to the Obsidian vault.** Critique and audit reports, and approved mockups, are saved through vague's `/vault` skill, with a pointer logged in vague memory.
- **Claude only.** The skill installs for Claude runtimes only. Mentions of Codex, Cursor and GitHub Copilot spawn syntax are removed.
- **Live-mode parameter sections removed** from `colorize`, `layout` and `typeset`.
- **Source detector.** `vague/design_rules.py` ports 8 source rules from `crates/detect/src/regex_matchers.rs` (`side-tab`, `border-accent-on-rounded`, `overused-font`, `gradient-text`, `gray-on-color`, `ai-color-palette`, `bounce-easing`, `broken-image`) and the inline `impeccable-disable` comments from `crates/foundation/src/inline_ignores.rs`. `vague design-check` runs it, and every upstream `detect` step in `audit`, `critique`, `layout`, `typeset`, `polish` and `routing` now runs `vague design-check` before the manual scan.
- **Hook in the skill's frontmatter.** A `PostToolUse` hook declared in `SKILL.md` runs `vague design-check --hook` after each Edit and Write once the skill is invoked. It replaces upstream's `hooks` command, which installed design hooks into the user's project settings.
