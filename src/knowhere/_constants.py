"""Constants used throughout the Knowhere SDK."""

from __future__ import annotations

# Base URL for the Knowhere API
DEFAULT_BASE_URL: str = "https://api.knowhereto.ai"

# Environment variable names
ENV_API_KEY: str = "KNOWHERE_API_KEY"
ENV_BASE_URL: str = "KNOWHERE_BASE_URL"
ENV_LOG_LEVEL: str = "KNOWHERE_LOG_LEVEL"

# Timeout defaults (in seconds)
DEFAULT_TIMEOUT: float = 60.0
DEFAULT_UPLOAD_TIMEOUT: float = 600.0
DEFAULT_POLL_TIMEOUT: float = 1800.0
DEFAULT_POLL_INTERVAL: float = 10.0

# Retry configuration
DEFAULT_MAX_RETRIES: int = 5

# Polling configuration
MAX_POLL_INTERVAL: float = 30.0
POLL_BACKOFF_MULTIPLIER: float = 1.2
POLL_BACKOFF_THRESHOLD: float = 60.0

# API version prefix
API_VERSION: str = "v1"

# Terminal job statuses that indicate polling should stop
TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "failed"})
