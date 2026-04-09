"""
manual_export.py

A provider that performs no AI refinement.

Instead of sending the transcript to a model, it returns the fully
assembled request as-is. The review page detects this provider type
and displays the text in a copy-paste textarea so the user can paste
it into any external AI tool of their choice.

This is the default provider. It works with no API key, no local model,
and no network connection.
"""


class ManualExportProvider:
    provider_type = "manual_export"
    provider_name = "Manual Export"

    def __init__(self, config=None):
        # No configuration needed; config arg accepted for a uniform
        # constructor signature across all providers.
        self.config_snapshot = "{}"

    def validate_config(self) -> list[str]:
        return []

    def health_check(self) -> tuple[bool, str]:
        return (True, "ready")

    async def refine_transcript(self, assembled: str) -> tuple[str | None, str | None]:
        """
        Return the assembled request unchanged.

        The caller (the /refine route) checks provider_type and skips
        parse_response() for manual_export runs, storing the assembled
        text directly as output_polished.
        """
        return (assembled, None)
