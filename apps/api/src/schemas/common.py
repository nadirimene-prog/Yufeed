"""
Common API Schemas

Standardized request/response models for consistency across all endpoints.
"""

from pydantic import BaseModel, Field
from typing import TypeVar, Generic, List, Optional, Any
from datetime import datetime

# Generic type for paginated items
T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum items to return")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response wrapper.

    Use for all list endpoints that support pagination.
    """

    items: List[T]
    total: int = Field(description="Total number of items matching the query")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items returned")
    has_more: bool = Field(description="Whether more items exist beyond this page")

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Use for consistent error formatting across all endpoints.
    """

    error: str = Field(description="Error code/type")
    message: str = Field(description="Human-readable error message")
    detail: Optional[Any] = Field(default=None, description="Additional error details")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracing")


class SuccessResponse(BaseModel):
    """Standard success response for operations without specific return data."""

    success: bool = True
    message: str = Field(description="Success message")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status (ok/degraded/error)")
    service: str = Field(description="Service name")
    version: Optional[str] = Field(default=None, description="Service version")
    timestamp: datetime = Field(description="Current server time")


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""

    total_requested: int = Field(description="Total items in request")
    successful: int = Field(description="Successfully processed items")
    failed: int = Field(description="Failed items")
    errors: Optional[List[dict]] = Field(default=None, description="Details of failures")
