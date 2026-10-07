from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RecipientInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class JobCreateRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=255)
    event_date: date
    recipients: list[RecipientInput] = Field(min_length=1, max_length=10_000)

    @field_validator("event_name")
    @classmethod
    def event_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("event_name must not be blank")
        return value


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_name: str
    recipient_email: str
    status: str
    error_message: str | None = None
    download_url: str | None = None


class JobResponse(BaseModel):
    job_id: int
    status: str
    total: int
    successful: int
    failed: int
    processed: int
    progress: int
    created_at: datetime
    completed_at: datetime | None = None
    certificates: list[CertificateResponse] = []
