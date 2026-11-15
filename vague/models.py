"""Pydantic models for vague."""

from typing import Literal

from pydantic import BaseModel


class ConfigModel(BaseModel):
    telemetry: str = "local"  # "local" | "off"


class SkillHookCommand(BaseModel):
    type: Literal["command"]
    command: str


class SkillHookMatcher(BaseModel):
    # Claude Code reads `matcher` as a regex over the tool name; absent means every tool.
    matcher: str = ""
    hooks: list[SkillHookCommand]


class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    sdk_commands: list[str] = []
    # Empty means every runtime. The installer reads it to keep Claude-only skills out of cursor and windsurf.
    runtimes: list[Literal["claude", "cursor", "windsurf", "generic"]] = []
    # Claude Code skill hooks, keyed by event (`PostToolUse`): active only while the skill is loaded.
    hooks: dict[str, list[SkillHookMatcher]] = {}
