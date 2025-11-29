"""Main FastAPI application - Thin controllers only.

Routes delegate to service layer for business logic.
Follows Single Responsibility and Dependency Inversion principles.
"""

import time

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from backend.dependencies import (
    get_auth_service,
    get_container,
    get_metrics_service,
    get_video_service,
)
from backend.metrics import METRICS_PATH, MetricsService
from backend.services.auth_service import verify_token
from backend.services.user_service import AuthService
from backend.services.video_service import VideoService

load_dotenv()

app = FastAPI(title="Stash API", description="Video Content Organizer")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to record Prometheus metrics for every request."""

    async def dispatch(self, request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)

        # Prefer route path pattern to reduce label cardinality (e.g. /api/videos/{video_id})
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)

        # Record metrics (service handles exclusion of metrics endpoint)
        metrics_service = get_metrics_service()
        metrics_service.record_request(
            request.method, path, response.status_code, start, exclude_path=METRICS_PATH
        )

        return response


app.add_middleware(PrometheusMiddleware)


@app.get("/")
async def read_root():
    """Serve the main frontend page"""
    return FileResponse("frontend/index.html")


# Pydantic Models
class SignupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str


class VideoRequest(BaseModel):
    url: str


# Authentication Dependency
def get_current_user(authorization: str | None = Header(None)):
    """
    Dependency that extracts and validates JWT token from request headers.
    Returns user info if token is valid, raises 401 error if not.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Extract token from "Bearer <token>" format
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        # Verify token and get user info
        payload = verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return payload  # Returns {"username": "...", "user_id": ...}

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


# ============================================================================
# Authentication Endpoints
# ============================================================================


@app.post("/api/auth/signup", response_model=TokenResponse)
def signup(request: SignupRequest, auth_service: AuthService = Depends(get_auth_service)):
    """
    Register a new user with username and password.
    Returns JWT token for immediate login.
    """
    result = auth_service.signup(request.username, request.password)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "username": result["username"],
    }


@app.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    """
    Login with username and password.
    Returns JWT token for authenticated requests.
    """
    result = auth_service.login(request.username, request.password)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "username": result["username"],
    }


@app.get("/api/auth/me")
def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get information about the currently logged-in user.
    Requires valid JWT token in Authorization header.
    """
    user = auth_service.get_user_info(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": user}


# ============================================================================
# Video Endpoints
# ============================================================================


@app.post("/api/videos")
def save_video_transcript(
    request: VideoRequest,
    current_user: dict = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
):
    """
    Save a video transcript to database.
    Only accessible with valid JWT token.
    Videos are associated with the logged-in user.
    """
    try:
        result = video_service.save_video(request.url, current_user["user_id"])

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to save video"))

        # Handle "already exists" case
        if "message" in result:
            return {"message": result["message"], "data": result["data"]}

        return {"success": True, "message": "Video saved", "data": result["data"]}

    except HTTPException:
        # Re-raise HTTPException from services (for testing and service layer errors)
        raise
    except ValueError as e:
        # Invalid URL format
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__} occurred"
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/videos")
def get_all_videos(
    current_user: dict = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
):
    """
    Get all saved videos for the currently logged-in user.
    Only returns videos belonging to this user.
    """
    try:
        videos = video_service.get_user_videos(current_user["user_id"])
        return {"success": True, "data": videos}
    except HTTPException:
        # Re-raise HTTPException from services
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__} occurred"
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/videos/{video_id}")
def get_video(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
):
    """
    Get specific video by ID.
    Only accessible if video belongs to the logged-in user.
    """
    video = video_service.get_video(video_id, current_user["user_id"])
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {"success": True, "data": video}


@app.delete("/api/videos/{video_id}")
def delete_video(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
):
    """Delete a video (only if it belongs to current user)"""
    result = video_service.delete_video(video_id, current_user["user_id"])

    if not result["success"]:
        error = result["error"]
        if error == "Video not found":
            raise HTTPException(status_code=404, detail=error)
        elif error == "Access denied":
            raise HTTPException(status_code=403, detail=error)
        else:
            raise HTTPException(status_code=500, detail=error)

    return {"success": True, "message": "Video deleted"}


@app.put("/api/videos/{video_id}")
def update_video(
    video_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
):
    """Update video summary/notes (only if it belongs to current user)"""
    result = video_service.update_video(video_id, current_user["user_id"], request)

    if not result["success"]:
        error = result["error"]
        if error == "Video not found":
            raise HTTPException(status_code=404, detail=error)
        elif error == "Access denied":
            raise HTTPException(status_code=403, detail=error)
        else:
            raise HTTPException(status_code=500, detail=error)

    return {"success": True, "message": "Video updated", "data": result["data"]}


# ============================================================================
# Health Check
# ============================================================================


@app.get("/api/health")
def health_check():
    """
    Check if the API is running and which services are available.
    Public endpoint - no authentication required.
    """
    container = get_container()
    return {
        "status": "healthy",
        "service": "stash-api",
        "groq_summarizer": container.summarizer_available,
    }


# ============================================================================
# Metrics Endpoint (Unauthenticated)
# ============================================================================


@app.get(METRICS_PATH)
def get_metrics(metrics_service: MetricsService = Depends(get_metrics_service)):
    """
    Expose Prometheus metrics in text format.
    Public endpoint - no authentication required.
    """
    return metrics_service.get_metrics_response()
