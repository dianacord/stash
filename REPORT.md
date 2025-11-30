# Stash DevOps Assignment 2 Report

## 1. Introduction
The objective of Assignment 2 was to evolve an existing FastAPI + frontend application ("Stash") into a production-oriented system exhibiting core DevOps capabilities: automated testing with coverage enforcement, containerization, continuous integration and deployment on Azure App Service, secret management, health and metrics endpoints, and improved code quality through refactoring and SOLID principles. The baseline application already extracted YouTube transcripts and (optionally) generated AI-powered adaptive summaries via the Groq API. This assignment layer focused on operational hardening: making the system observable, repeatable, deployable, and maintainable.

Key deliverables included:
- CI pipeline (pytest, coverage threshold, Docker build validation)
- CD pipeline (Azure authentication, ACR push, Web App container deployment)
- Docker image (slim base, deterministic startup)
- Secret handling via GitHub Actions and runtime `.env`
- Health endpoint (`/api/health`) and Prometheus metrics endpoint (`/api/metrics`)
- Structured tests with >70% coverage
- Application of SOLID, dependency inversion, and removal of code smells
- Documentation (README + this report)

## 2. Code Quality Improvements
### 2.1 Refactoring Strategy
Refactoring goals were: isolate responsibilities, enable testability of business logic without HTTP server boot, simplify error propagation, and reduce implicit dependencies. Previously, logic for fetching transcripts, summarizing content, and storing records risked being interwoven with route handlers. The refactoring introduced a clear layering:
- **Controller Layer**: FastAPI route functions in `backend/main.py` – thin orchestration only.
- **Service Layer**: Business logic in dedicated classes (`VideoService`, `AuthService`). Services coordinate workflow (e.g., transcript fetch + optional summarization + persistence). Each service returns structured dictionaries (`{"success": ..., "data": ...}`) for predictable error handling.
- **Infrastructure Layer**: Persistence (`DatabaseService`), external AI (`GroqSummarizer`), transcript acquisition (`YouTubeFetcher`), and metrics (`MetricsService`).
- **Dependency Container**: `ServiceContainer` in `dependencies.py` centralizes construction while gracefully handling optional components (e.g., summarizer absent if API key missing).

### 2.2 SOLID Principles Applied
| Principle | Application | Outcome |
|-----------|------------|---------|
| Single Responsibility | `VideoService` only coordinates video-related operations; `YouTubeFetcher` only handles retrieval/parsing; `GroqSummarizer` only summarizes transcripts. | Classes easier to reason about & test in isolation. |
| Open/Closed | Protocol-based abstraction (`protocols.py`) allows adding other fetchers (e.g., Vimeo) or summarizers without modifying existing consumers. | Extensible features without disruptive changes. |
| Liskov Substitution | Protocols (structural types) define expected methods (`fetch`, `summarize`) so alternate implementations can substitute seamlessly. | Future adapters drop in without failing client expectations. |
| Interface Segregation | Separate protocols for repository, fetcher, summarizer prevent bloated interfaces on simple services. | Minimal required method surface area. |
| Dependency Inversion | High-level services depend on protocol abstractions, not concrete implementations; container wires concrete classes. | Looser coupling promoting test doubles and easier evolution.

### 2.3 Dependency Injection
`ServiceContainer` constructs dependencies once and exposes accessor functions (e.g., `get_video_service`). FastAPI’s `Depends` integrates with these provider functions. Benefits:
- Centralized lifecycle management (single DB service instance, single metrics registry).
- Optional service handling – summarizer initialization guarded with exception capture; health endpoint can expose availability flag.
- Clean test setup – fixtures can override providers or inject mocks.

### 2.4 Removing Code Smells
| Smell | Resolution | Benefit |
|-------|------------|---------|
| God functions / large route logic | Moved logic to services; controllers only validate inputs and map errors to HTTP. | Reduced duplication; simpler surface for tests. |
| Implicit global state | Replaced ad-hoc instantiation with container; explicit singletons only for metrics & DI container. | Predictable initialization, clearer dependency graph. |
| Mixed responsibilities (data access + business rules) | Separation: repository-like operations confined to `DatabaseService`; assembly in `VideoService`. | Higher cohesion & clarity. |
| Unclear error propagation | Services standardize response dict shape; controllers translate to HTTP codes. | Consistent failure semantics aiding tests & observability. |
| Hard-coded branching for transcript shapes | Normalization helper `_join_text_from_payload` consolidates shape conversion. | Reduced conditional complexity & duplication.

