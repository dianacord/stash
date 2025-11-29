"""Prometheus metrics service for FastAPI application.

Provides Prometheus-style metrics collection following best practices:

Uses explicit CollectorRegistry for predictable behavior in containerized environments.
"""

import time

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

# Metrics endpoint path - defined here so metrics module owns its configuration
METRICS_PATH = "/api/metrics"


class MetricsService:
    """Service for collecting and exposing Prometheus metrics."""

    def __init__(self):
        """Initialize metrics registry and collectors."""
        # Explicit registry (avoid default) for clarity & potential future grouping
        self.registry = CollectorRegistry()

        # Define metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests processed",
            ["method", "path", "status_code"],
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "Duration of HTTP requests in seconds",
            ["method", "path", "status_code"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )

        self.http_errors_total = Counter(
            "http_errors_total",
            "Total HTTP error responses (4xx and 5xx)",
            ["method", "path", "status_code"],
            registry=self.registry,
        )

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        start_time: float,
        exclude_path: str | None = None,
    ) -> None:
        """
        Record metrics for a completed HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path pattern
            status_code: HTTP response status code
            start_time: Request start timestamp from time.perf_counter()
            exclude_path: Optional path to exclude from metrics (e.g., metrics endpoint itself)
        """
        # Skip metrics endpoint itself to prevent self-scrape pollution
        if exclude_path and path == exclude_path:
            return

        duration = time.perf_counter() - start_time
        status_str = str(status_code)

        # Record request count
        self.http_requests_total.labels(
            method=method, path=path, status_code=status_str
        ).inc()

        # Record request duration
        self.http_request_duration_seconds.labels(
            method=method, path=path, status_code=status_str
        ).observe(duration)

        # Record errors (4xx and 5xx)
        if 400 <= status_code < 600:
            self.http_errors_total.labels(
                method=method, path=path, status_code=status_str
            ).inc()

    def get_metrics_response(self) -> Response:
        """
        Generate Prometheus exposition format response.

        Returns:
            FastAPI Response with metrics in Prometheus text format
        """
        output = generate_latest(self.registry)
        return Response(content=output, media_type=CONTENT_TYPE_LATEST)


# Global metrics service instance
_metrics_service: MetricsService | None = None


def get_metrics_service() -> MetricsService:
    """Get or create the global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
