# ADR-0004: LLM Usage Boundary — Explanation Only

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** NetPulse architecture review

---

## Context

NetPulse detects and predicts internet instability using a combination of
statistical anomaly detection, time-series forecasting, and graph neural
networks. When an incident is confirmed, users benefit from a **natural-language
explanation** of the probable root cause — something like:

> "Elevated latency and packet loss observed across AS 3356 (Level3/Lumen)
> and downstream customers, coinciding with a BGP path change that withdrew
> 47 prefixes from the affected region. This pattern is consistent with a
> fiber cut or upstream provider depeering event."

Large Language Models (LLMs) excel at generating these summaries from structured
data. However, LLMs introduce cost, latency, non-determinism, and hallucination
risk. This ADR defines a strict boundary for LLM usage.

## Decision

The LLM (Claude API, Anthropic) is used **exclusively for post-hoc incident
explanation**. It is **never** used for detection, prediction, anomaly scoring,
or any decision-making in the system.

### Explicit Scope

**The LLM IS used for:**
1. Generating a 2–3 sentence natural-language root-cause hypothesis for a
   **confirmed** incident.
2. Input: structured JSON containing:
   - Affected ASNs and their relationships
   - Affected probes and their measurements (RTT, packet loss)
   - BGP events (withdrawals, path changes, origin changes)
   - Anomaly scores and prediction confidence
   - Temporal context (when it started, duration, trend)
3. Output: cached text stored in `incidents.explanation` column.

**The LLM is NOT used for:**
- Anomaly detection or scoring
- Instability prediction or forecasting
- BGP event classification or filtering
- Incident severity determination or escalation
- Data ingestion, parsing, or transformation
- Any real-time decision that affects system behavior
- Processing user-submitted text or queries
- Any purpose beyond generating explanation text

### Operational Constraints

| Constraint | Value | Rationale |
|---|---|---|
| Max calls per hour | 10 | Cost control; incidents are rare |
| Min incident severity for explanation | MEDIUM | LOW incidents don't justify LLM cost |
| Cache TTL | 24 hours | Explanations don't change; avoid re-generation |
| Cache strategy | Write-through to `incidents.explanation` | Persistent; survives restarts |
| Batch policy | Related incidents batched into single call | e.g., 5 ASes in same upstream → 1 call |
| Fallback on failure | Serve incident without explanation | Structured data always available |
| Model | Claude (configurable) | Chosen for structured-data summarization quality |
| Max input tokens | ~2,000 (structured JSON) | Bounded by incident context size |
| Max output tokens | ~300 (2–3 sentences) | Short, focused explanation |

## Consequences

### Positive

- **Predictable cost** — bounded at 10 calls/hour × ~2,300 tokens per call.
  At Claude Sonnet pricing (~$3/M input, ~$15/M output tokens), worst case is
  ~$0.50/day even during a major outage. Monthly budget: <$15.
- **No hallucination in critical path** — the LLM never influences detection,
  prediction, or escalation. If it hallucinates a root cause, the structured
  incident data (ASNs, prefixes, BGP events) is always available as ground truth.
- **Graceful degradation** — if the Claude API is down, rate-limited, or budget
  is exhausted, the system continues operating with full functionality minus
  explanation text. No operational impact.
- **No latency impact** — explanation generation is asynchronous (fire-and-forget
  after incident creation). The incident is visible to users immediately; the
  explanation appears when the LLM call completes (typically 1–3 seconds later).
- **Auditability** — every LLM call is logged with input hash, output, latency,
  and cost. The explanation is a cached artifact, not a live computation.

### Negative

- **Limited LLM value** — the LLM is deliberately underutilized. It could
  potentially assist with trend summarization, report generation, or
  natural-language queries. These use cases are explicitly deferred (not rejected)
  to future versions.
- **Explanation quality depends on input structure** — the LLM can only reason
  about what it's given. If the structured JSON is incomplete (e.g., missing
  BGP events due to ingestion lag), the explanation may be less accurate.
  Mitigated by including data-completeness signals in the input.

## Alternatives Considered

### LLM for Anomaly Detection / Classification

- **Pro:** Could potentially detect subtle patterns in BGP update sequences
  or latency signatures that statistical methods miss.
- **Con:** Non-deterministic; high latency for real-time detection; expensive
  at the volume of BGP events (~1K/sec); hallucination risk in a critical
  detection path; impossible to validate or unit-test reliably.
- **Rejected:** The statistical + GNN approach provides deterministic,
  auditable, fast detection. LLM non-determinism is unacceptable in the
  detection loop.

### No LLM at All

- **Pro:** Zero external API dependency; zero cost; fully self-contained.
- **Con:** Users see raw incident data (ASN lists, BGP event counts, anomaly
  scores) without context. Technical users can interpret this; general users
  cannot. Natural-language explanations significantly improve incident
  comprehension and are a key differentiator for NetPulse.
- **Rejected:** The explanation layer is a high-value, low-cost feature when
  properly bounded.

### LLM for Natural-Language Queries

- **Pro:** Users could ask "what happened to AS 3356 yesterday?" and get a
  conversational answer.
- **Con:** Requires prompt engineering, RAG pipeline, or function-calling
  integration. Significant additional complexity. Opens attack surface
  (prompt injection). Not essential for MVP.
- **Deferred:** May be added in a future version after the core platform
  is stable.

### Template-Based Explanations (No LLM)

- **Pro:** Deterministic; zero cost; no external dependency.
- **Con:** Templates are rigid and produce formulaic explanations that lack
  nuance. "AS 3356 experienced elevated latency" is less useful than an LLM's
  ability to synthesize BGP path changes, geographic context, and historical
  patterns into a coherent narrative.
- **Rejected:** LLM explanations are meaningfully better for incident
  comprehension, and the bounded usage keeps cost negligible.
