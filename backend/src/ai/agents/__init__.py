"""
AI Agents Module - The AI AML Officer Agent Army

This module contains specialized AI agents that form the backbone of
the AI AML Officer system. Each agent is an expert in a specific domain.

Agents:
- BaseAgent: Foundation class for all agents
- TriageAgent: Real-time alert scoring and prioritization
- InvestigationAgent: Deep-dive alert analysis and evidence gathering
- SARAgent: SAR narrative generation and filing preparation
- NetworkAgent: Graph-based fraud detection
- ComplianceOfficerAgent: Daily briefings and proactive monitoring
"""

from .base import BaseAgent, AgentContext, AgentResult, AgentRegistry
from .investigation import InvestigationAgent
from .sar import SARAgent, SARWorkflowManager, SARDraft, SARStatus
from .compliance_officer import ComplianceOfficerAgent, DailyBriefing, ProactiveAlert
# from .network import NetworkAgent  # Sprint 4

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "AgentRegistry",
    "InvestigationAgent",
    "SARAgent",
    "SARWorkflowManager",
    "SARDraft",
    "SARStatus",
    "ComplianceOfficerAgent",
    "DailyBriefing",
    "ProactiveAlert",
]
