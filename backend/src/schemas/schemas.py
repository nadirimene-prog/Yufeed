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

class WatchlistBase(BaseModel):
    name: str
    mode: str = "email"
    rss_url: Optional[str] = None
    query_json: Dict[str, Any]
    curated_celex_json: Optional[Dict[str, Any]] = None # Using Dict to store generic list/map
    recipients_json: Optional[Dict[str, Any]] = None
    schedule: str = "daily"

class WatchlistCreate(WatchlistBase):
    pass

class WatchlistRead(WatchlistBase):
    id: int

    class Config:
        orm_mode = True

class AlertEventRead(BaseModel):
    id: int
    event_type: str
    detected_at: datetime
    doc_id: int
    watchlist_id: Optional[int] = None

    class Config:
        orm_mode = True

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
