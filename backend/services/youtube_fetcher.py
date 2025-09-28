# Used: https://pypi.org/project/youtube-transcript-api/
from youtube_transcript_api import YouTubeTranscriptApi

class YouTubeFetcher:
    """YouTube fetcher that correctly handles the FetchedTranscript data structure"""
    
    def __init__(self):
        self.api = YouTubeTranscriptApi()
    
    # Helper method to extract video ID from URL
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        url = url.strip()
        
        if 'v=' in url:
            return url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
        else:
            raise ValueError("Please use a standard YouTube URL")
    
    # Fetches transcript
    def get_transcript(self, url: str) -> dict:
        """
        Fetch transcript using the correct API and data access
        """
        try:
            video_id = self.extract_video_id(url)
            
            # Use the method: api.fetch(video_id)
            fetched_transcript = self.api.fetch(video_id)
            
            # Extract text from FetchedTranscriptSnippet objects
            # Use .text attribute that accesses the actual text from the transcript snippet
            full_text = ' '.join([snippet.text for snippet in fetched_transcript.snippets])
            
            return {
                'success': True,
                'method': 'api_fetch',
                'video_id': video_id,
                'transcript': full_text,
                'segments_count': len(fetched_transcript.snippets),
                'preview': full_text[:300] + '...' if len(full_text) > 300 else full_text,
                'language': fetched_transcript.language,
                'is_generated': fetched_transcript.is_generated
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'video_id': video_id if 'video_id' in locals() else None
            }
    
    def can_handle(self, url: str) -> bool:
        return 'youtube.com' in url.lower() or 'youtu.be' in url.lower()


# Test the fetcher
def test_fetcher():
    """Test the fetcher"""
    print("Testing YouTube fetcher...")
    
    fetcher = YouTubeFetcher()
    result = fetcher.get_transcript("https://www.youtube.com/watch?v=UyyjU8fzEYU")
    
    if result['success']:
        print(f" Success!")
        print(f" Segments: {result['segments_count']}")
        print(f"  Language: {result['language']}")
        print(f" Auto-generated: {result['is_generated']}")
        print(f" Preview: {result['preview'][:150]}...")
        return True
    else:
        print(f" FAILED: {result['error']}")
        return False


if __name__ == "__main__":
    test_fetcher()