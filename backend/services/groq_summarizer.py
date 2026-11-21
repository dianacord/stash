import os

from ddtrace.trace import tracer
from groq import Groq

# Defaults are centralized for easier tuning/testing
# Groq retired Llama 3.3 70B in 2026; gpt-oss-120b is the largest chat model it serves.
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 0.4
# gpt-oss is a reasoning model: its hidden reasoning counts toward this limit too.
DEFAULT_MAX_OUTPUT_TOKENS = 2000


class GroqSummarizer:
    """Service to adaptively summarize video transcripts using Groq AI"""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=api_key)

    def summarize(self, transcript: str, max_length: int = 12000) -> dict:
        """
        Generate adaptive notes from a video transcript.

        Args:
            transcript: The full transcript text
            max_length: Maximum characters to send to API (to avoid token limits)

        Returns:
            dict with 'success' and 'summary' or 'error'
        """
        try:
            if not transcript or not transcript.strip():
                return {"success": False, "error": "Transcript is empty"}
            truncated_transcript = transcript[:max_length]

            # Datadog APM: record each LLM call as its own span (service "stash-groq"),
            # so its latency, error rate and token usage can be graphed and alerted
            # on separately from the HTTP request around it. A no-op without an Agent.
            with tracer.trace(
                "groq.chat.completion", service="stash-groq", resource=DEFAULT_MODEL
            ) as span:
                span.set_tag("llm.model", DEFAULT_MODEL)
                span.set_metric("llm.transcript_chars", len(transcript))
                span.set_metric("llm.truncated", int(len(transcript) > max_length))
                response = self._create_completion(truncated_transcript)
                usage = getattr(response, "usage", None)
                for field in ("prompt_tokens", "completion_tokens"):
                    value = getattr(usage, field, None)
                    if isinstance(value, int):
                        span.set_metric(f"llm.{field}", value)

            summary = response.choices[0].message.content

            return {"success": True, "summary": summary}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_completion(self, truncated_transcript: str):
        return self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that summarizes YouTube transcripts into concise, "
                        "structured notes. Adapt your style depending on the type of video:\n\n"
                        "- If it's a recipe → list ingredients and step-by-step instructions.\n"
                        "- If it's a travel/destination video → create an itinerary with places, activities, and tips.\n"
                        "- If it's an educational/talk/tutorial → list key points, definitions, and takeaways.\n\n"
                        "Keep notes clear, skimmable, and avoid filler words. Use Markdown with emojis if useful."
                        "Keep notes concise, aim for 400-500 words"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Here is the transcript:\n\n{truncated_transcript}\n\nPlease create adaptive notes.",
                },
            ],
            temperature=DEFAULT_TEMPERATURE,  # more deterministic
            max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,  # longer output allowed
        )
