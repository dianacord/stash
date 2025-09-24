from youtube_transcript_api import YoutubeTranscriptApi
from urllib.parse import urlparse, parese_qs
import re

class YouTubeFetcher:
    """Fetches transcripts from YouTube videos."""

    def __init__(self, default_language='en', enable_logging=True):
        self.default_language = default_language
        self.enable_logging = enable_logging
        
        self.supported_languages = ['en', 'es', 'fr']

        #Statistics tracking
        self.requests_made = 0
        self.successful_fetches = 0
        self.failed_fetches = 0

        #URL patterns for validation
        self.youtube_url_patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'  # Just the ID
        ]

    def log(self, message):
        """Logs a message if logging is enabled."""
        if self.enable_logging:
            print(f"[YouTubeFetcher] {message}")

    def extract_video_id(self, url):
        """Extracts video ID from YT url."""
        try:
            url = url.strip()

            #Try each url patterns
            for pattern in self.youtube_url_patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            self.log(f"Error extracting video ID from {url}: {e}")
            return None

    def get_video_title(self, video_id):
        """Get video title (placeholder, would use YouTube Data API during production)."""        
        return f"Youtube Video {video_id[:8]}"
    
    def fetch_transcript(self, url, language=None):
        """Fetches transcript for a given YouTube URL."""
        self.requests_made += 1 # Updates stats
        target_language = language or self.default_language # Use provided or default language
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                self.failed_fetches += 1
                return{
                    'success': False,
                    'error': 'Could not extract video ID from URL'
                }
            self.log(f"Fetching transcript for video ID: {video_id} in language: {target_language}")
        
            # Try getting transcript in requested language
            try:
                transcript_list = YoutubeTranscriptApi.get_transcript(
                    video_id,
                    languages=[target_language]
                )
                used_language = target_language
            except:
                # Fallback to the language available
                self.log(f"Language {target_language} not available, trying any language...")
                transcript_list = YoutubeTranscriptApi.get_transcript(video_id)
                used_language = 'auto'

            # Combine transcript segments
            full_transcript = " ".join([seg['text'] for seg in transcript_list])

            # Get video info
            title = self.get_video_title(video_id)

            # Update stats
            self.successful_fetches += 1
            self.log(f"Successfully fetched transcript ({len(full_transcript)} characters)")    
            return {
                'success': True,
                'video_id': video_id,
                'title': title,
                'transcript': full_transcript,
                'platform': 'YouTube',
                'language': used_language,
                'url': url,
                'fetcher_stats': self.get_stats()
            }
        except Exception as e:
            self.failed_fetches += 1
            self.log(f"Failed to fetch transcript for {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'video_id': self.extract_video_id(url) if url else None,
                'fetcher_stats': self.get_stats()
            }
    
    def validate_url(self, url):
        """Checks if url is valid YT url."""    
        if not url:
            return False
        return self.extract_video_id(url) is not None
    
    def get_stats(self):
        """Fetcher statistics."""
        success_rate = (self.successful_fetches/ max(self.requests_made, 1)) * 100
        return{
            'total_requests': self.requests_made,
            'successful_fetches': self.successful_fetches,
            'failed_fetches': self.failed_fetches,
            'success_rate': f"{success_rate:.f}%"
        }
    
    def reset_stats(self):
        """Resets stats."""
        self.requests_made = 0
        self.successful_fetches = 0
        self.failed_fetches = 0
        self.log("Statistics counters reset.")

    def set_language(self, language):
        """Changes default language"""
        old_language = self.default_language
        self.default_language = language
        if language not in self.supported_languages:
            self.log(f"Warning: {language} not supported. Supported: {self.supported_languages}")