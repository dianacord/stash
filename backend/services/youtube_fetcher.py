# Used: https://pypi.org/project/youtube-transcript-api/
from youtube_transcript_api import YouTubeTranscriptApi

class YouTubeFetcher:
    """YouTube fetcher that handles the FetchedTranscript data structure"""
    
    def __init__(self):
        self.api = YouTubeTranscriptApi()
        print(f"DEBUG: Available methods: {[m for m in dir(self.api) if not m.startswith('_')]}")
    
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        url = url.strip()
        
        if 'v=' in url:
            return url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
        else:
            raise ValueError("Please use a standard YouTube URL")
    
    def get_transcript(self, url: str) -> dict:
        """Fetch transcript, preferring English"""
        try:
            video_id = self.extract_video_id(url)
            
            # Use fetch with English language preference
            fetched_transcript = self.api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
            
            # Extract text from FetchedTranscriptSnippet objects
            full_text = ' '.join([snippet.text for snippet in fetched_transcript.snippets])
            
            return {
                'success': True,
                'video_id': video_id,
                'transcript': full_text,
                'segments_count': len(fetched_transcript.snippets),
                'language': fetched_transcript.language,
                'is_generated': fetched_transcript.is_generated
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e) if str(e) else type(e).__name__,
                'error_type': type(e).__name__,
                'video_id': video_id if 'video_id' in locals() else None
            }
    
    def can_handle(self, url: str) -> bool:
        return 'youtube.com' in url.lower() or 'youtu.be' in url.lower()