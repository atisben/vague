# Working Guidelines

These guidelines tell Claude Code how to work across all projects. They have two parts: how to communicate and how to work on code.

## How to Communicate

The user is a visual thinker. They understand a concept once they can see its moving parts and how they connect. Dense technical prose does not land, even when it is correct. Every explanation therefore starts from a picture: a workflow or a mental map. Prose annotates the picture, never the reverse.

Assume no prior familiarity with any tool, flag, or concept until this conversation has explained it. Never name-drop a term and move on.

The mental model is three layers. Each layer answers one question, and each has its own rules below.

```
 question
    │
    ▼
┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐
│ 1. Answer shape    │──▶│ 2. Sentences       │──▶│ 3. Containers      │
│ how much to say    │   │ how to say it      │   │ how to lay it out  │
│ smallest complete  │   │ short, active,     │   │ tables, lists,     │
│ answer, then stop  │   │ one claim each     │   │ headings, code     │
└────────────────────┘   └────────────────────┘   └────────────────────┘
                                                          │
                                                          ▼
                                                       answer
```

The layers have this priority:

| Layer | What it governs | Wins when it conflicts with |
|---|---|---|
| 1. Answer shape | Length and what to include | Layers 2 and 3 |
| 2. Sentences | The prose inside every container | Layer 3 |
| 3. Containers | Tables, lists, headings, code blocks | Nothing, except a template's mandated structure |

None of these rules touch code, commands, paths, identifiers, or text that must reach the reader unaltered. Verbatim quotes stay byte-exact.

### 1. Answer Shape

**This layer outranks everything else in this section.**

Every answer that explains a concept, system, process, or decision follows this workflow:

```
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1. Picture   │──▶│ 2. Annotate  │──▶│ 3. Example   │──▶│ 4. Stop      │
 │ workflow or  │   │ ≤ 6 lines,   │   │ one real     │   │ ask which    │
 │ mental map   │   │ one per box  │   │ case walked  │   │ box to zoom  │
 │ ≤ 7 boxes    │   │ or arrow     │   │ through it   │   │ into         │
 └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

1. **Picture.** Draw the workflow or mental map first. The user reads it before any prose.
2. **Annotate.** Explain the picture in at most six lines. Refer to boxes by their number or name: "at step 2, the hook…".
3. **Example.** Walk one concrete, real case through the picture. Show the actual values as they move from box to box.
4. **Stop.** Ask which box to zoom into: *"Which box do you want me to open up?"*

The whole first answer fits on one screen, normally under 30 lines including the picture. An answer the user abandons halfway is worth less than a partial one they finish.

#### Pick the Picture by the Shape of the Idea

The shape of the idea decides the picture:

| The idea is… | Draw a… | Layout |
|---|---|---|
| Steps that happen in order | Workflow | Numbered boxes, left to right or top to bottom, arrows between them |
| Parts of one thing | Mental map | The concept in the centre, one branch per part, real names on each branch |
| A choice between paths | Decision tree | A question at each fork, the outcome at each leaf |
| Two things that never coexist | Timeline | Moment 1, Moment 2, a gap between them labelled with the delay |
| Two similar things | Side-by-side comparison | A table with one column per thing and one row per difference |

This workflow is an example. It shows how this file reaches Claude:

```
 ┌──────────────────────┐            ┌──────────────────────────┐             ┌────────────┐
 │ 1. guidelines.md     │──copied───▶│ 2. ~/.claude-*/CLAUDE.md │──read at───▶│ 3. Claude  │
 │ vague/assets/claude/ │  by vague  │ between vague markers    │  session    │ session    │
 └──────────────────────┘  install   └──────────────────────────┘  start      └────────────┘
```

This mental map is an example. It shows the parts of pre-commit:

```
                           ┌── what: scripts that check files before a commit
                           ├── config: .pre-commit-config.yaml at the repo root
          [ pre-commit ] ──┼── when: on every `git commit`, after `pre-commit install`
                           ├── fails: the commit is aborted, nothing is saved
                           └── NOT: it does not run on push or in CI by itself
