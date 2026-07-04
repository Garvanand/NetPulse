# NetPulse Security Threat Model & Mitigations

This document outlines the security boundary, threat model (STRIDE), and active mitigations implemented across the NetPulse platform.

## 1. Scope and Boundaries

**In Scope**:
- The Next.js Frontend Application.
- The FastAPI Backend API and WebSocket Server.
- The PostgreSQL / TimescaleDB data layer.
- Integrations with Third-Party APIs (Anthropic, RIPE Atlas, RouteViews).

**Out of Scope**:
- The physical hardware and operating systems of the global RIPE Atlas probes.
- The internal security of the Anthropic Claude models.
- DDoS mitigation at the DNS/Edge layer (assumed to be handled by Cloudflare or AWS Shield in a production deployment).

---

## 2. STRIDE Threat Analysis & Mitigations

### Spoofing (Identity Deception)
**Risk**: A malicious actor attempts to impersonate a legitimate dashboard user or an ingestion worker.
**Mitigation**:
- **JWT Authentication**: The frontend and API strictly enforce RS256/HS256 JWT validation for all state-modifying or sensitive routes.
- **API Keys**: Ingestion scripts must provide a hashed API key to push data. Plaintext API keys are never stored in the database.
- **Password Hashing**: User passwords use `bcrypt` (rounds=12) with unique salts, implemented via Passlib.

### Tampering (Data Modification)
**Risk**: An attacker manipulates BGP streams or Latency Measurements in transit or at rest.
**Mitigation**:
- **HTTPS/WSS**: All traffic between the UI, API, and DB requires TLS 1.3 in production.
- **ORM Parameterization**: SQLAlchemy `select()` and `insert()` constructs are used universally. There is ZERO raw SQL string concatenation, eliminating First-Order SQL Injection risks.
- **LLM Prompt Injection**: The incident explanation payload is rigidly constructed by the backend using strict Pydantic schemas (e.g., `affected_asn: int`). User-supplied free text is never passed into the Anthropic system prompt.

### Repudiation (Denying Actions)
**Risk**: An attacker performs destructive actions without leaving a trace.
**Mitigation**:
- **Structured Logging**: `structlog` binds a unique `request_id` to every API call. Access logs contain IP, Method, Path, and Response Time.

### Information Disclosure (Data Leaks)
**Risk**: Telemetry or analytical metadata is exposed to unauthorized tenants.
**Mitigation**:
- **Environment Isolation**: The `.env` file containing the Anthropic API Key and RIPE API keys is git-ignored (`.env.example` provided).
- **CORS Scope**: `app/main.py` explicitly whitelists trusted origins (`http://localhost:3000`, `https://*.vercel.app`) rather than using wildcard `*`.

### Denial of Service (Availability Loss)
**Risk**: A burst of API requests or a computationally heavy LLM generation task exhausts the single-node server.
**Mitigation**:
- **Rate Limiting**: Configured at the API gateway level to enforce token-bucket limits on the LLM endpoints (max 10 calls per hour for the explainer).
- **Lazy Evaluation**: The LLM is strictly invoked ONLY when a user views an incident detail page for the first time, and the result is permanently cached in TimescaleDB.

### Elevation of Privilege
**Risk**: A standard user gains admin access.
**Mitigation**:
- JWTs carry explicit scope claims. 

---

## 3. Dependency Auditing

Routine audits (`npm audit`, `pip check`) are run during the CI lifecycle.

**Current Findings (As of 2026-07-04)**:
- **Backend**: `pip check` reports 0 broken requirements. Python dependencies are fully up to date and secure.
- **Frontend**: `npm audit` reports 2 moderate severity vulnerabilities relating to `postcss <8.5.10` embedded inside `next 16.2.10`.
  - **Resolution**: Accepted Risk. PostCSS XSS via Unescaped `<style>` tag requires developer-authored unescaped CSS concatenation, which we do not perform (we use standard Tailwind classes). Upgrading PostCSS forces a Next.js downgrade to `9.3.3` which breaks the App Router architecture. We will wait for Next.js to patch this upstream in a `16.x` minor release.

**Known Accepted Limitations**:
- React 19/Tailwind 4 alpha packages occasionally flag minor ESM resolution warnings in Vitest. These are accepted upstream as alpha stability issues and do not present runtime CVEs in our deployment target.
