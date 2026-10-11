from typing import Literal
from pydantic import BaseModel, Field


class Source(BaseModel):
    id: str
    title: str
    url: str
    excerpt: str
    basis: str = "搜索摘要"


class Selection(BaseModel):
    source_ids: list[str]
    rationale: str


class Evidence(BaseModel):
    statement: str
    source_ids: list[str]
    limitation: str


class EvidenceBundle(BaseModel):
    evidence: list[Evidence] = Field(min_length=1, max_length=8)


class Topic(BaseModel):
    id: str = ""
    title: str
    angle: Literal["决策", "争议", "实践", "认知"]
    audience: str
    why: str
    tension: str
    source_ids: list[str]
    caveat: str


class TopicBundle(BaseModel):
    topics: list[Topic] = Field(min_length=1, max_length=5)


class ResearchRun(BaseModel):
    id: str
    subject: str
    audience: str
    focus: str
    mode: Literal["demo", "live"]
    created_at: str
    sources: list[Source]
    evidence: list[Evidence]
    topics: list[Topic]
    trace: list[dict[str, str]]


class Outline(BaseModel):
    thesis: str
    sections: list[str] = Field(min_length=3, max_length=6)
    counterargument: str
    checks: list[str]
    source_ids: list[str]