### 2.5 Additional Improvements
- Added histogram buckets for request latency (`MetricsService`) chosen to reflect both sub-100ms fast paths and multi-second slow calls.
- Simplified summarization prompt construction and truncated transcript length for cost control & determinism.
- Adopted type hints broadly to assist static analysis and readability.
- Introduced consistent automated formatting + linting using **Ruff** (configured in `pyproject.toml`). Each commit/PR was formatted and linted to enforce import ordering (isort), pyflakes checks, bugbear warnings, comprehension simplifications, and modernization (pyupgrade). Non-critical or framework-specific patterns (e.g., FastAPI dependency defaults) were selectively ignored. This reduced stylistic noise in reviews and kept diffs focused on logical changes.

## 3. Testing Improvements
### 3.1 Test Layers
- **Unit Tests**: Target services in isolation (`test_youtube_fetcher_unit.py`, `test_database_service_unit.py`, `test_auth_service_unit.py`). These validate pure business logic (e.g., user signup error when username exists, video ID extraction robustness).
- **Integration Tests**: Exercise API endpoints (`test_api.py`) through FastAPI’s test client with dependency injection in place (JWT issuance, video creation flow).
- **Edge Cases**: Transcript failure paths, duplicate video saves, invalid token scenarios, summarizer absence.

### 3.2 Coverage Results
The suite exceeds the required 70% (observed ~80%). High coverage was achieved by:
- Testing both success and failure paths of video save (existing video, transcript failure, summarizer optional).
- Verifying JWT token creation & validation (auth flows).
- Exercising normalization logic for transcript payload variations.
- Covering metrics middleware indirectly via endpoint hits (request counters & error classification).

### 3.3 Representative Test Case Examples
| Test | Focus | Assertion |
|------|-------|----------|
| `test_save_video_transcript_success` | Full save path with transcript | Response success + data fields present. |
| `test_save_video_transcript_duplicate` | Duplicate video handling | Returns existing record message not error. |
| `test_auth_signup_and_login_flow` | Credential lifecycle | Token returned, subsequent authenticated call succeeds. |
| `test_youtube_id_extraction_variants` | Robust URL parsing | Short & standard forms yield consistent IDs. |
| `test_metrics_endpoint_available` | Monitoring surface | `/api/metrics` returns Prometheus content type. |

### 3.4 Quality Gates
CI conceptually enforces:
- Test pass/fail gating merges.
- Coverage threshold (≥70%) – failing secondary action halts build.
- Docker build viability ensures runtime dependencies resolve before deployment.

## 4. Continuous Integration Pipeline
### 4.1 Workflow Overview
Triggered on pull requests and pushes to `main`. Typical steps:
1. Checkout repository.
2. Setup Python (defined version matrix optional, here single 3.12).
3. Install dependencies (`pip install -r requirements.txt`).
4. Run pytest with coverage; capture exit code.
5. (Optional) Upload coverage artifact or annotate summary.
6. Build Docker image to validate Dockerfile correctness (without push on PR).

### 4.2 Rationale
- Early feedback loop for contributors (red/green visibility).
- Prevents broken container specifications from reaching CD stage.
- Surfaces regression risk via coverage trends (quality metric).

### 4.3 Automation Guarantees
- Repeatable environment (clean container-like dependencies each run).
- Deterministic pass criteria (coverage threshold numeric and objective).
- Security: secrets only exposed on trusted branches (avoid PR exfiltration by restricting secret usage to `main` push or approved conditions).

## 5. Continuous Deployment Pipeline
### 5.1 Flow
Deployment triggers only after successful CI on `main`:
1. Azure authentication (`azure/login`) via service principal or OIDC federation.
2. Login to ACR (`az acr login`); ensures ability to push.
3. Build image tagged with commit SHA and optionally `latest`.
4. Push tags to ACR.
5. Update App Service configuration pointing to new image (either via `az webapp create` initially or `az webapp config container set` on updates).
6. (Optional) Run post-deploy health probe (`curl /api/health`) to confirm readiness.

### 5.2 Security & Stability Considerations
- Principle of least privilege: Service principal assigned only required roles (`AcrPush`, `WebApp Contributor`).
- Rollback via redeploying previous image tag (maintain tag history).
- Deployment restricted to `main` to prevent accidental production changes.

### 5.3 Secrets Handling
Secrets accessed only in deployment job; environment separation ensures test jobs cannot echo them. OIDC reduces need to store `AZURE_CLIENT_SECRET` if configured.

## 6. Containerization
### 6.1 Dockerfile Analysis
Key choices:
- **Base Image**: `python:3.12-slim` reduces surface area and image size vs full Debian.
- **Layer Caching**: Dependencies installed before copying full source – faster rebuilds when code changes but requirements unchanged.
- **System Dependencies**: Minimal packages (`build-essential`, `libffi-dev`) for cryptography/possible wheels; removed apt lists to reduce size.
- **Environment Variables**: `PYTHONDONTWRITEBYTECODE` & `PYTHONUNBUFFERED` improve container logging behavior and avoid stray `.pyc`.
- **Entrypoint**: Uvicorn directly (single process) – acceptable for lightweight assignment; in production could pair with process manager or use multiple workers.
- **Port Exposure**: 8000 consistent across local and cloud.

