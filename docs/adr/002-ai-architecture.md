# ADR-002: AI/ML Architecture

## Status

Accepted

## Context

YuFeed needs AI capabilities for:
1. **Regulatory Impact Assessment**: Analyzing how new regulations affect the business
2. **Policy Generation**: Creating compliance policies from regulatory text
3. **Alert Triage**: Prioritizing AML alerts
4. **Natural Language Queries**: Allowing users to ask questions in plain English

Key requirements:
- Handle sensitive financial data securely
- Provide accurate, auditable results
- Scale with user demand
- Control costs

## Decision

We will use a **Hybrid AI Architecture** combining:

1. **Large Language Models (LLM)**: Anthropic Claude for complex reasoning
2. **Vector Database**: Chroma for document embeddings and semantic search
3. **Embeddings**: OpenAI text-embedding-3 for document vectorization
4. **RAG (Retrieval Augmented Generation)**: For context-aware responses

### Architecture

```
User Query → RAG Retriever → Vector DB → Relevant Docs → LLM → Response
                  ↑
           Document Store
           (EUR-Lex, Internal)
```

### Why This Approach?

- **RAG ensures accuracy**: LLM answers based on actual regulatory documents
- **Cost control**: Only send relevant context to expensive LLM calls
- **Auditability**: Can trace which documents influenced the response
- **Privacy**: Sensitive data stays in our vector DB

## Consequences

### Positive

- **High Accuracy**: RAG reduces hallucinations significantly
- **Cost Efficient**: Vector search is cheap, LLM calls are minimized
- **Up-to-date**: Re-index documents when regulations change
- **Explainable**: Can show which documents were used

### Negative

- **Complexity**: More moving parts than direct LLM calls
- **Latency**: Two-step process (retrieve, then generate)
- **Maintenance**: Must keep vector DB synchronized
- **Cost**: Still expensive at scale

### Neutral

- Requires prompt engineering expertise
- Model updates may require re-evaluation

## Alternatives Considered

### Alternative 1: Direct LLM Calls (No RAG)

**Pros:**
- Simpler architecture
- Lower latency
- No vector DB needed

**Cons:**
- Hallucinations on specific regulatory details
- No source attribution
- Expensive for long contexts
- Knowledge cutoff issues

**Why Not:** Accuracy and auditability are critical for compliance.

### Alternative 2: Fine-tuned Model

**Pros:**
- Optimized for our specific domain
- Potentially lower inference costs
- No dependency on external APIs

**Cons:**
- Expensive to train and maintain
- Requires ML expertise
- Hard to keep current with new regulations
- Still needs RAG for document references

**Why Not:** Cost-prohibitive for our current scale.

### Alternative 3: Self-hosted Open Source Models

**Pros:**
- Full data control
- No external API dependency
- Potentially lower per-token costs

**Cons:**
- Complex infrastructure
- Lower quality than Claude/GPT-4
- Significant GPU costs
- Maintenance burden

**Why Not:** Operational complexity outweighs benefits at our scale.

## Implementation

See:
- [RAG Indexer](../../apps/api/src/ai/rag_indexer.py)
- [Impact Analyzer](../../apps/api/src/ai/impact_analyzer.py)
- [Policy Generator](../../apps/api/src/services/policy_generator.py)

## Cost Model

| Component | Cost per 1K Requests | Notes |
|-----------|---------------------|-------|
| Vector Search | $0.10 | Chroma self-hosted |
| Embeddings | $0.02 | OpenAI text-embedding-3-small |
| LLM (Claude) | $3-8 | Depends on context size |
| **Total** | **$3.12-8.12** | Per complex query |

## Privacy & Security

- No PII sent to external LLMs
- Document embeddings are anonymous
- Audit log of all AI interactions
- User consent for AI features

## References

- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [Chroma Vector Database](https://www.trychroma.com/)
- [RAG Pattern](https://www.pinecone.io/learn/retrieval-augmented-generation/)
