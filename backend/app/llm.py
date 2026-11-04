import json

import httpx

from .config import BIFROST_URL, EXTRACTOR_MODEL, JUDGE_MODEL, env

fallback_events = 0


async def complete(system: str, prompt: str, *, strong: bool = False, outage: bool = False) -> str:
    global fallback_events
    headers = {"Content-Type": "application/json"}
    if env("BIFROST_API_KEY"):
        headers["Authorization"] = f"Bearer {env('BIFROST_API_KEY')}"
    model = JUDGE_MODEL if strong else EXTRACTOR_MODEL
    if outage:
        model = "groq/__freshcheck_simulated_outage__"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.post(
                f"{BIFROST_URL}/v1/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError):
            fallback_events += 1
        fallbacks = [env("FALLBACK_MODEL", "groq/openai/gpt-oss-20b")]
        if env("OPENAI_API_KEY"):
            fallbacks.append("openai/gpt-4o-mini")
        last_error = None
        for fallback_model in fallbacks:
            payload["model"] = fallback_model
            try:
                response = await client.post(
                    f"{BIFROST_URL}/v1/chat/completions", headers=headers, json=payload
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("No Bifrost fallback model is configured")


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(text)
