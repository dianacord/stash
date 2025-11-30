# Used: https://pypi.org/project/youtube-transcript-api/
import html
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import requests
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def fetch_with_scraperapi(url: str) -> str:
    """Fetch URL content using ScraperAPI proxy.

    Args:
        url: The URL to fetch

    Returns:
        Raw response body as string

    Raises:
        ValueError: If SCRAPER_API_KEY is not set
        requests.HTTPError: If the request fails
    """
    api_key = os.getenv("SCRAPER_API_KEY")
    if not api_key:
        raise ValueError("SCRAPER_API_KEY not found in environment variables")

    # Use render=false and keep_headers=true for raw API responses (not browser rendering)
    scraper_url = (
        f"http://api.scraperapi.com/?api_key={api_key}&url={quote(url)}"
        f"&country_code=us&render=false&keep_headers=true&device_type=desktop"
    )
    response = requests.get(scraper_url, timeout=30)
    response.raise_for_status()
    return response.text


class YouTubeFetcher:
    """Service for extracting YouTube video IDs and transcripts.

    Notes
    -----
    - Keeps public return shape stable for existing tests and API consumers.
    - Can handle both the library's FetchedTranscript object (with `.snippets`)
      and the classic list-of-dicts format returned by `get_transcript`.
    - Supports ScraperAPI proxy for bypassing IP blocks when SCRAPER_API_KEY is set.
    """

    def __init__(self) -> None:
        # While the library often exposes static methods, we keep an instance for flexibility
        self.api = YouTubeTranscriptApi()
        self.use_scraper = os.getenv("SCRAPER_API_KEY") is not None

    def _fetch_transcript_via_scraperapi(self, video_id: str) -> list[dict] | None:
        """
        Fetch transcript by scraping the YouTube video page HTML via ScraperAPI,
        extracting ytInitialPlayerResponse JSON, and downloading transcript from captionTracks.
        Returns list of dicts with 'text' keys, or None on failure so caller falls back.
        """
        if not self.use_scraper:
            return None

        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"[ScraperAPI] Fetching video page HTML for {video_id} via {video_url}")
            html_text = fetch_with_scraperapi(video_url)
            if not html_text or not html_text.strip():
                logger.warning("[ScraperAPI] Empty response for video page HTML")
                return None
            # Find ytInitialPlayerResponse JSON
            import json
            import re

            match = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;", html_text, re.DOTALL)
            if not match:
                logger.warning("[ScraperAPI] ytInitialPlayerResponse JSON not found in HTML")
                # Optionally log a snippet of HTML for debugging
                logger.debug(f"[ScraperAPI] HTML snippet: {html_text[:500]}")
                return None
            try:
                player_json = json.loads(match.group(1))
                logger.info("[ScraperAPI] ytInitialPlayerResponse JSON parsed successfully")
            except Exception as e:
                logger.warning(f"[ScraperAPI] Failed to parse ytInitialPlayerResponse JSON: {e}")
                logger.debug(f"[ScraperAPI] JSON snippet: {match.group(1)[:500]}")
                return None
            # Extract captionTracks
            tracks = (
                player_json.get("captions", {})
                .get("playerCaptionsTracklistRenderer", {})
                .get("captionTracks", [])
            )
            logger.info(f"[ScraperAPI] Found {len(tracks)} captionTracks")
            if not tracks:
                logger.warning("[ScraperAPI] No captionTracks found in ytInitialPlayerResponse")
                logger.debug(
                    f"[ScraperAPI] ytInitialPlayerResponse keys: {list(player_json.keys())}"
                )
                return None

            # Prioritize English tracks
            def priority(track):
                lang = track.get("languageCode", "")
                kind = track.get("kind", "")
                if lang.startswith("en") and kind != "asr":
                    return (0, lang)
                if lang.startswith("en") and kind == "asr":
                    return (1, lang)
                if kind != "asr":
                    return (2, lang)
                return (3, lang)

            chosen = sorted(tracks, key=priority)[0]
            logger.info(
                f"[ScraperAPI] Chosen captionTrack: lang={chosen.get('languageCode')}, kind={chosen.get('kind')}, name={chosen.get('name')}"
            )
            transcript_url = chosen.get("baseUrl")
            if not transcript_url:
                logger.warning("[ScraperAPI] No baseUrl found for chosen captionTrack")
                logger.debug(f"[ScraperAPI] Chosen track: {chosen}")
                return None
            logger.info(f"[ScraperAPI] Fetching transcript from baseUrl: {transcript_url}")
            transcript_text = fetch_with_scraperapi(transcript_url)
            if not transcript_text or not transcript_text.strip():
                logger.warning("[ScraperAPI] Empty response for transcript baseUrl")
                return None
            # Parse XML transcript
            try:
                transcript_root = ET.fromstring(transcript_text)
                segments: list[dict] = []
                for node in transcript_root.findall("text"):
                    raw = node.text or ""
                    cleaned = html.unescape(raw).replace("\n", " ").strip()
                    if cleaned:
                        segments.append({"text": cleaned})
                logger.info(f"[ScraperAPI] Transcript XML parsed, {len(segments)} segments found")
                if segments:
                    logger.info(
                        f"Transcript for {video_id} fetched via ScraperAPI HTML/ytInitialPlayerResponse lang={chosen.get('languageCode')}"
                    )
                    return segments
                logger.warning("[ScraperAPI] Transcript XML returned no segments")
            except Exception as e:
                logger.warning(f"[ScraperAPI] Transcript XML parse failed: {e}")
                logger.debug(f"[ScraperAPI] Transcript XML snippet: {transcript_text[:500]}")
                return None
        except Exception as e:
            logger.error(f"[ScraperAPI] HTML scraping failed: {e}")
            return None

    def extract_video_id(self, url: str) -> str:
        """Extract the YouTube video ID from a URL.

        Supports standard watch URLs and youtu.be short links. Keeps behavior
        consistent with tests, but uses urllib for slightly safer parsing.
        """
        raw = url.strip()

        # Try short form first: https://youtu.be/<id>?...
        if "youtu.be/" in raw:
            try:
                path_id = urlparse(raw).path.lstrip("/")
                if path_id:
                    return path_id.split("/")[0]
            except Exception:
                pass

            # Fallback string split (back-compatible with prior logic)
            return raw.split("youtu.be/")[1].split("?")[0]

        # Standard form: https://www.youtube.com/watch?v=<id>&...
        if "v=" in raw:
            try:
                parsed = urlparse(raw)
                qs = parse_qs(parsed.query)
                v = qs.get("v", [None])[0]
                if v:
                    return v
            except Exception:
                pass

            # Fallback string split (back-compatible with prior logic)
            return raw.split("v=")[1].split("&")[0]

        raise ValueError("Please use a standard YouTube URL")

    def _join_text_from_payload(self, payload: Any) -> dict[str, Any]:
        """Normalize various transcript payload shapes into a common dict.

        Handles:
        - FetchedTranscript: has `.snippets` (each with `.text`)
        - list[dict]: each element with a 'text' key (classic API)
        - list[str]: rare/defensive case; join directly
        Returns a mapping with: transcript, segments_count, language, is_generated
        Missing fields default to None.
        """
        language = getattr(payload, "language", None)
        is_generated = getattr(payload, "is_generated", None)

        # FetchedTranscript object with `.snippets`
        snippets = getattr(payload, "snippets", None)
        if isinstance(snippets, list):
            texts = [getattr(s, "text", "") for s in snippets]
            return {
                "transcript": " ".join(t for t in texts if t),
                "segments_count": len(snippets),
                "language": language,
                "is_generated": is_generated,
            }

        # List of dicts (classic youtube-transcript-api)
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            texts = [str(item.get("text", "")) for item in payload]
            return {
                "transcript": " ".join(t for t in texts if t),
                "segments_count": len(payload),
                "language": language,
                "is_generated": is_generated,
            }

        # List of strings (defensive fallback)
        if isinstance(payload, list) and payload and isinstance(payload[0], str):
            return {
                "transcript": " ".join(payload),
                "segments_count": len(payload),
                "language": language,
                "is_generated": is_generated,
            }

        # Unknown shape
        return {
            "transcript": "",
            "segments_count": 0,
            "language": language,
            "is_generated": is_generated,
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

            normalized: dict[str, Any] | None = None

            # First attempt via ScraperAPI HTML scraping if key present
            if self.use_scraper:
                logger.info(
                    f"Attempting transcript fetch via ScraperAPI HTML scraping for video_id={video_id}"
                )
                proxy_segments = self._fetch_transcript_via_scraperapi(video_id)
                if proxy_segments is not None:
                    normalized = self._join_text_from_payload(proxy_segments)
                    logger.info(
                        f"Transcript for {video_id} fetched via ScraperAPI HTML/ytInitialPlayerResponse endpoint"
                    )
                else:
                    logger.warning(
                        f"ScraperAPI HTML scraping failed for video_id={video_id}, falling back to direct API."
                    )
            if normalized is None:
                # Fallback to library direct access (may still work if IP not blocked)
                try:
                    payload = self.api.fetch(video_id, languages=["en", "en-US", "en-GB"])  # type: ignore[attr-defined]
                except AttributeError:
                    payload = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=["en", "en-US", "en-GB"]
                    )
                normalized = self._join_text_from_payload(payload)
                logger.info(f"Transcript for {video_id} fetched via direct youtube-transcript-api")

            return {
                "success": True,
                "video_id": video_id,
                "transcript": normalized["transcript"],
                "segments_count": normalized["segments_count"],
                "language": normalized.get("language"),
                "is_generated": normalized.get("is_generated"),
            }

        except Exception as e:
            logger.error(f"Transcript fetch failed: {e}")
            return {
                "success": False,
                "error": str(e) if str(e) else type(e).__name__,
                "error_type": type(e).__name__,
                "video_id": video_id,
            }

    def can_handle(self, url: str) -> bool:
        return "youtube.com" in url.lower() or "youtu.be" in url.lower()
