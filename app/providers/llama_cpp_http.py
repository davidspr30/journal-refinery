"""
llama_cpp_http.py

Provider that calls a locally running llama-server (llama.cpp) over HTTP.

llama-server exposes an OpenAI-compatible /v1/chat/completions endpoint.
This provider sends the assembled request as a single user message and
returns the text from the first completion choice.

The user is responsible for starting llama-server before using the app.
This provider does not start, stop, or monitor the server process.

Config fields (stored as JSON in the provider_configs table):

  base_url    The URL of the running llama-server.
              Default: "http://localhost:8080"

  model_name  Model identifier sent in the request body.
              If empty, the "model" field is omitted entirely — llama-server
              uses whatever model is currently loaded. Other OpenAI-compatible
              servers (Ollama, LM Studio) may require a specific value here.
              Default: "" (omit from request)

  api_key     Sent as "Authorization: Bearer <api_key>" if non-empty.
              Most local llama-server setups do not need this.
              Default: "" (no auth header)

  timeout     Seconds to wait for a response before giving up.
              Local model inference on CPU can be slow — 60 s is a
              reasonable ceiling for journal-length text.
              Default: 60

  max_tokens  Maximum number of tokens in the completion.
              Default: 2048
"""

import json

import httpx

# Named constants so they appear in one place and are easy to adjust.
DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_TIMEOUT = 60        # seconds; local CPU inference can be slow
DEFAULT_MAX_TOKENS = 2048
HEALTH_CHECK_TIMEOUT = 5   # seconds; short — just checking connectivity


class LlamaCppHttpProvider:
    provider_type = "llama_cpp_http"
    provider_name = "Local llama-server (llama.cpp)"

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.base_url = cfg.get("base_url", DEFAULT_BASE_URL).rstrip("/")
        self.model_name = cfg.get("model_name", "")
        self.api_key = cfg.get("api_key", "")
        self.timeout = float(cfg.get("timeout", DEFAULT_TIMEOUT))
        self.max_tokens = int(cfg.get("max_tokens", DEFAULT_MAX_TOKENS))

        # Snapshot everything except the api_key (no secrets in run records).
        self.config_snapshot = json.dumps({
            "base_url": self.base_url,
            "model_name": self.model_name,
            "timeout": self.timeout,
            "max_tokens": self.max_tokens,
        })

    # ------------------------------------------------------------------
    # ProviderProtocol interface
    # ------------------------------------------------------------------

    def validate_config(self) -> list[str]:
        """
        Check that the stored settings make basic sense.
        Returns a list of error strings; empty list means all good.
        Does NOT make any network calls.
        """
        errors = []
        if not self.base_url:
            errors.append("base_url is required.")
        if self.timeout <= 0:
            errors.append("timeout must be a positive number of seconds.")
        if self.max_tokens <= 0:
            errors.append("max_tokens must be a positive integer.")
        return errors

    def health_check(self) -> tuple[bool, str]:
        """
        Test whether llama-server is reachable by calling GET /health.

        llama-server returns:
          200  — model loaded and ready
          503  — server running but model still loading
          anything else — server up but unclear state

        Uses a synchronous httpx.Client with a short timeout since this
        method is not called in the hot path.
        """
        config_errors = self.validate_config()
        if config_errors:
            return (False, f"Bad config: {'; '.join(config_errors)}")

        try:
            with httpx.Client(timeout=HEALTH_CHECK_TIMEOUT) as client:
                r = client.get(f"{self.base_url}/health")

            if r.status_code == 200:
                return (True, "llama-server is running")
            if r.status_code == 503:
                return (False, "llama-server is still loading the model. Try again in a moment.")
            # Some servers (e.g. Ollama) don't have /health but will return
            # 404 — treat that as "connected but health endpoint absent".
            return (True, f"Connected to {self.base_url} (HTTP {r.status_code})")

        except httpx.ConnectError:
            return (False, f"Could not connect to {self.base_url}. Is llama-server running?")
        except httpx.TimeoutException:
            return (False, f"Connection to {self.base_url} timed out. Is llama-server running?")
        except Exception as e:
            return (False, f"Unexpected error during health check: {str(e)}")

    async def refine_transcript(self, assembled: str) -> tuple[str | None, str | None]:
        """
        Send the assembled request to llama-server and return the response.

        Uses POST /v1/chat/completions (OpenAI-compatible format).
        The assembled request is sent as a single user-role message.

        Returns (polished_text, None) on success.
        Returns (None, error_string) on any failure.
        """
        config_errors = self.validate_config()
        if config_errors:
            return (None, f"Provider not configured: {'; '.join(config_errors)}")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "messages": [{"role": "user", "content": assembled}],
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        # Only include "model" if explicitly set — most local servers use
        # whatever model is already loaded and accept requests without it.
        if self.model_name:
            payload["model"] = self.model_name

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            text = data["choices"][0]["message"]["content"]
            return (text, None)

        except httpx.ConnectError:
            return (
                None,
                f"Could not connect to llama-server at {self.base_url}. Is it running?",
            )
        except httpx.TimeoutException:
            return (
                None,
                f"Request to llama-server timed out after {int(self.timeout)}s. "
                "The model may still be generating — try a shorter transcript or "
                "increase the timeout in provider settings.",
            )
        except httpx.HTTPStatusError as e:
            body_preview = e.response.text[:300]
            return (
                None,
                f"llama-server returned HTTP {e.response.status_code}: {body_preview}",
            )
        except (KeyError, IndexError):
            return (
                None,
                "llama-server returned a response in an unexpected format. "
                "Expected choices[0].message.content in the JSON body.",
            )
        except (ValueError, json.JSONDecodeError):
            return (
                None,
                "llama-server returned a response that could not be parsed as JSON.",
            )
        except Exception as e:
            return (None, f"Unexpected error calling llama-server: {str(e)}")
