from typing import Literal

from pydantic import BaseModel, Field

Risk = Literal["low", "medium", "high"]


class ChangedFile(BaseModel):
    filename: str
    additions: int = 0
    deletions: int = 0
    patch: str = ""


class PullRequest(BaseModel):
    title: str
    description: str = ""
    files: list[ChangedFile] = Field(default_factory=list)


class TriageResult(BaseModel):
    risk: Risk = Field(description="How risky the change is to ship")
    focus_areas: list[str] = Field(
        description="What QA should test first, most important first", max_length=5
    )
    rationale: str = Field(description="One or two sentences explaining the risk rating")
