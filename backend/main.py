from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.services.youtube_fetcher import YouTubeFetcher
from backend.services.database import DatabaseService
import traceback

app = FastAPI(title="Stash API", description="Video Content Organizer")

# Initialize services
youtube_fetcher = YouTubeFetcher()
db_service = DatabaseService()

class VideoRequest(BaseModel):
    url: str

@app.post("/api/videos")
def save_video_transcript(request: VideoRequest):
    """Save a video transcript to database"""
    try:
        print(f"DEBUG - Received URL: {request.url}")
        
        # Check if already exists
        video_id = youtube_fetcher.extract_video_id(request.url)
        print(f"DEBUG - Extracted video_id: {video_id}")
        
        existing = db_service.get_video_by_id(video_id)
        print(f"DEBUG - Existing video: {existing}")
        
        if existing:
            return {"message": "Video already exists", "data": existing}
        
        # Fetch transcript
        print("DEBUG - Fetching transcript...")
        transcript_result = youtube_fetcher.get_transcript(request.url)
        print(f"DEBUG - Transcript result success: {transcript_result.get('success')}")
        
        if not transcript_result['success']:
            raise HTTPException(status_code=400, detail=transcript_result['error'])
        
        # Prepare data for database
        video_data = {
            'url': request.url,
            'video_id': transcript_result['video_id'],
            'raw_transcript': transcript_result['transcript'],
            'language': transcript_result.get('language'),
            'is_generated': transcript_result.get('is_generated'),
            'segments_count': transcript_result['segments_count'],
            'platform': 'youtube'
        }
        print(f"DEBUG - Prepared video_data with {len(video_data['raw_transcript'])} chars of transcript")

        # Save to database
        print("DEBUG - Saving to database...")
        save_result = db_service.save_video(video_data)
        print(f"DEBUG - Save result: {save_result.get('success')}")
        
        if save_result['success']:
            return {"success": True, "message": "Video saved", "data": save_result['data']}
        else:
            raise HTTPException(status_code=500, detail=save_result['error'])
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the full traceback for debugging
        print(f"ERROR - Exception type: {type(e).__name__}")
        print(f"ERROR - Exception message: {str(e)}")
        print(f"ERROR - Full traceback:")
        traceback.print_exc()
        
        # Raise with detailed error message
        error_msg = str(e) if str(e) else f"{type(e).__name__} occurred with no message"
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/videos")
def get_all_videos():
    """Get all saved videos"""
    try:
        videos = db_service.get_all_videos()
        return {"success": True, "data": videos}
    except Exception as e:
        print(f"ERROR getting videos: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{video_id}")
def get_video(video_id: str):
    """Get specific video by ID"""
    try:
        video = db_service.get_video_by_id(video_id)
        if video:
            return {"success": True, "data": video}
        else:
            raise HTTPException(status_code=404, detail="Video not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR getting video: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "stash-api"}