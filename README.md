<div align="center">

# Stash

Organize saved YouTube videos with transcript extraction, AI summarization, authentication, metrics, and Postgres, and DevOps tooling (CI, Docker, Kubernetes).

</div>

## 1. Overview
Stash tackles the “save for later but never revisit” problem. Users save a YouTube URL; the backend extracts the transcript, optionally summarizes it via Groq (`openai/gpt-oss-120b`), and persists structured information. This assignment extends the original app by adding: automated testing & coverage gates, Docker image builds, GitHub Actions CI/CD, secret management, health/metrics endpoints, and improved code quality (SOLID + dependency injection).

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
│       ├── database.py         # Postgres persistence (users + saved_videos)
│       ├── youtube_fetcher.py  # Transcript retrieval & normalization
│       └── groq_summarizer.py  # AI summarization (optional if key present)
├── frontend/               # Thin static UI served separately (index.html)
├── tests/                  # Unit + integration tests (services + API)
├── k8s/                    # Kubernetes manifests (Kustomize) + kind cluster config
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
Stash needs Postgres. Start one locally with Docker, then set `DATABASE_URL` in `.env` (see `.env.example`):
```bash
docker run -d --name stash-db -e POSTGRES_USER=stash -e POSTGRES_PASSWORD=stash \
  -e POSTGRES_DB=stash -p 5432:5432 pgvector/pgvector:0.8.0-pg17
```
Tables are created on first use.

## 4. Run Locally
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Access:
- API Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/api/health
- Liveness / readiness: http://localhost:8000/healthz, http://localhost:8000/readyz
- Metrics: http://localhost:8000/api/metrics
Frontend: open `frontend/index.html` directly or serve via a simple static server (the root `/` returns the file through FastAPI).

## 5. Tests & Coverage
Tests run against a real Postgres (CI starts one as a service container). Locally, start a test database on port 5433 first:
```bash
docker run -d --name stash-test-db -e POSTGRES_USER=stash -e POSTGRES_PASSWORD=stash \
  -e POSTGRES_DB=stash_test -p 5433:5432 pgvector/pgvector:0.8.0-pg17
```
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

## 8. Kubernetes (local kind cluster)
Stash runs on a 3-node [kind](https://kind.sigs.k8s.io/) cluster (1 control plane, 2 workers), deployed with Kustomize from `k8s/`.

| Object | What it does |
|--------|--------------|
| `Deployment/stash` | 2 replicas of the API, spread across the workers. |
| `Service/stash` (NodePort 30080) | Stable address in front of the pods; kind maps it to `localhost:8081`. |
| `StatefulSet/postgres` + PVC | Postgres 17 + pgvector with a 1Gi persistent volume, so data survives pod restarts. |
| `Service/postgres` (ClusterIP) | Stash reaches the database at `postgres:5432` via cluster DNS. |
| `Secret/stash-secrets-<hash>` | Generated by Kustomize from the gitignored `k8s/secrets.env`; a changed secret gets a new name and rolls the pods. |

Probes are split on purpose:
- **Liveness** `/healthz` checks only that the process answers. A database or Groq outage must not make Kubernetes restart pods, since a restart can't fix either.
- **Readiness** `/readyz` checks the database and returns 503 when it is unreachable, so the pod leaves the load balancer until Postgres is back. Groq is not checked: the app works without summaries.

Run it:
```bash
kind create cluster --config k8s/kind-config.yaml
cp k8s/secrets.env.example k8s/secrets.env   # then fill in
docker build -t stash:pg .
kind load docker-image stash:pg --name stash
kubectl apply -k k8s/
kubectl get pods -w                          # wait for 1/1
curl localhost:8081/api/health
```

Verified on the cluster:
- Deleting `postgres-0` brings it back on the same volume in about 2 seconds, and a user created before the restart can still log in.
- With Postgres scaled to 0, the Stash pods drop to `0/1` (not ready) with 0 restarts, then return to `1/1` by themselves when Postgres is back.
- CI (`k8s-e2e` job) runs the same deploy on a fresh kind cluster for every pull request and push to `main`, then repeats the persistence check.

## 9. Environment Variables / Secrets
Application `.env` (runtime):
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Optional | Enables AI summarization (if absent, app still works). |
| `SECRET_KEY` | Required | JWT signing key. The app refuses to start without it. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `DATABASE_URL` | Required | Postgres connection string, e.g. `postgresql://stash:stash@localhost:5432/stash`. |

Sample `.env`:
```env
SECRET_KEY=replace_with_a_long_random_string
GROQ_API_KEY=sk_groq_...
DATABASE_URL=postgresql://stash:stash@localhost:5432/stash
```

## 10. Monitoring Endpoints
| Endpoint | Purpose |
|----------|---------|
| `/api/health` | Lightweight status + whether summarizer initialized. |
| `/healthz` | Liveness probe: process is up (no dependency checks). |
| `/readyz` | Readiness probe: 200 if the database answers, else 503. |
| `/api/metrics` | Prometheus exposition format with counters/histograms. |

Prometheus Metrics Implemented:
- `http_requests_total{method,path,status_code}` – request volume.
- `http_request_duration_seconds{...}` – latency histogram buckets.
- `http_errors_total{...}` – 4xx/5xx counts.
These support alerting (error spike) & SLO evaluation (latency).

## 11. Deployed Application
Stash was previously deployed to Azure App Service through Azure Container Registry. That ran on a university subscription that has since ended, so the deploy workflow was removed; the Kubernetes setup in section 8 is the current way to run it.

## 12. Troubleshooting & Common Issues
| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on video endpoints | Missing/invalid JWT | Sign up/login first; pass `Authorization: Bearer <token>`. |
| "SECRET_KEY is not set" | JWT signing key missing | Add `SECRET_KEY` to `.env` (or the deployment's secrets). |
| "GROQ_API_KEY not found" | Key absent in environment | Add to `.env` or GitHub secret. |
| Empty summary field | Summarizer unavailable | Check health endpoint; ensure `GROQ_API_KEY` valid. |
| Transcript failures | Video lacks captions | Try a different video or language variant. |
| Coverage < 70% in CI | New code untested | Add tests; run `pytest --cov` locally. |

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