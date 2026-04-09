"""
base.py

ProviderProtocol — the interface every refinement provider must satisfy.

Using typing.Protocol means no inheritance is required. Any class that
defines the listed attributes and methods satisfies the protocol and can
be passed wherever a ProviderProtocol is expected.
"""

from typing import Protocol


class ProviderProtocol(Protocol):
    provider_type: str
    """Short machine-readable identifier, e.g. 'manual_export', 'llama_cpp_http'."""

    provider_name: str
    """Human-readable display name shown in the UI."""

    config_snapshot: str
    """JSON string of the current config (no secrets). Stored on each run record."""

    def validate_config(self) -> list[str]:
        """
        Check that the provider's settings are valid.
        Return a list of human-readable error strings.
        Return an empty list if everything looks good.
        Does NOT make any network calls.
        """
        ...

    def health_check(self) -> tuple[bool, str]:
        """
        Test whether the provider is ready.
        Return (True, message) on success, (False, message) on failure.
        For providers with no external dependency, always return (True, 'ready').
        """
        ...

    async def refine_transcript(self, assembled: str) -> tuple[str | None, str | None]:
        """
        Run the assembled request through the provider.
        Return (output_text, None) on success.
        Return (None, error_string) on failure.
        """
        ...
