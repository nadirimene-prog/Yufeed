"""
Base Agent Class - Foundation for all AI AML Officer Agents

This module provides the foundational architecture for specialized AI agents.
Each agent extends BaseAgent and implements domain-specific logic while
inheriting common functionality like Claude API integration, logging,
error handling, and context management.

Architecture:
- AgentContext: Carries conversation history, user context, and session state
- AgentResult: Standardized output format with reasoning chain and citations
- BaseAgent: Abstract base class with Claude integration and common utilities
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic
import json
import logging
import os
import hashlib
from anthropic import Anthropic

from src.core.circuit_breaker import CircuitOpenError, anthropic_breaker


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of AI agents in the AML Officer system."""

    TRIAGE = "triage"
    INVESTIGATION = "investigation"
    SAR = "sar"
    NETWORK = "network"
    COMPLIANCE_OFFICER = "compliance_officer"
    REGULATORY = "regulatory"


class ConfidenceLevel(str, Enum):
    """Confidence levels for agent outputs."""

    HIGH = "high"  # >0.8 - Can auto-act
    MEDIUM = "medium"  # 0.5-0.8 - Needs review
    LOW = "low"  # <0.5 - Manual required


class ActionRecommendation(str, Enum):
    """Standard action recommendations from agents."""

    ESCALATE = "escalate"
    INVESTIGATE = "investigate"
    RESOLVE = "resolve"
    FALSE_POSITIVE = "false_positive"
    FILE_SAR = "file_sar"
    MONITOR = "monitor"
    NO_ACTION = "no_action"


@dataclass
class Citation:
    """A regulatory citation supporting an agent's conclusion."""

    source_type: str  # "regulation", "internal_policy", "case_precedent"
    reference: str  # e.g., "AMLD 5, Article 13"
    celex_id: Optional[str] = None
    excerpt: Optional[str] = None
    relevance_score: float = 1.0


@dataclass
class ReasoningStep:
    """A single step in the agent's chain-of-thought reasoning."""

    step_number: int
    description: str
    evidence: List[str] = field(default_factory=list)
    conclusion: Optional[str] = None
    confidence: float = 1.0


