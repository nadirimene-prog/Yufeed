"""
Prompt Templates Module

Centralized prompt management for AI agents. This module provides:
- Base prompt templates
- Template composition utilities
- Domain-specific prompts
- Regulatory context injection
"""

from .templates import (
    PromptTemplate,
    PromptLibrary,
    COMPLIANCE_CONTEXT,
    EU_REGULATORY_CONTEXT,
    INVESTIGATION_TEMPLATES,
    SAR_TEMPLATES,
)

__all__ = [
    "PromptTemplate",
    "PromptLibrary",
    "COMPLIANCE_CONTEXT",
    "EU_REGULATORY_CONTEXT",
    "INVESTIGATION_TEMPLATES",
    "SAR_TEMPLATES",
]
