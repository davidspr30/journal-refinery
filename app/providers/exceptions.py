"""
exceptions.py

Provider-specific exceptions.
"""


class ProviderError(Exception):
    """Base class for all provider errors."""


class ProviderUnavailable(ProviderError):
    """Raised when a provider cannot be reached (e.g. server not running)."""
