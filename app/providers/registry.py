"""
registry.py

Maps provider_type strings to provider classes and provides the
get_provider() factory that the /refine route calls at request time.

To add a new provider:
  1. Create a class in app/providers/ that satisfies ProviderProtocol.
  2. Add it to _REGISTRY below.
"""

from app.providers.manual_export import ManualExportProvider

_REGISTRY = {
    "manual_export": ManualExportProvider,
}


def get_provider(conn):
    """
    Read active_provider_type from the settings table and return the
    corresponding provider instance.

    Falls back to ManualExportProvider if the setting is missing or
    names an unrecognised provider type.
    """
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'active_provider_type'"
    ).fetchone()
    provider_type = row["value"] if row else "manual_export"
    cls = _REGISTRY.get(provider_type, ManualExportProvider)
    return cls()


def list_provider_types() -> list[str]:
    """Return the keys of all registered providers."""
    return list(_REGISTRY.keys())
