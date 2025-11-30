<div align="center">

# Stash

Organize saved YouTube videos with transcript extraction, AI summarization, authentication, metrics, and production-ready DevOps (CI/CD + containerization) on Azure.

</div>

## 1. Overview
Stash tackles the “save for later but never revisit” problem. Users save a YouTube URL; the backend extracts the transcript, optionally summarizes it via Groq’s Llama model, and persists structured information. This assignment extends the original app by adding: automated testing & coverage gates, Docker image builds, GitHub Actions CI/CD, secret management, health/metrics endpoints, and improved code quality (SOLID + dependency injection).

## 2. Repository / Folder Structure
```
├── backend/                # FastAPI app (routes in main.py, DI in dependencies.py)
│   ├── main.py             # Entrypoint + HTTP controllers
│   ├── metrics.py          # Prometheus metrics service & endpoint path
│   ├── dependencies.py     # ServiceContainer (dependency injection)
│   ├── protocols.py        # Structural typing (Protocols) for inversion
│   └── services/           # Business + infrastructure services
│       ├── auth_service.py     # JWT creation & password hashing
│       ├── user_service.py     # Auth/business logic layer
│       ├── database.py         # SQLite persistence (users + saved_videos)
│       ├── youtube_fetcher.py  # Transcript retrieval & normalization
│       └── groq_summarizer.py  # AI summarization (optional if key present)
├── frontend/               # Thin static UI served separately (index.html)
├── tests/                  # Unit + integration tests (services + API)
├── Dockerfile              # Production container image definition
├── requirements*.txt       # Runtime / dev dependencies
├── pyproject.toml          # Project metadata (if needed for tooling)
├── docs/                   # Diagrams or supplementary documentation
└── htmlcov/                # Generated coverage HTML (after CI/test run)
```

## 3. Clone & Local Setup
Prerequisites: Python 3.12+, Git.
```bash
git clone https://github.com/dianacord/stash.git
cd stash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # then edit values
```
SQLite database (`stash.db`) auto-creates on first run.

## 4. Run Locally
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Access:
- API Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/api/health
- Metrics: http://localhost:8000/api/metrics
Frontend: open `frontend/index.html` directly or serve via a simple static server (the root `/` returns the file through FastAPI).

## 5. Tests & Coverage
Run full suite:
```bash
PYTHONPATH=. pytest -v
```
Coverage (threshold > 70% enforced conceptually in CI):
```bash
PYTHONPATH=. pytest -v --cov=backend --cov-report=term --cov-report=html
open htmlcov/index.html  # macOS
```
Targeted tests:
```bash
PYTHONPATH=. pytest tests/test_api.py::test_save_video_transcript_success -v
```

## 6. Docker: Build & Run Locally
Dockerfile produces a slim Python 3.12 image.
```bash
docker build -t stash:local .
docker run --rm -p 8000:8000 --env-file .env stash:local
```
Then visit http://localhost:8000/api/health. Image uses `uvicorn backend.main:app --port 8000`. For iterative dev you can mount code:
```bash
docker run -p 8000:8000 --env-file .env -v "$PWD/backend":/app/backend stash:local
```

## 7. Continuous Integration (CI)
Trigger: Pull Request or push to `main`.
Typical jobs:
| Job | Purpose |
|-----|---------|
| `setup-python` | Install Python & dependencies. |
| `lint` (optional) | Placeholder for style/type checks. |
| `test` | Run `pytest` + generate coverage. Fails if coverage < 70%. |
| `docker-build` | Build container image (no push on PR). |
Artifacts: coverage summary & HTML report (if uploaded). CI ensures code quality before merge.

## 8. Continuous Deployment (CD)
Trigger: Push to `main` after CI success.
Steps (conceptual workflow):
1. Authenticate to Azure (`azure/login` using federated credentials or stored secret).
2. `az acr login` (Azure Container Registry).
3. Build image: `docker build -t $ACR_LOGIN_SERVER/stash:${{ github.sha }} .`.
4. Push image: `docker push $ACR_LOGIN_SERVER/stash:${{ github.sha }}`.
5. Update Web App: `az webapp config container set ...` OR use `azure/webapps-deploy` action (runtime image reference from ACR).
Branch protection: Only `main` deploys; PRs run CI only. Rollback: redeploy prior image tag.

## 9. Environment Variables / Secrets
Application `.env` (runtime):
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Optional | Enables AI summarization (if absent, app still works). |
| `SECRET_KEY` | Recommended | JWT signing key (defaults to dev key if unset). |