### 6.2 Potential Multi-Stage Considerations
A future improvement could compile wheels in a builder stage and copy site-packages to a smaller final image (e.g., `distroless` or `python:slim` without build tools). For current assignment complexity, single stage is adequate.

### 6.3 Image Slimming & Security Options
- Remove build tooling after installs (already done by ephemeral layer strategy).
- Consider `--no-cache-dir` (already used) to eliminate pip cache.
- Add non-root user for defense-in-depth (future enhancement).

## 7. Monitoring & Observability
### 7.1 Health Endpoint (`/api/health`)
Returns JSON including:
- `status`: simple heartbeat
- `service`: identifier (`stash-api`)
- `groq_summarizer`: boolean flag indicating whether summarizer initialized (depends on `GROQ_API_KEY`).
This enables deployment validation and feature availability detection (front-end can degrade gracefully if summarizer is absent).

### 7.2 Metrics Endpoint (`/api/metrics`)
Prometheus exposition format includes:
- `http_requests_total` (labelled by method, path pattern, status_code)
- `http_request_duration_seconds` (histogram with fine-grained buckets from 5ms to 10s)
- `http_errors_total` (error volume for 4xx/5xx differentiation)

### 7.3 Middleware Integration
Custom `PrometheusMiddleware` wraps each request, capturing start time and labels via route pattern (reduces cardinality vs raw paths). Metrics service excludes self-scraping for `/api/metrics` to avoid recursion and pollution.

### 7.4 Observability Outcomes
- Latency distributions facilitate SLO setting (e.g., 95% under 250ms for GET endpoints).
- Error counters distinguish systemic vs user input issues through status codes.
- Simple health status quickly reveals summarizer operational state (missing key vs functioning).

## 8. Proxy Integration Attempt (ScraperAPI)
### 8.1 Motivation
Direct transcript extraction can fail when YouTube throttles or restricts requests from predictable cloud IP ranges. A proxy (e.g., ScraperAPI) can rotate IP addresses and handle anti-bot challenges.

### 8.2 Observed Limitations
- **Code Not Present in Current Branch**: The experimental ScraperAPI integration code was intentionally **removed** after evaluation because reliability was inconsistent. It can be reviewed in the commit history (earlier feature attempts) but is excluded now to keep the deployed artifact stable and lean.
- **Partial Success**: Some videos accessible; others still blocked due to dynamic JavaScript-based checks beyond simple IP rotation.
- **Latency Increase**: Additional network hop adds measurable delay (~300–800ms typical).
- **Cost & Quotas**: Proxy usage introduces rate limits and potential billing concerns.

### 8.3 Fallback Strategy
If proxy retrieval fails, the system falls back to direct library access (current implementation gracefully returns an error structure). Errors are surfaced in API response (`success: false, error_type`). The front-end or subsequent logic can interpret failure and prompt user to try alternative videos.

### 8.4 Future Mitigations
- Introduce exponential backoff + alternative language code attempts.
- Cache successful transcripts to minimize repeated external calls.
- Pre-flight HEAD request to detect potential blocking early.

### 8.5 Error Handling Rationale
Returning structured failures rather than raising raw exceptions allows downstream layers (controllers, tests) to assert behavior deterministically without brittle stack inspection.

## 9. Conclusion
### 9.1 Achievements
The Stash application now embodies core DevOps pillars: automated testing with strong coverage, reproducible container builds, CI/CD workflows, explicit secret handling, and baseline observability (health + metrics). The refactored architecture demonstrates SOLID principles and clean separation of concerns enabling isolated testability and future extensibility (new platforms, alternative summarizers).

### 9.2 Remaining Limitations
- No background processing for long-running summarizations (could block request thread).
- Single-process Uvicorn instance limits concurrency under heavy load.
- Lack of structured logging and distributed tracing (metrics only provide aggregate view).
- Proxy integration incomplete; not fully resilient to advanced anti-bot mechanisms.
- Security hardening (non-root container user, rate limiting, CORS tightening) could be improved.

### 9.3 Forward-Looking Improvements
1. Add Celery or FastAPI background tasks for async summarization.
2. Integrate OpenTelemetry for traces + log correlation with metrics.
3. Multi-stage Docker build & non-root runtime user.
4. Implement pagination + indexing strategy for large transcript sets.
5. Adopt feature flags (e.g., summarizer model variant selection).
6. Introduce automated performance tests in CI (e.g., Locust smoke test stage).

### 9.4 Summary
This assignment elevated Stash from a functional prototype to an operationally aware, deployable service. The introduced pipelines, containerization, and observability foundations reduce deployment friction, shorten feedback cycles, and prepare the application for incremental scaling. The combination of architectural refactoring and DevOps instrumentation supports maintainability and lays groundwork for production-grade evolution.

---
*End of Report*
