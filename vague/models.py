"""Pydantic models for vague."""

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
