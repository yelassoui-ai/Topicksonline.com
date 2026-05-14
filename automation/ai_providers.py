"""
TopPicksOnline.com — Multi-Provider AI System
Stacks 3 free AI providers for near-zero failure rate:
  1. Google Gemini (primary — best quality)
  2. Groq (fallback — Llama 3.3 70B, ultra-fast)
  3. NVIDIA NIM (backup — Llama 3.1 70B)
"""

import json
import os
import re
import time


def _get_api_keys():
    """Get API keys from config or environment."""
    try:
        from automation import config
        return {
            "gemini": getattr(config, "GEMINI_API_KEY", ""),
            "groq": getattr(config, "GROQ_API_KEY", ""),
            "nvidia": getattr(config, "NVIDIA_API_KEY", ""),
        }
    except ImportError:
        return {
            "gemini": os.environ.get("GEMINI_API_KEY", ""),
            "groq": os.environ.get("GROQ_API_KEY", ""),
            "nvidia": os.environ.get("NVIDIA_API_KEY", ""),
        }


def _call_gemini(prompt: str, api_key: str, model: str, temperature: float, max_tokens: int) -> str:
    """Call Google Gemini API."""
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": temperature, "max_output_tokens": max_tokens},
    )
    return response.text.strip()


def _call_groq(prompt: str, api_key: str, temperature: float, max_tokens: int) -> str:
    """Call Groq API (OpenAI-compatible)."""
    import urllib.request

    body = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["choices"][0]["message"]["content"].strip()


def _call_nvidia(prompt: str, api_key: str, temperature: float, max_tokens: int) -> str:
    """Call NVIDIA NIM API (OpenAI-compatible)."""
    import urllib.request

    body = json.dumps({
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["choices"][0]["message"]["content"].strip()


def generate_with_failover(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 65536,
    max_retries: int = 5,
    task_name: str = "generation",
) -> str:
    """
    Try to generate content using multiple AI providers with automatic failover.

    Order: Gemini → Groq → NVIDIA NIM → retry cycle
    Returns raw text response from whichever provider succeeds.
    Raises RuntimeError if ALL providers fail ALL attempts.
    """
    keys = _get_api_keys()

    # Build provider rotation — primary first, then fallbacks, then retries
    providers = []

    # Attempt 1: Gemini (best quality)
    if keys["gemini"]:
        providers.append(("gemini", "gemini-2.5-flash"))

    # Attempt 2: Groq (fast, free)
    if keys["groq"]:
        providers.append(("groq", "llama-3.3-70b-versatile"))

    # Attempt 3: NVIDIA NIM (backup)
    if keys["nvidia"]:
        providers.append(("nvidia", "meta/llama-3.1-70b-instruct"))

    # Attempt 4: Gemini retry
    if keys["gemini"]:
        providers.append(("gemini", "gemini-2.5-flash"))

    # Attempt 5: Groq retry
    if keys["groq"]:
        providers.append(("groq", "llama-3.3-70b-versatile"))

    # Ensure we have at least some providers
    if not providers:
        raise RuntimeError("No AI API keys configured! Set GEMINI_API_KEY, GROQ_API_KEY, or NVIDIA_API_KEY.")

    # Pad to max_retries if needed
    while len(providers) < max_retries:
        providers.append(providers[0])

    errors = []

    for attempt, (provider, model) in enumerate(providers[:max_retries], 1):
        # Wait between retries (increasing delay)
        if attempt > 1:
            wait_time = 15 * attempt
            print(f"   ⏳ Waiting {wait_time}s before retry...")
            time.sleep(wait_time)

        print(f"   🤖 {task_name} attempt {attempt}/{min(len(providers), max_retries)} — {provider.upper()} ({model})")

        try:
            if provider == "gemini":
                raw = _call_gemini(prompt, keys["gemini"], model, temperature, max_tokens)
            elif provider == "groq":
                # Groq has a 32K token limit for output
                raw = _call_groq(prompt, keys["groq"], temperature, min(max_tokens, 32000))
            elif provider == "nvidia":
                raw = _call_nvidia(prompt, keys["nvidia"], temperature, min(max_tokens, 32000))
            else:
                continue

            # Validate we got something
            if raw and len(raw) > 100:
                print(f"   ✅ {provider.upper()} succeeded ({len(raw)} chars)")
                return raw
            else:
                raise ValueError(f"Response too short: {len(raw)} chars")

        except Exception as e:
            error_msg = f"{provider.upper()}: {str(e)[:200]}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")

    raise RuntimeError(f"All {len(errors)} attempts failed:\n" + "\n".join(f"  {i+1}. {e}" for i, e in enumerate(errors)))


def parse_json_response(raw_text: str) -> dict:
    """Parse JSON from AI response, handling markdown code fences."""
    text = raw_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)

    return json.loads(text)
