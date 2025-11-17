# Used: https://pypi.org/project/youtube-transcript-api/
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi

class YouTubeFetcher:
    """Service for extracting YouTube video IDs and transcripts.

    Notes
    -----
    - Keeps public return shape stable for existing tests and API consumers.
    - Can handle both the library's FetchedTranscript object (with `.snippets`)
      and the classic list-of-dicts format returned by `get_transcript`.
    """

    def __init__(self) -> None:
        # While the library often exposes static methods, we keep an instance for flexibility
        self.api = YouTubeTranscriptApi()

    def extract_video_id(self, url: str) -> str:
        """Extract the YouTube video ID from a URL.

        Supports standard watch URLs and youtu.be short links. Keeps behavior
        consistent with tests, but uses urllib for slightly safer parsing.
        """
        raw = url.strip()

        # Try short form first: https://youtu.be/<id>?...
        if 'youtu.be/' in raw:
            try:
                path_id = urlparse(raw).path.lstrip('/')
                if path_id:
                    return path_id.split('/')[0]
            except Exception:
                pass

            # Fallback string split (back-compatible with prior logic)
            return raw.split('youtu.be/')[1].split('?')[0]

        # Standard form: https://www.youtube.com/watch?v=<id>&...
        if 'v=' in raw:
            try:
                parsed = urlparse(raw)
                qs = parse_qs(parsed.query)
                v = qs.get('v', [None])[0]
                if v:
                    return v
            except Exception:
                pass

            # Fallback string split (back-compatible with prior logic)
            return raw.split('v=')[1].split('&')[0]

        raise ValueError("Please use a standard YouTube URL")

    def _join_text_from_payload(self, payload: Any) -> Dict[str, Any]:
        """Normalize various transcript payload shapes into a common dict.

        Handles:
        - FetchedTranscript: has `.snippets` (each with `.text`)
        - list[dict]: each element with a 'text' key (classic API)
        - list[str]: rare/defensive case; join directly
        Returns a mapping with: transcript, segments_count, language, is_generated
        Missing fields default to None.
        """
        language = getattr(payload, 'language', None)
        is_generated = getattr(payload, 'is_generated', None)

        # FetchedTranscript object with `.snippets`
        snippets = getattr(payload, 'snippets', None)
        if isinstance(snippets, list):
            texts = [getattr(s, 'text', '') for s in snippets]
            return {
                'transcript': ' '.join(t for t in texts if t),
                'segments_count': len(snippets),
                'language': language,
                'is_generated': is_generated,
            }

        # List of dicts (classic youtube-transcript-api)
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            texts = [str(item.get('text', '')) for item in payload]
            return {
                'transcript': ' '.join(t for t in texts if t),
                'segments_count': len(payload),
                'language': language,
                'is_generated': is_generated,
            }

        # List of strings (defensive fallback)
        if isinstance(payload, list) and payload and isinstance(payload[0], str):
            return {
                'transcript': ' '.join(payload),
                'segments_count': len(payload),
                'language': language,
                'is_generated': is_generated,
            }

        # Unknown shape
        return {
            'transcript': '',
            'segments_count': 0,
            'language': language,
            'is_generated': is_generated,
        }

    def get_transcript(self, url: str) -> dict:
        """Fetch transcript for the given URL, preferring English variants.

        Returns a dict:
        - success: bool
        - video_id: str | None
        - transcript: str (on success)
        - segments_count: int (on success)
        - language: Optional[str]
        - is_generated: Optional[bool]
        - error, error_type (on failure)
        """
        video_id: str | None = None
        try:
            video_id = self.extract_video_id(url)

            # Prefer English. Keep using instance API for back-compat; some versions
            # expose a richer FetchedTranscript via `fetch`, others return list via `get_transcript`.
            try:
                payload = self.api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])  # type: ignore[attr-defined]
            except AttributeError:
                # Fallback to classic static method if `.fetch` isn't available
                payload = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])

            normalized = self._join_text_from_payload(payload)

            return {
                'success': True,
                'video_id': video_id,
                'transcript': normalized['transcript'],
                'segments_count': normalized['segments_count'],
                'language': normalized.get('language'),
                'is_generated': normalized.get('is_generated'),
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e) if str(e) else type(e).__name__,
                'error_type': type(e).__name__,
                'video_id': video_id,
            }

    def can_handle(self, url: str) -> bool:
        return 'youtube.com' in url.lower() or 'youtu.be' in url.lower()