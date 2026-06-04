"""Atomic git commit using GitPython."""

from __future__ import annotations

from pathlib import Path

NOTHING_TO_COMMIT = "nothing-to-commit"


def atomic_commit(message: str, files: list[str], cwd: Path | None = None) -> str:
    """Stage files, commit with GitPython. Returns commit SHA or 'nothing-to-commit'."""
    import git as gitpython
    repo = gitpython.Repo(str(cwd) if cwd else ".", search_parent_directories=True)

    for f in files:
        repo.index.add([f])

    if repo.head.is_valid():
        # Normal case: compare staged tree against the last commit.
        nothing_to_commit = not repo.index.diff("HEAD") and not repo.index.diff(None)
    else:
        # Unborn branch (fresh repo, no commits): HEAD has nothing to diff
        # against, so "anything to commit" just means "anything staged".
        nothing_to_commit = not repo.index.entries

    if nothing_to_commit:
        return NOTHING_TO_COMMIT

    commit = repo.index.commit(message)
    return commit.hexsha
