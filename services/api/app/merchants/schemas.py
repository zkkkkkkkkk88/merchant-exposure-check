from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class MerchantSourceCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=40)
    url: HttpUrl
    is_verified: bool = False


class MerchantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    branch_name: str | None = Field(default=None, max_length=160)
    city: str = Field(min_length=1, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    industry: str = Field(min_length=1, max_length=80)
    address: str | None = Field(default=None, max_length=300)
    price_range: str | None = Field(default=None, max_length=80)
    opening_hours: str | None = Field(default=None, max_length=160)
    products: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    sources: list[MerchantSourceCreate] = Field(default_factory=list)


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    branch_name: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    industry: str | None = Field(default=None, min_length=1, max_length=80)
    address: str | None = Field(default=None, max_length=300)
    price_range: str | None = Field(default=None, max_length=80)
    opening_hours: str | None = Field(default=None, max_length=160)
    products: list[str] | None = None
    strengths: list[str] | None = None
    sources: list[MerchantSourceCreate] | None = None


class MerchantSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    url: str
    is_verified: bool
    created_at: datetime


class MerchantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    normalized_name: str
    branch_name: str | None
    city: str
    district: str | None
    industry: str
    address: str | None
    price_range: str | None
    opening_hours: str | None
    products: list[str]
    strengths: list[str]
    sources: list[MerchantSourceRead]
    created_at: datetime
    updated_at: datetime
