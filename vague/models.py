"""Pydantic models for vague."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConfigModel(BaseModel):
    proactive: bool = True
    telemetry: str = "local"  # "local" | "off"


class LearningEntry(BaseModel):
    skill: str
    type: str  # pitfall | pattern | preference | architecture | tool | operational
    key: str
    insight: str
    confidence: int  # 1-10
    source: str  # observed | user-stated | inferred
    files: list[str] = []
    ts: datetime


class TimelineEntry(BaseModel):
    skill: str
    event: str  # started | completed
    branch: str
    session: str
    outcome: Optional[str] = None
    ts: datetime


class AnalyticsEntry(BaseModel):
    skill: str
    ts: datetime
    repo: str


class VagueInitResult(BaseModel):
    slug: str
    branch: str
    proactive: bool
    telemetry: str
    learnings: list[LearningEntry]  # top 3 by confidence if >5 entries, else all


class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    sdk_commands: list[str] = []
    requires_slug: bool = True
    requires_planning: bool = False
