"""
registry.py

Maps provider_type strings to factory callables and provides the
get_provider() function that the /refine route calls at request time.

Each factory is a callable that takes a config dict and returns a
provider instance. This keeps get_provider() data-driven — adding a
new provider requires only a new entry in _REGISTRY, not new branching
logic in the factory.

To add a new provider:
  1. Create a class in app/providers/ that satisfies ProviderProtocol.
  2. Add a lambda (or any callable) to _REGISTRY below.
"""

import json

from app.providers.manual_export import ManualExportProvider
from app.providers.llama_cpp_http import LlamaCppHttpProvider

_REGISTRY = {
    "manual_export":  lambda config: ManualExportProvider(config),
    "llama_cpp_http": lambda config: LlamaCppHttpProvider(config),
}


def get_provider(conn):
    """
    Read active_provider_type from the settings table, load its stored
    config from provider_configs, and return a ready provider instance.

    Falls back to ManualExportProvider if the setting is missing or
    names an unrecognised provider type.
    """
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'active_provider_type'"
    ).fetchone()
    provider_type = row["value"] if row else "manual_export"

    factory = _REGISTRY.get(provider_type)
    if factory is None:
        # Unrecognised type — fall back silently so the app stays usable.
        factory = _REGISTRY["manual_export"]
        provider_type = "manual_export"

    config = _load_config(conn, provider_type)
    return factory(config)


def list_provider_types() -> list[str]:
    """Return the keys of all registered providers."""
    return list(_REGISTRY.keys())


def _load_config(conn, provider_type: str) -> dict:
    """
    Load the stored config dict for a provider from provider_configs.
    Returns {} if no row exists or if the JSON is malformed.
    """
    row = conn.execute(
        "SELECT config_json FROM provider_configs WHERE provider_type = ?",
        (provider_type,),
    ).fetchone()
    if row is None:
        return {}
    try:
        return json.loads(row["config_json"])
    except (ValueError, TypeError):
        return {}
