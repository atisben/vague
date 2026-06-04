"""Concurrency tests: parallel appends must not lose writes."""

import os
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime

from vague.models import LearningEntry, ObservationEntry
from vague.sdk.core.learnings import append_learning, search_learnings
from vague.sdk.core.observations import append_observation, list_observations


def _append_learning(args):
    home, i = args
    os.environ["VAGUE_HOME"] = home
    append_learning(
        "test-slug",
        LearningEntry(
            skill="t",
            type="pattern",
            key=f"key-{i}",
            insight="x",
            confidence=5,
            source="observed",
            ts=datetime.now(UTC),
        ),
    )


def _append_observation(args):
    home, i = args
    os.environ["VAGUE_HOME"] = home
    append_observation(
        "test-slug",
        ObservationEntry(
            id=0,
            skill="t",
            type="improvement",
            issue=f"i-{i}",
            suggestion="s",
            principle="p",
            source_skill="t",
            ts=datetime.now(UTC),
        ),
    )


def test_parallel_learnings_no_lost_writes(vague_home):
    home = str(vague_home)
    n = 40
    with ProcessPoolExecutor(max_workers=8) as ex:
        list(ex.map(_append_learning, [(home, i) for i in range(n)]))
    assert len(search_learnings("test-slug")) == n


def test_parallel_observations_unique_ids(vague_home):
    home = str(vague_home)
    n = 40
    with ProcessPoolExecutor(max_workers=8) as ex:
        list(ex.map(_append_observation, [(home, i) for i in range(n)]))
    obs = list_observations("test-slug")
    assert len(obs) == n
    ids = [o.id for o in obs]
    assert len(set(ids)) == n  # no duplicate ids under contention
