from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    policy_id: Optional[str] = None
    name: str
    owner: Optional[str] = None
    status: Optional[str] = "draft"
    language: Optional[str] = "en"
    effective_date: Optional[datetime] = None
    source_url: Optional[str] = None
    content: Optional[str] = None


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None
    language: Optional[str] = None
    effective_date: Optional[datetime] = None
    source_url: Optional[str] = None
    content: Optional[str] = None


class PolicySectionCreate(BaseModel):
    section_ref: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = "draft"
    version: Optional[str] = None


class PolicySectionUpdate(BaseModel):
    section_ref: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None


class InternalRuleCreate(BaseModel):
    internal_rule_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    control_owner: Optional[str] = None
    status: Optional[str] = "draft"
    policy_section_id: Optional[int] = None


class InternalRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    control_owner: Optional[str] = None
    status: Optional[str] = None
    policy_section_id: Optional[int] = None


class InternalRuleMappingCreate(BaseModel):
    monitoring_rule_id: Optional[int] = None
    monitoring_rule_rule_id: Optional[str] = None
    mapping_type: Optional[str] = "transaction_monitoring"
