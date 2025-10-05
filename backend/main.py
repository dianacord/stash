from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
from datetime import timedelta
from pydantic import BaseModel
from backend.services.youtube_fetcher import YouTubeFetcher
from backend.services.database import DatabaseService
from backend.services.groq_summarizer import GroqSummarizer
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from backend.services.auth_service import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

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

@app.get("/")
async def read_root():
    """Serve the main frontend page"""
    return FileResponse("frontend/index.html")

# Initialize services
youtube_fetcher = YouTubeFetcher()
db_service = DatabaseService()

try:
    groq_summarizer = GroqSummarizer()
    summarizer_available = True
except Exception as e:
    print(f"Warning: GroqSummarizer not available: {e}")
    groq_summarizer = None
    summarizer_available = False

# Pydantic Auth models
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

# Video Models
class VideoRequest(BaseModel):
    url: str

def get_current_user(authorization: Optional[str] = Header(None)):
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

# Authentication Endpoints
@app.post("/api/auth/signup", response_model=TokenResponse)
def signup(request: SignupRequest):
    """
    Register a new user with username and password.
    Returns JWT token for immediate login.
    """
    try:
        # Check if username already taken
        existing_user = db_service.get_user_by_username(request.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Hash password for secure storage
        hashed_password = get_password_hash(request.password)
        
        # Create user in database
        result = db_service.create_user(request.username, hashed_password)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        user = result['data']
        
        # Generate JWT token
        access_token = create_access_token(
            data={"sub": user['username'], "user_id": user['id']},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user['username']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """
    Login with username and password.
    Returns JWT token for authenticated requests.
    """
    try:
        # Get user from database
        user = db_service.get_user_by_username(request.username)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Verify password matches stored hash
        if not verify_password(request.password, user['hashed_password']):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Generate JWT token
        access_token = create_access_token(
            data={"sub": user['username'], "user_id": user['id']},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user['username']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get information about the currently logged-in user.
    Requires valid JWT token in Authorization header.
    """
    user = db_service.get_user_by_id(current_user['user_id'])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": user}


# Video endpoints
@app.post("/api/videos")
def save_video_transcript(
    request: VideoRequest,
    current_user: dict = Depends(get_current_user)  # Requires authentication
):
    """
    Save a video transcript to database.
    Only accessible with valid JWT token.
    Videos are associated with the logged-in user.
    """
    try:
        # Extract video ID and check if already exists
        video_id = youtube_fetcher.extract_video_id(request.url)
        existing = db_service.get_video_by_id(video_id)
        
        if existing:
            return {"message": "Video already exists", "data": existing}
        
        # Fetch transcript from YouTube
        transcript_result = youtube_fetcher.get_transcript(request.url)
        
        if not transcript_result['success']:
            raise HTTPException(status_code=400, detail=transcript_result['error'])

        # Generate AI summary if available
        ai_summary = None
        if summarizer_available and groq_summarizer:
            summary_result = groq_summarizer.summarize(transcript_result['transcript'])
            if summary_result['success']:
                ai_summary = summary_result['summary']
            else:
                print(f"Warning: Failed to generate summary - {summary_result.get('error')}")
        
        # Prepare data for database
        video_data = {
            'url': request.url,
            'video_id': transcript_result['video_id'],
            'raw_transcript': transcript_result['transcript'],
            'ai_summary': ai_summary,
            'language': transcript_result.get('language'),
            'is_generated': transcript_result.get('is_generated'),
            'segments_count': transcript_result['segments_count'],
            'platform': 'youtube'
        }

        # Save to database with user_id
        save_result = db_service.save_video(video_data, current_user['user_id'])
        
        if save_result['success']:
            return {"success": True, "message": "Video saved", "data": save_result['data']}
        else:
            raise HTTPException(status_code=500, detail=save_result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__} occurred"
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/videos")
def get_all_videos(current_user: dict = Depends(get_current_user)):
    """
    Get all saved videos for the currently logged-in user.
    Only returns videos belonging to this user.
    """
    try:
        videos = db_service.get_user_videos(current_user['user_id'])
        return {"success": True, "data": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/{video_id}")
def get_video(video_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get specific video by ID.
    Only accessible if video belongs to the logged-in user.
    """
    try:
        video = db_service.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if video belongs to current user
        if video.get('user_id') != current_user['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {"success": True, "data": video}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    """
    Check if the API is running and which services are available.
    Public endpoint - no authentication required.
    """
    return {
        "status": "healthy", 
        "service": "stash-api", 
        "groq_summarizer": summarizer_available
    }

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a video (only if it belongs to current user)"""
    try:
        video = db_service.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check ownership
        if video.get('user_id') != current_user['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete from database
        result = db_service.delete_video(video_id)
        
        if result['success']:
            return {"success": True, "message": "Video deleted"}
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/videos/{video_id}")
def update_video(
    video_id: str, 
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update video summary/notes (only if it belongs to current user)"""
    try:
        video = db_service.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check ownership
        if video.get('user_id') != current_user['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update in database
        result = db_service.update_video(video_id, request)
        
        if result['success']:
            return {"success": True, "message": "Video updated", "data": result['data']}
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))