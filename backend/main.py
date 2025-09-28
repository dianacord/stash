from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.services.youtube_fetcher import WorkingYouTubeFetcher

# Initialize FastAPI app
app = FastAPI(
    title="Stash API",
    description="Video Content Organizer",
    version="1.0.0"
)

# Initialize YouTube fetcher
youtube_fetcher = WorkingYouTubeFetcher()

# Pydantic models for request/response validation
class VideoRequest(BaseModel):
    url: str

class VideoResponse(BaseModel):
    success: bool
    video_id: str
    transcript: str
    segments_count: int
    preview: str

class ErrorResponse(BaseModel):
    success: bool
    error: str

# Routes
@app.get("/")
def root():
    """Root endpoint with basic info"""
    return {
        "message": "Stash API - Video Content Organizer",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health")
def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy", 
        "service": "stash-api",
        "version": "1.0.0"
    }

# In your backend/main.py, update the endpoint:
@app.post("/api/test-youtube")
def test_youtube_transcript(request: VideoRequest):
    # Temporarily hardcode the working video for testing
    test_url = "https://www.youtube.com/watch?v=UyyjU8fzEYU"  # This one worked in CLI!
    
    try:
        result = youtube_fetcher.get_transcript(test_url)
        return {"debug": "Using hardcoded working URL", "result": result}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}
        
# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)