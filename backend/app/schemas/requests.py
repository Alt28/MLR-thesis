from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)


class CloudImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal['google', 'onedrive']
    url: str = Field(min_length=1, max_length=4096)


class AuthenticationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=4096)


class ConfigRequest(RevisionRequest):
    config: dict
    approve_interactions: bool = False


class ReviewRequest(RevisionRequest):
    record_id: str
    action: Literal["retain", "exclude", "correct"]
    reason: str = Field(min_length=1, max_length=2000)
    corrections: dict[str, str | float] = Field(default_factory=dict)


class TrainingRequest(RevisionRequest):
    selection: Literal["baseline", "enhanced", "both"] = "both"


class AnalysisRequest(RevisionRequest):
    approve_interactions: bool = False
    retain_remaining: bool = False
    retain_reason: str = Field(default="", max_length=2000)
