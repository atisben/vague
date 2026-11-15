---
name: dev-review
version: 1.0.0
category: Execution
summary: 'Review a diff on two axes: Standards and Spec.'
description: |
  Two-axis review of the changes since a fixed point (commit, branch, tag, merge-base).
  Standards: does the diff follow the repo's documented coding standards, plus a Fowler smell baseline?
  Spec: does the diff match the issue or plan it came from? Runs both in parallel sub-agents,
  verifies each finding against the files, and reports the axes separately. Read-only.
  Trigger: "review since X", "review this branch", "review my changes against the spec", "/dev-review".
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
---

<!-- Adapted from mattpocock/skills@7739eae (MIT). See NOTICE.md. -->

## Preamble

```bash
eval "$(vague context --shell --skill dev-review)"
```

**Proactive invocation:** When the user asks to review a branch, a PR, or work in progress against a standard or a spec, invoke this skill. For a correctness bug hunt, use the built-in `/code-review` instead.

---

## What this skill does

```
 ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
 │ 1. Pin the     │──▶│ 2. Find spec   │──▶│ 3. Find the    │
 │ fixed point    │   │ issue / plan   │   │ standards      │
 └────────────────┘   └────────────────┘   └────────────────┘
                                                    │
        ┌───────────────────────────────────────────┤
        ▼                                           ▼
 ┌────────────────┐                          ┌────────────────┐
 │ 4a. Standards  │                          │ 4b. Spec       │
 │ sub-agent      │                          │ sub-agent      │
 └────────────────┘                          └────────────────┘
        │                                           │
        └──────────────────┬────────────────────────┘
                           ▼
                  ┌────────────────┐   ┌────────────────┐
                  │ 5. Verify each │──▶│ 6. Two reports │
                  │ finding        │   │ never merged   │
                  └────────────────┘   └────────────────┘
```

- **Standards** asks: does the code follow the documented conventions?
- **Spec** asks: does the code build what the issue or plan asked for?
- **Not** a bug hunt. It does not look for correctness bugs, and it never edits files.

Both axes run as parallel sub-agents, so neither pollutes the other's context. Start every sub-agent with a fresh context window.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point: a commit SHA, branch, tag, `main`, `HEAD~5`. If they gave none, ask with AskUserQuestion.

Capture the diff command once: `git diff <fixed-point>...HEAD`. The three dots compare against the merge-base. Also capture `git log <fixed-point>..HEAD --oneline`.

Confirm the fixed point resolves with `git rev-parse <fixed-point>` and that the diff is not empty. A bad ref or an empty diff must fail here, not inside two parallel sub-agents.

### 2. Identify the spec source

Look for the originating spec in this order:

1. Issue references in the commit messages (`#123`, `Closes #45`, GitLab `!67`). Fetch them with `gh issue view <n>`, or `glab issue view <n>` on GitLab.
2. A path the user passed as an argument.
3. The engineering plan for this branch. Run `vague memory-search --kind doc --skill plan-eng`. The plan has the key `eng-plan-<branch>`, with every `/` in the branch replaced by `-`. Each line ends with `(files: <path>)`, a vault note you can read.
4. A spec file under `docs/`, `specs/`, or `.scratch/` that matches the branch name or feature.
5. If nothing is found, ask the user where the spec is. If they say there is none, skip the Spec sub-agent and report "no spec available".

### 3. Identify the standards sources

Search the repo for every file that documents how code is written. Include these when they exist:

- `CODING_STANDARDS.md` and `CONTRIBUTING.md`
- the repo's `CLAUDE.md` and `AGENTS.md`
- `~/.claude*/CLAUDE.md` (the user's global working guidelines)

On top of the documented standards, the Standards axis always carries the **smell baseline** below. It applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented standard always wins. Where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation. Skip anything tooling already enforces: linters, formatters, `mypy`, the `pre-commit` hooks.

Smell baseline (Fowler, *Refactoring*, ch. 3). Each entry reads *what it is* → *how to fix*:

- **Mysterious Name**: a function, variable, or type whose name does not reveal what it does or holds. → rename it. If no honest name comes, the design is murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk or file. → extract the shared shape and call it from both.
- **Feature Envy**: a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together. → bundle them into one type and pass that.
- **Primitive Obsession**: a primitive or string stands in for a domain concept. → give the concept its own small type.
- **Repeated Switches**: the same `switch` or `if` cascade on one type recurs across the change. → replace it with polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files. → gather what changes together into one module.
- **Divergent Change**: one file or module is edited for several unrelated reasons. → split it so each module changes for one reason.
- **Speculative Generality**: abstraction, parameters, or hooks added for needs the spec does not have. → delete it and inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller should not depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly delegates onward. → cut it and call the real target directly.
- **Refused Bequest**: a subclass that ignores or overrides most of what it inherits. → drop the inheritance and use composition.

### 4. Spawn both sub-agents in parallel

Issue both `Agent` calls in one response, in the foreground. Each sub-agent sees only its prompt, so paste everything it needs.

Every sub-agent prompt must also say: "Do not invoke any skill, including `/dev-review`. Do not edit files. Use only read-only commands."

**Standards sub-agent prompt** includes:

- The full diff command and the commit list.
- The standards-source files from step 3, plus the smell baseline pasted in full.
- This brief: "Report, per file and hunk, (a) every place the diff violates a documented standard, citing the file and the rule; and (b) every baseline smell you spot, naming it and quoting the hunk. Documented-standard breaches can be hard violations. Baseline smells are always judgement calls. A documented standard overrides the baseline. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** includes:

- The diff command and the commit list.
- The path or fetched contents of the spec.
- This brief: "Report (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that was not asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec sub-agent and say so in the final report.

### 5. Verify each finding

Sub-agents can misread a hunk. Before reporting, open the cited file with Read or Grep and check each finding against the real code.

- Drop a finding whose quoted hunk does not exist or does not say what the sub-agent claims.
- Mark a smell you cannot confirm as "unconfirmed" instead of dropping it silently.
- Never add a finding of your own. This skill relays and checks. It does not review.

### 6. Aggregate

Present the two reports under `## Standards` and `## Spec` headings. Do **not** merge or rerank findings across axes (see *Why two axes*).

End with one line: the finding count per axis and the worst issue within each axis. Never pick a single winner across axes.

Then offer the next step: "Fix these yourself, or run `/code-review --fix` for the correctness pass. Then `/dev-ship`."

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but builds the wrong thing → **Standards pass, Spec fail.**
- Code that does what the issue asked but breaks the conventions → **Spec pass, Standards fail.**

Separate reports stop one axis from hiding the other.

## Memory

Log a durable fact only when a later session would otherwise rediscover it. Examples: where this repo documents its standards, or a smell the repo endorses on purpose.

```bash
vague memory-log review-standards-source "Coding standards live in docs/STYLE.md; the repo allows Middle Man in adapters/." --files docs/STYLE.md --skill dev-review
```