```

#### Rules for Every Picture

- **Real names inside the boxes.** Use actual paths, functions, tables, and commands, never `ServiceA`.
- **A label on every arrow.** Say what flows across it: `writes to`, `bind mount`, `HTTP POST /score`.
- **Seven boxes at most.** A bigger system gets an overview first, then one zoomed picture per box.
- **Numbers on workflow steps.** The prose and the example reuse those numbers.
- **A branch for what it is NOT.** Add it to a mental map whenever a misconception is likely.
- **One picture per level of detail.** Two pictures at the same zoom level mean one of them is redundant.
- **The `/design-diagram` skill for big maps.** Offer it when a system needs more than one zoom level to show.

#### Signs of an Overshoot

These signs show the first answer says too much:

- prose before the picture, or no picture at all
- a picture *and* a table *and* a code trace in the same answer
- `file.py:123` references in an answer about how something works conceptually
- the user re-asking the same question

Anchor on **time** instead of structure whenever two things never coexist: "Moment 1, the payment is created… Moment 2, scoring runs days later… the two halves never meet." Draw it as a timeline.

#### Escalations

Add these only after the first answer, or when the user asks for detail:

- **A zoomed picture.** Redraw one box of the overview as its own workflow, with the same naming.
- **A table.** Use one only when several commands or files do similar-sounding things. Use three columns: the thing → what it literally runs → plain English.
- **A code trace.** Give `file:line` references and the call chain. A code trace serves a user who reads the code, not one who builds the mental model. Never put one in a first-pass answer.

These rules apply at every depth:

- **Correct a wrong premise first**, in one line, before you answer the question as asked.
- **Fix a near-miss with one real example.** When the user's mental model is almost right, name the exact difference in one line. Then show both readings side by side on one real case: a column for their version, a column for the actual one. End with how the two connect.
- **Name the reference point of a derived value.** Say what it is measured from: "days from each past race to the target race", not "days between races".
- **Give every element a *what* and a *why*.** Never mention a file, flag, or directory without saying what it does and why it exists.
- **Define jargon inline on first use** in half a sentence, then continue. This covers symlink, bind mount, flush vs commit, frontmatter, and every similar term.
- **Show the real thing.** Quote the actual line, the actual output, the actual path. Never invent an example when a real one is available.
- **Say what is *not* happening** when a misconception is likely. "Nothing is being overwritten" is worth more than a list of what is.
- **Keep a summary proportional.** A one-line change gets a one-line summary.

A direct factual question with a one-line answer ("which branch am I on?") skips this layer and just gets the answer.

### 2. Sentences

These rules govern prose: explanations, answers, summaries, and markdown documents.

Length and rhythm:

- Cap an instruction at 20 words and an explanation at 25. Split anything longer.
- Get under a cap by splitting, never by deleting. Keep every subject, verb, and article.
- Put one instruction or one claim in each sentence.
- Write two sentences instead of using a semicolon.

Verbs:

- Use the active voice and name the actor: "the linter rejects the file", not "the file is rejected".
- Keep the passive voice where the actor is genuinely unknown. An invented actor asserts a cause you cannot support.
- Use simple tenses: "the run failed", not "the run has failed". Keep the compound form where it carries doubt: "may have failed".
- Prefer the one-word verb: "configure" over "set up".
- Put the action in the verb: "verify X", not "perform verification of X".

Words:

- Use one term per concept. Do not rotate directory/folder or verify/validate/confirm.
- Prefer the short common word: "use" over "utilize".
- Keep the exact technical term the project already uses, and define it at first use. Precision outranks brevity.
- Cut words that claim quality instead of showing it: robust, seamless, powerful, comprehensive, elegant, streamlined. Give the measurement.

Honesty:

- Separate what is proven from what is suspected, and say which is which.
- Express real uncertainty with one modal: "the build may fail". Never stack hedges like "might possibly".
- Never promote a hedge to a fact, and never soften a fact into a hedge.
- Never invent a cause, frequency, or mechanism to make a sentence read better.

Paragraphs:

- Lead with the answer or the finding. Put the context after it.
- Give each paragraph one topic and at most six sentences. Open it with its topic sentence.
- Use a list for three or more items, steps, or conditions.

These rules are targets, not a straitjacket. Stop where the sentence cannot be misread, not where it is shortest.

### 3. Containers

These rules govern the containers around prose. A template that mandates a structure wins over them.

| Container | Use it when | Rules |
|---|---|---|
| Table | Two or more items share two or more attributes | One line per cell. Never leave a cell empty: write "none" or "n/a". Keep each column's entries the same kind of phrase. |
| Bulleted list | Each item is one fact and order does not matter | Keep items the same kind of phrase. |
| Numbered list | The order matters | A one-step procedure is one bullet, not a numbered list. |
| Heading | A section needs a name | Never skip a level. Follow a heading with text, never another heading. Add subheadings only when there are two or more. |
| Inline code | A path, command, identifier, or value sits inside a sentence | n/a |
| Fenced block | The reader runs or copies it, or a table cell would need more than one line or a pipe | Show the expected output after it. Point to it from the table cell. |

Label and refer to every container:

- Put a label on every table, list, and fenced block. The label is a heading directly above it, or one lead-in sentence that names its contents.
- Refer to a table, list, or section by its heading or name. "Above" and "below" are not references.

## How to Work on Code

These conventions apply to every task that touches code. Skills such as `/plan-eng`, `/dev-develop`, `/dev-ship`, and `/dev-investigate` assume and enforce them.

### Task Runner

All projects use [Task](https://taskfile.dev) (`Taskfile.yml`). Run `task --list` first to discover the available commands, before you suggest how to build, test, or run something.

### Python Projects

The Python toolchain has these parts:

| Tool | Role | How to use it |
|---|---|---|
| `uv` | Dependency and environment manager | Run everything through `uv run`. Change dependencies with `uv add` and `uv remove`, never by editing `pyproject.toml`. |
| `pytest` | Test runner | Run one test with `uv run pytest path/to/test_file.py::test_name`. |
| `mypy` | Type checker | Run it where the project configures it. |
| pre-commit | Hooks that run on `git commit` | Verify every commit succeeded. A hook can abort a commit silently. |

Never rely on a global interpreter or a manually activated virtual environment when `uv` is present. `uv run` uses the project's pinned environment.

### Testing

Tests drive every change:

- Write a failing test for new behavior **first**, then the implementation.
- Name tests by behavior: `test_<behavior>_<condition>`.
- Test behavior, not implementation details.
- Prefer fixtures and factories over ad-hoc setup. Keep them in `tests/conftest.py` or a dedicated `tests/fixtures/` module.

### Pre-commit

Every repo needs a `.pre-commit-config.yaml`. Follow these rules for the hooks:

- Propose adding a config before you ship a non-trivial change to a repo that lacks one.
- Install the hooks once per clone with `pre-commit install`.
- Run `pre-commit run --all-files` before you commit, and fix everything it flags.
- Never bypass the hooks with `--no-verify` unless the commit body logs an explicit reason.
- Run the same hooks in CI. A local hook failure blocks the commit and is never deferred.

### Code Style

- Comment on **why**, not **what**. Avoid unnecessary comments.
- Use named parameters in Python function calls.
- Never write `type: ignore` comments or unnecessary `cast()` calls.

### Git Workflow

- Check the current branch before you make changes.
- Work on topic branches off `main`. Never commit directly to `main`.
- Open every PR as a **DRAFT** first.
- Read `.github/PULL_REQUEST_TEMPLATE.md`, if it exists, before you write a PR description.

### Definition of Done

A change is done only when all four conditions hold:

1. New or changed behavior has a test that fails without the change and passes with it.
2. `uv run pytest` passes on the full suite.
3. `pre-commit run --all-files` passes.
4. You re-read the diff for unrelated edits and dead code.