GitHub Actions Secrets (example set):
| Secret | Purpose |
|--------|---------|
| `GROQ_API_KEY` | Inject for tests using summarizer (optional). |
| `SECRET_KEY` | Secure non-default JWT key in CI/CD. |
| `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` | Service principal for Azure login. |
| `AZURE_CLIENT_SECRET` | Credential for service principal (unless using OIDC). |
| `ACR_LOGIN_SERVER` | Registry hostname (e.g., `myregistry.azurecr.io`). |
| `AZURE_RESOURCE_GROUP` | Resource group for Web App + ACR. |
| `AZURE_WEBAPP_NAME` | Target Azure App Service name. |
| `SCRAPER_API_KEY` | Optional proxy API key (experimental transcript fetching). |

Sample `.env`:
```env
SECRET_KEY=change-me-in-production
GROQ_API_KEY=sk_groq_...
```

## 10. Monitoring Endpoints
| Endpoint | Purpose |
|----------|---------|
| `/api/health` | Lightweight status + whether summarizer initialized. |
| `/api/metrics` | Prometheus exposition format with counters/histograms. |

Prometheus Metrics Implemented:
- `http_requests_total{method,path,status_code}` – request volume.
- `http_request_duration_seconds{...}` – latency histogram buckets.
- `http_errors_total{...}` – 4xx/5xx counts.
These support alerting (error spike) & SLO evaluation (latency).

## 11. Deployed Application
Azure App Service (Container) URL (replace if changed):
```
https://<your-webapp-name>.azurewebsites.net
```
Health check in production: `https://<your-webapp-name>.azurewebsites.net/api/health`.
If using a custom domain, update DNS + add binding; steps unchanged.

## 12. Troubleshooting & Common Issues
| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on video endpoints | Missing/invalid JWT | Sign up/login first; pass `Authorization: Bearer <token>`. |
| "GROQ_API_KEY not found" | Key absent in environment | Add to `.env` or GitHub secret. |
| Empty summary field | Summarizer unavailable | Check health endpoint; ensure `GROQ_API_KEY` valid. |
| Transcript failures | Video lacks captions | Try a different video or language variant. |
| Coverage < 70% in CI | New code untested | Add tests; run `pytest --cov` locally. |
| Azure deploy fails on login | Wrong SP credentials | Re-create service principal / verify tenant & subscription IDs. |
| ACR push denied | Missing permission | Assign `AcrPush` role to service principal. |

General Debug Commands:
```bash
uvicorn backend.main:app --reload
curl localhost:8000/api/health
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/videos
```

## API Quick Reference
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/signup` | No | Register + return token |
| POST | `/api/auth/login` | No | Authenticate + return token |
| GET | `/api/auth/me` | Yes | Current user info |
| POST | `/api/videos` | Yes | Save video (transcript + summary) |
| GET | `/api/videos` | Yes | List user videos |
| GET | `/api/videos/{video_id}` | Yes | Single video |
| PUT | `/api/videos/{video_id}` | Yes | Update video title/summary |
| DELETE | `/api/videos/{video_id}` | Yes | Remove video |
| GET | `/api/health` | No | Service health |
| GET | `/api/metrics` | No | Prometheus metrics |

Example (save video):
```bash
TOKEN=<jwt>
curl -X POST http://localhost:8000/api/videos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## Code Quality Highlights
- SOLID: Controllers thin; services encapsulate logic; protocols enable inversion.
- Dependency Injection: `ServiceContainer` centralizes creation allowing graceful failure if optional summarizer absent.
- Reduced Coupling: Business logic isolated from HTTP specifics (testable in isolation).
- Error Handling Strategy: Service returns structured dicts → HTTP layer maps to status codes.

## Future Improvements
- Background task queue for longer summaries.
- Pagination & search APIs.
- Structured tagging & filtering.
- OpenTelemetry traces integrated with metrics.
- Multi-stage Docker build (wheels compile vs runtime) if build time grows.

## License / Academic Context
Produced for a university DevOps assignment (Assignment 2) – educational use only.

## Author
**Diana Cordovez** – Software Development & DevOps Course (2025)

## Acknowledgments
FastAPI, Groq, youtube-transcript-api, Prometheus client, Uvicorn.

---
This README emphasizes operational & DevOps aspects (CI/CD, monitoring, containerization) added to the original application.