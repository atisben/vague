"""Pydantic models for vague."""

from typing import Literal

from pydantic import BaseModel


class ConfigModel(BaseModel):
    proactive: bool = True
    telemetry: str = "local"  # "local" | "off"


class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    sdk_commands: list[str] = []
    requires_slug: bool = True
    # Empty means every runtime. The installer reads it to keep Claude-only skills out of cursor and windsurf.
    runtimes: list[Literal["claude", "cursor", "windsurf", "generic"]] = []
