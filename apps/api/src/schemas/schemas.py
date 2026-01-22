from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class LegalDocumentBase(BaseModel):
    celex: str
    title: str
    type: Optional[str] = None
    publication_date: Optional[datetime] = None
    entry_into_force_date: Optional[datetime] = None
    status: str = "active"

class LegalDocumentRead(LegalDocumentBase):
    id: int
    last_modified: datetime
    eli: Optional[str] = None
    cellar_id: Optional[str] = None
    
    # Compliance fields
    compliance_domain: Optional[str] = None
    risk_level: Optional[str] = None
    implementation_deadline: Optional[datetime] = None
    jurisdictional_scope: Optional[str] = None
    obligations_json: Optional[List[Dict[str, Any]]] = None
    ai_summary: Optional[str] = None
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2

class NotificationConfig(BaseModel):
    email: bool = True
    push: bool = False

# --- Monitoring Rule Schemas ---
class MonitoringRuleBase(BaseModel):
    rule_id: str
    name: str
    description: Optional[str] = None
    category: str
    severity: str
    priority: int = 3
    enabled: bool = True
    is_template: bool = False
    conditions_json: Dict[str, Any]
    aggregation_json: Optional[Dict[str, Any]] = None
    regulatory_source_id: Optional[int] = None
    regulation_article: Optional[str] = None
    regulatory_requirement: Optional[str] = None

class MonitoringRuleCreate(MonitoringRuleBase):
    pass

class MonitoringRuleRead(MonitoringRuleBase):
    id: int
    alert_count: int
    true_positive_rate: Optional[float]
    false_positive_rate: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Alert & Rule Hit Schemas ---
class RuleHitRead(BaseModel):
    id: int
    rule_id: int
    trigger_values: Dict[str, Any]
    matched_conditions: List[Dict[str, Any]]
    hit_at: datetime

    class Config:
        from_attributes = True

class AlertRead(BaseModel):
    id: int
    alert_id: str
    alert_type: str
    severity: str
    status: str
    priority: int
    transaction_id: Optional[int]
    user_id: str
    description: Optional[str]
    risk_score: Optional[float]
    matched_rules_data: Optional[Dict[str, Any]]
    evidence: Optional[Dict[str, Any]]
    related_regulations: Optional[List[int]]
    regulation_context: Optional[str]
    created_at: datetime
    rule_hits: List[RuleHitRead] = []

    class Config:
        from_attributes = True

# Search Schemas
class SearchResultItem(BaseModel):
    celex: str
    title: str
    publication_date: Optional[datetime] = None
    status: Optional[str] = None
    score: Optional[float] = None

class SearchResponse(BaseModel):
    total: int
    results: List[SearchResultItem]
