# Create a test file: test_transcript.py
from youtube_transcript_api import YouTubeTranscriptApi

# Test with the TED talk ID directly
try:
    video_id = "ZQUxL4Jm1Lo"  # From the URL
    print(f"Testing video ID: {video_id}")
    
    # Try to get transcript
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    print(f"Success! Got {len(transcript)} transcript segments")
    print("First few segments:")
    for i, segment in enumerate(transcript[:3]):
        print(f"{i+1}: {segment}")
        
except Exception as e:
    print(f"Failed: {e}")
    print(f"Error type: {type(e)}")