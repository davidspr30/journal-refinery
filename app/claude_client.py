"""
claude_client.py

Sends the assembled request to Claude and returns the response text.

Usage:
    from app.claude_client import call_claude

    text, error = call_claude(assembled_request)
    if error:
        # handle the error message
    else:
        # use text

This module only makes the API call. It does not parse the response,
save anything to the database, or know about the intake form.
"""

import anthropic

from app.config import ANTHROPIC_API_KEY, CLAUDE_MAX_TOKENS, CLAUDE_MODEL


def call_claude(assembled_request):
    """
    Send assembled_request to Claude and return (response_text, error).

    On success: returns (text, None)
    On failure: returns (None, human-readable error message)

    This is a synchronous function. In async route handlers, call it with:
        text, error = await asyncio.to_thread(call_claude, assembled_request)
    """
    if not ANTHROPIC_API_KEY:
        return None, (
            "ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your Anthropic API key."
        )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            messages=[
                {"role": "user", "content": assembled_request}
            ],
        )
        return message.content[0].text, None

    except anthropic.AuthenticationError:
        return None, (
            "Authentication failed. Check that ANTHROPIC_API_KEY in your .env "
            "file is correct and has not expired."
        )

    except anthropic.RateLimitError:
        return None, (
            "Rate limit reached. Please wait a moment and try again."
        )

    except anthropic.APIConnectionError:
        return None, (
            "Could not reach the Claude API. Check your internet connection."
        )

    except anthropic.APIStatusError as e:
        return None, f"Claude API error ({e.status_code}): {e.message}"

    except anthropic.APIError as e:
        return None, f"Claude API error: {str(e)}"

    except Exception as e:
        return None, f"Unexpected error calling Claude: {str(e)}"
