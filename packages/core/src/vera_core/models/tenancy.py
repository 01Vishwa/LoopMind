"""Tenancy domain models — tenant, user, and RBAC role."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr

from vera_core.models.ids import TenantId, UserId


class TenantPlan(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Tenant(BaseModel):
    id: TenantId
    name: str
    plan: TenantPlan = TenantPlan.FREE
    created_at: datetime

    model_config = {"frozen": True}


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(BaseModel):
    id: UserId
    tenant_id: TenantId
    email: EmailStr
    full_name: str
    role: Role = Role.ANALYST
    avatar_url: str | None = None
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    default_run_mode: str = "precise"
    created_at: datetime

    model_config = {"frozen": True}


__all__ = ["TenantPlan", "Tenant", "Role", "User"]
