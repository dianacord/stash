# Used: https://pypi.org/project/youtube-transcript-api/
from youtube_transcript_api import YouTubeTranscriptApi
import time

class YouTubeFetcher:
    """YouTube fetcher using youtube-transcript-api"""
    
    def __init__(self):
        self.api = YouTubeTranscriptApi()
    
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
        """
        Fetch transcript for given Yt URL
        """
        video_id = None
        
        try:
            video_id = self.extract_video_id(url)
            print(f"DEBUG - Fetching transcript for video_id: {video_id}")
            
            transcript_list = self.api.list(video_id)
            print(f"DEBUG - Got transcript list")
            
            # Tries to find English transcript first, then fall back to any available
            transcript = None
            preferred_languages = ['en', 'en-US', 'en-GB']
            
            for t in transcript_list:
                if hasattr(t, 'language_code') and t.language_code.lower() in [lang.lower() for lang in preferred_languages]:
                    transcript = t
                    print(f"DEBUG - Found English transcript: {t.language}")
                    break
            
            # If no English, take the first available
            if not transcript:
                for t in transcript_list:
                    try:
                        transcript = t
                        print(f"DEBUG - No English found, using transcript in language: {t.language}")
                        break
                    except:
                        continue
            
            if not transcript:
                return {
                    'success': False,
                    'error': 'No transcripts available for this video',
                    'error_type': 'NoTranscriptFound',
                    'video_id': video_id
                }
            
            # Fetch the actual transcript data
            print(f"DEBUG - Fetching transcript data...")
            fetched_data = transcript.fetch()
            print(f"DEBUG - Retrieved transcript data")
            
            # Extract text from the fetched data (there are other atrributes, but we just want .text)
            if hasattr(fetched_data, '__iter__'):
                # It's a list of FetchedTranscriptSnippet objects
                full_text = ' '.join([snippet.text for snippet in fetched_data])
                segments_count = len(fetched_data)
            else:
                # Fallback
                full_text = str(fetched_data)
                segments_count = 1
            
            # Get metadata
            language = getattr(transcript, 'language', None)
            is_generated = getattr(transcript, 'is_generated', None)
            
            return {
                'success': True,
                'method': 'api_fetch',
                'video_id': video_id,
                'transcript': full_text,
                'segments_count': segments_count,
                'preview': full_text[:300] + '...' if len(full_text) > 300 else full_text,
                'language': language,
                'is_generated': is_generated
            }

        # Error handling   
        except AttributeError as e:
            return {
                'success': False,
                'error': f'API method not found: {str(e)}',
                'error_type': 'AttributeError',
                'video_id': video_id
            }
            
        except Exception as e:
            error_str = str(e)
            print(f"ERROR - Exception: {error_str}")
            
            # Detect common errors
            if 'disabled' in error_str.lower():
                return {
                    'success': False,
                    'error': 'Transcripts are disabled for this video',
                    'error_type': 'TranscriptsDisabled',
                    'video_id': video_id
                }
            
            if 'not found' in error_str.lower():
                return {
                    'success': False,
                    'error': 'No transcript found for this video',
                    'error_type': 'NoTranscriptFound',
                    'video_id': video_id
                }
            
            if 'no element found' in error_str.lower() or 'xml' in error_str.lower():
                return {
                    'success': False,
                    'error': 'Unable to retrieve transcript - YouTube may be blocking requests. Try again later.',
                    'error_type': 'XMLParseError',
                    'video_id': video_id
                }
            
            return {
                'success': False,
                'error': error_str if error_str else f'{type(e).__name__} occurred',
                'error_type': type(e).__name__,
                'video_id': video_id
            }
    
    def can_handle(self, url: str) -> bool:
        """Check if this fetcher can handle the given URL"""
        return 'youtube.com' in url.lower() or 'youtu.be' in url.lower()


# Test the fetcher
def test_fetcher():
    """Test the fetcher"""
    print("Testing YouTube fetcher...\n")
    
    test_videos = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=UyyjU8fzEYU",
    ]
    
    fetcher = YouTubeFetcher()
    
    for video_url in test_videos:
        print(f"\nTesting: {video_url}")
        print("-" * 50)
        result = fetcher.get_transcript(video_url)
        
        if result['success']:
            print(f"✓ Success!")
            print(f"  Method: {result.get('method')}")
            print(f"  Segments: {result['segments_count']}")
            print(f"  Language: {result.get('language', 'Unknown')}")
            print(f"  Auto-generated: {result.get('is_generated', 'Unknown')}")
            print(f"  Preview: {result['preview'][:100]}...")
        else:
            print(f"✗ FAILED: {result['error']}")
            print(f"  Error type: {result['error_type']}")


if __name__ == "__main__":
    test_fetcher()