@dataclass
class AgentContext:
    """
    Context passed to agents for processing.

    Contains all information the agent needs to perform its task,
    including conversation history, user identity, and session state.
    """

    # Core identifiers
    session_id: str
    user_id: Optional[str] = None
    user_role: Optional[str] = None

    # Conversation history for multi-turn interactions
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Current task context
    task_type: Optional[str] = None
    task_id: Optional[str] = None

    # Data payloads (alert, case, transaction, etc.)
    primary_data: Optional[Dict[str, Any]] = None
    related_data: List[Dict[str, Any]] = field(default_factory=list)

    # Regulatory context
    applicable_regulations: List[Dict[str, Any]] = field(default_factory=list)

    # Agent chain context (for multi-agent workflows)
    previous_agent_results: List["AgentResult"] = field(default_factory=list)

    # Configuration
    max_tokens: int = 4096
    temperature: float = 0.3  # Lower for more deterministic compliance outputs

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append(
            {"role": role, "content": content, "timestamp": utc_now().isoformat()}
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "task_type": self.task_type,
            "task_id": self.task_id,
            "primary_data": self.primary_data,
            "related_data": self.related_data,
            "applicable_regulations": self.applicable_regulations,
            "conversation_history": self.conversation_history,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentResult:
    """
    Standardized result from an AI agent.

    All agents return this format to ensure consistent handling,
    audit trail creation, and downstream processing.
    """

    # Agent identification
    agent_type: AgentType
    agent_version: str = "1.0.0"

    # Core output
    success: bool = True
    recommendation: Optional[ActionRecommendation] = None
    summary: str = ""
    detailed_analysis: str = ""

    # Confidence and reasoning
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    reasoning_chain: List[ReasoningStep] = field(default_factory=list)

    # Regulatory compliance
    citations: List[Citation] = field(default_factory=list)
    regulatory_context: Optional[str] = None

    # Risk assessment
    risk_score: Optional[float] = None
    risk_factors: List[str] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)

    # Red flags and indicators
    red_flags: List[str] = field(default_factory=list)

    # Action items
    next_steps: List[str] = field(default_factory=list)
    required_actions: List[Dict[str, Any]] = field(default_factory=list)

    # SAR-specific fields
    sar_likelihood: Optional[float] = None
    sar_narrative: Optional[str] = None

    # Metadata
    processing_time_ms: int = 0
    tokens_used: int = 0
    model_used: str = ""

    # Error handling
    error_message: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API response."""
        return {
            "agent_type": self.agent_type.value,
            "agent_version": self.agent_version,
            "success": self.success,
            "recommendation": self.recommendation.value if self.recommendation else None,
            "summary": self.summary,
            "detailed_analysis": self.detailed_analysis,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "reasoning_chain": [
                {
                    "step": s.step_number,
                    "description": s.description,
                    "evidence": s.evidence,
                    "conclusion": s.conclusion,
                    "confidence": s.confidence,
                }
                for s in self.reasoning_chain
            ],
            "citations": [
                {
                    "source_type": c.source_type,
                    "reference": c.reference,
                    "celex_id": c.celex_id,
                    "excerpt": c.excerpt,
                    "relevance_score": c.relevance_score,
                }
                for c in self.citations
            ],
            "regulatory_context": self.regulatory_context,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "mitigating_factors": self.mitigating_factors,
            "red_flags": self.red_flags,
            "next_steps": self.next_steps,
            "required_actions": self.required_actions,
            "sar_likelihood": self.sar_likelihood,
            "sar_narrative": self.sar_narrative,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def error(cls, agent_type: AgentType, message: str) -> "AgentResult":
        """Create an error result."""
        return cls(
            agent_type=agent_type,
            success=False,
            error_message=message,
            confidence_level=ConfidenceLevel.LOW,
        )


T = TypeVar("T", bound=AgentResult)


class BaseAgent(ABC, Generic[T]):
    """
    Abstract base class for all AI AML Officer agents.

    Provides common functionality:
    - Claude API integration with proper error handling
    - Prompt template management
    - Reasoning chain construction
    - Citation extraction
    - Audit logging
    - Rate limiting and caching

    Subclasses must implement:
    - agent_type: The type of agent
    - system_prompt: The system prompt for Claude
    - process(): The main processing logic
    """

    # Class-level configuration
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    FALLBACK_MODEL = "claude-3-haiku-20240307"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_caching: bool = True,
    ):
        """Initialize the agent with Claude API client."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.is_configured = bool(self.api_key)

        if not self.is_configured:
            logger.warning(
                f"ANTHROPIC_API_KEY not found for {self.agent_type.value} agent. "
                "Operating in Demo Mode."
            )
            self.client = None
        else:
            self.client = Anthropic(api_key=self.api_key)
        self.model = model or self.DEFAULT_MODEL
        self.enable_caching = enable_caching
        self._cache: Dict[str, AgentResult] = {}

        logger.info(f"Initialized {self.agent_type.value} agent with model {self.model}")

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @property
    def agent_version(self) -> str:
        """Return the version of this agent."""
        return "1.0.0"

    @abstractmethod
    async def process(self, context: AgentContext) -> T:
        """
        Main processing method - must be implemented by subclasses.

        Args:
            context: The agent context with all necessary data

        Returns:
            AgentResult with the agent's analysis and recommendations
        """
        pass

    def _get_cache_key(self, context: AgentContext) -> str:
        """Generate a cache key for the context."""
        data = json.dumps(context.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    def _check_cache(self, context: AgentContext) -> Optional[AgentResult]:
        """Check if result is cached."""
        if not self.enable_caching:
            return None
        key = self._get_cache_key(context)
        return self._cache.get(key)

    def _set_cache(self, context: AgentContext, result: AgentResult) -> None:
        """Cache a result."""
        if self.enable_caching:
            key = self._get_cache_key(context)
            self._cache[key] = result

    async def call_claude(
        self,
        user_prompt: str,
        context: AgentContext,
        json_mode: bool = True,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call Claude API with proper error handling.

        Args:
            user_prompt: The user message to send
            context: Agent context for additional info
            json_mode: Whether to request JSON output
            max_tokens: Override max tokens

        Returns:
            Parsed response content
        """
        import time

        start_time = time.time()

        messages = []

        # Add conversation history if present
        for msg in context.conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user prompt
        messages.append({"role": "user", "content": user_prompt})

        if not self.is_configured:
            return self._generate_mock_response(user_prompt)

        try:
            # Wrap the Anthropic API call with the circuit breaker so that
            # repeated failures (timeouts, 5xx, etc.) cause fast-fail instead
            # of piling up slow requests.
            response = anthropic_breaker.call(
                self.client.messages.create,
                model=self.model,
                max_tokens=max_tokens or context.max_tokens,
                temperature=context.temperature,
                system=self.system_prompt,
                messages=messages,
            )

            text_chunks: List[str] = []
            for block in response.content:
                maybe_text = getattr(block, "text", None)
                if isinstance(maybe_text, str):
                    text_chunks.append(maybe_text)
            content = "\n".join(text_chunks).strip()
            processing_time = int((time.time() - start_time) * 1000)

            logger.info(
                f"{self.agent_type.value} agent completed in {processing_time}ms, "
                f"tokens: {response.usage.input_tokens + response.usage.output_tokens}"
            )

            # Parse JSON if requested
            if json_mode:
                try:
                    # Handle potential markdown code blocks
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]

                    parsed = json.loads(content.strip())
                    parsed["_meta"] = {
                        "processing_time_ms": processing_time,
                        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                        "model_used": self.model,
                    }
                    return parsed
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}")
                    return {
                        "raw_content": content,
                        "_meta": {
                            "processing_time_ms": processing_time,
                            "tokens_used": response.usage.input_tokens
                            + response.usage.output_tokens,
                            "model_used": self.model,
                            "json_parse_error": str(e),
                        },
                    }

            return {
                "content": content,
                "_meta": {
                    "processing_time_ms": processing_time,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "model_used": self.model,
                },
            }

        except CircuitOpenError:
            logger.warning(
                f"{self.agent_type.value} agent: Anthropic circuit breaker is "
                f"OPEN -- returning mock/fallback response"
            )
            mock = self._generate_mock_response(user_prompt)
            mock["_meta"]["circuit_breaker"] = "open"
            return mock

        except Exception as e:
            logger.error(f"{self.agent_type.value} agent error: {e}")
            raise

    def _generate_mock_response(self, user_prompt: str) -> Dict[str, Any]:
        """Generate a mock response when API key is missing."""
        logger.info(f"Generating mock response for {self.agent_type.value} agent")

        # Simple generic mock response based on agent type
        mock_data = {
            "critical_findings": ["Demo Mode: No API key configured"],
            "recommendation": "investigate",
            "confidence": 0.5,
            "summary": (
                f"This is a demo response from the {self.agent_type.value} agent. "
                "Please configure ANTHROPIC_API_KEY for real AI analysis."
            ),
            "detailed_analysis": (
                "In a production environment with a valid API key, this would contain "
                "a deep-dive analysis of the regulatory implications and risk factors. "
                "Currently, the system is operating in demonstration mode."
            ),
            "risk_score": 50.0,
            "red_flags": ["DEMO_MODE_ACTIVE"],
            "next_steps": ["Configure ANTHROPIC_API_KEY", "Verify system connectivity"],
            "citations": [
                {
                    "source_type": "internal",
                    "reference": "System Configuration Manual",
                    "excerpt": "Ensure all required environment variables are set.",
                }
            ],
            "reasoning": [
                {
                    "description": "System check",
                    "evidence": ["Missing API key"],
                    "conclusion": "Operating in fallback mode",
                    "confidence": 1.0,
                }
            ],
        }

        mock_data["_meta"] = {
            "processing_time_ms": 100,
            "tokens_used": 0,
            "model_used": "demo-fallback",
        }

        return mock_data

    def build_reasoning_chain(self, steps: List[Dict[str, Any]]) -> List[ReasoningStep]:
        """Build a structured reasoning chain from raw steps."""
        return [
            ReasoningStep(
                step_number=i + 1,
                description=step.get("description", ""),
                evidence=step.get("evidence", []),
                conclusion=step.get("conclusion"),
                confidence=step.get("confidence", 1.0),
            )
            for i, step in enumerate(steps)
        ]

    def build_citations(self, raw_citations: List[Dict[str, Any]]) -> List[Citation]:
        """Build structured citations from raw data."""
        return [
            Citation(
                source_type=c.get("source_type", "regulation"),
                reference=c.get("reference", ""),
                celex_id=c.get("celex_id"),
                excerpt=c.get("excerpt"),
                relevance_score=c.get("relevance_score", 1.0),
            )
            for c in raw_citations
        ]

    def calculate_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to level."""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def should_auto_act(self, result: AgentResult) -> bool:
        """
        Determine if the agent's recommendation can be auto-executed.

        Based on semi-autonomous configuration:
        - Auto-resolve if confidence > 0.9 and recommendation is FALSE_POSITIVE
        - Auto-escalate if confidence > 0.8 and recommendation is ESCALATE
        """
        if result.confidence_level != ConfidenceLevel.HIGH:
            return False

        if result.recommendation == ActionRecommendation.FALSE_POSITIVE:
            return result.confidence >= 0.9

        if result.recommendation == ActionRecommendation.ESCALATE:
            return result.confidence >= 0.8

        return False


class AgentRegistry:
    """Registry for managing and accessing agent instances."""

    _agents: Dict[AgentType, BaseAgent] = {}

    @classmethod
    def register(cls, agent_type_str: str = None):
        """Register an agent class as a decorator or register an instance."""

        def decorator(agent_class):
            # Return the class unchanged - actual registration happens on instantiation
            return agent_class

        # If called with a string argument, return decorator
        if isinstance(agent_type_str, str):
            return decorator
        # If called with an agent instance, register it
        elif agent_type_str is not None:
            agent = agent_type_str
            cls._agents[agent.agent_type] = agent
            logger.info(f"Registered {agent.agent_type.value} agent")
        return decorator

    @classmethod
    def get(cls, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent by type."""
        return cls._agents.get(agent_type)

    @classmethod
    def all_agents(cls) -> List[BaseAgent]:
        """Get all registered agents."""
        return list(cls._agents.values())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents."""
        cls._agents.clear()
