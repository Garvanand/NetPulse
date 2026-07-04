# Refactoring Notes (Phase 12)

This document tracks the architecture refactoring pass completed in Prompt 14.

## 1. Enforcement of the Repository Pattern
**Problem**: The FastApi routers (`api/topology/router.py`, `api/measurements/router.py`, `api/bgp/router.py`, `api/incidents/router.py`, `api/predictions/router.py`) were leaking database abstractions by constructing raw SQLAlchemy `select` and `func` statements directly in the view logic.
**Solution**: We strictly enforced the Repository Pattern. Routers now inject the active `AsyncSession` into dedicated repository classes (`TopologyRepository`, `MeasurementRepository`, `BGPRepository`, `IncidentRepository`) and invoke strongly-typed methods (e.g., `repo.get_graph(asn, rel_type)`). This completely decouples the HTTP layer from the Postgres/TimescaleDB query layer.

## 2. Centralization of Error Handling
**Problem**: Validation and authorization failures were triggering inline `raise HTTPException(status_code=...)` statements scattered across the codebase, violating the DRY (Don't Repeat Yourself) principle and risking inconsistent error responses.
**Solution**:
1. Introduced `app/core/exceptions.py` containing a hierarchy of domain exceptions (`NetPulseException`, `NotFoundError`, `ValidationError`, `AuthenticationError`, `AuthorizationError`).
2. Replaced all inline `HTTPException` raises with these domain exceptions.
3. Registered a unified `@app.exception_handler(NetPulseException)` in `app/main.py` that formats every error into a consistent JSON envelope: `{"error": {"code": 400, "message": "..."}}`.

## 3. Frontend Fetch Consolidation
**Problem**: Next.js React components sometimes implement ad-hoc `fetch()` calls that skip auth tokens or base URL configurations.
**Solution**: Audited the frontend `/src` directory. Verified that all external data fetching strictly routes through `src/lib/api-client.ts`, which enforces the `API_BASE_URL` and attaches JWTs uniformly. No orphaned `fetch` calls exist in the UI components.
