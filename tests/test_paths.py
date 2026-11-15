"""Tests for vague.paths: where state lives and how a state file is replaced."""

from vague.paths import atomic_write, vague_home


def test_vague_home_uses_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(tmp_path))
    assert vague_home() == tmp_path


def test_vague_home_defaults_to_home_dot_vague(monkeypatch):
    monkeypatch.delenv("VAGUE_HOME", raising=False)
    assert vague_home().name == ".vague"


def test_vague_home_empty_env_var_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", "")
    assert vague_home().name == ".vague"


def test_vague_home_expands_tilde(monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", "~/.custom-vague")
    assert "~" not in str(vague_home())
    assert vague_home().name == ".custom-vague"


def test_atomic_write_creates_parents_and_leaves_no_temp_file(tmp_path):
    target = tmp_path / "nested" / "settings.json"
    atomic_write(path=target, text="first")
    atomic_write(path=target, text="second")
    assert target.read_text() == "second"
    assert [p.name for p in target.parent.iterdir()] == ["settings.json"]
