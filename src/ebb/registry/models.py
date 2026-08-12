from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class Provider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class RegistryEntry(BaseModel):
    """One tracked model retirement. `source_url` and `verified_at` have no default and no
    `| None` — Pydantic already refuses to load a record missing either, which is the literal
    requirement (CLAUDE_CODE_PLAN.md Session 4: "refusing to load any record lacking
    source_url and verified_at"). The field validators below close the one gap plain
    required-ness doesn't: an explicit empty string is a present-but-useless value, not a
    missing one."""

    model_config = ConfigDict(frozen=True)

    canonical_id: str
    provider: Provider
    aliases: list[str] = []
    announced_at: date | None = None
    shutdown_at: date | None = None
    replacement_id: str | None = None
    source_url: str
    verified_at: date

    @field_validator("canonical_id", "source_url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank — provenance is a hard rule, not a formality")
        return value
