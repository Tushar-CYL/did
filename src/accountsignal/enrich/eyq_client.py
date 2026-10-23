"""EYQ client — OpenAI-compatible chat wrapper for EY's internal LLM endpoint.

Reads EYQ_INCUBATOR_ENDPOINT / EYQ_INCUBATOR_KEY / EYQ_MODEL from settings. The
exact auth header style varies by deployment, so we try the common ones. A mock
mode lets the whole pipeline (enrichment + Excel + dashboard) be built and tested
on a machine that cannot reach the EY network; real EYQ runs on the office laptop.
"""
from __future__ import annotations

import json
import logging
import re

import requests

log = logging.getLogger("accountsignal.enrich.eyq")


class EYQError(RuntimeError):
    pass


class EYQClient:
    def __init__(self, endpoint: str, key: str, model: str = "gpt-5.2",
                 timeout: int = 60, mock: bool = False) -> None:
        self.endpoint = (endpoint or "").rstrip("/")
        self.key = key or ""
        self.model = model or "gpt-5.2"
        self.timeout = timeout
        self.mock = mock or not (self.endpoint and self.key)

    # ---- public API -------------------------------------------------------
    def chat_json(self, system: str, user: str, max_tokens: int = 900) -> dict:
        """Return the model's reply parsed as JSON (robust to code fences)."""
        if self.mock:
            return {}  # callers supply their own deterministic mock output
        text = self._chat(system, user, max_tokens)
        return _loads_loose(text)

    def chat_text(self, system: str, user: str, max_tokens: int = 500) -> str:
        if self.mock:
            return ""
        return self._chat(system, user, max_tokens)

    # ---- transport --------------------------------------------------------
    def _chat(self, system: str, user: str, max_tokens: int) -> str:
        url = f"{self.endpoint}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        # try a few auth header styles used by Azure/OpenAI-compatible gateways
        header_variants = [
            {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            {"api-key": self.key, "Content-Type": "application/json"},
            {"x-api-key": self.key, "Content-Type": "application/json"},
        ]
        last_err = None
        for headers in header_variants:
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                if r.status_code == 200:
                    data = r.json()
                    return data["choices"][0]["message"]["content"]
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code in (401, 403):
                    continue  # try next auth style
                break
            except requests.RequestException as exc:
                last_err = str(exc)
        raise EYQError(f"EYQ call failed: {last_err}")


def _loads_loose(text: str) -> dict:
    """Parse JSON that may be wrapped in ```json fences or have surrounding prose."""
    if not text:
        return {}
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}
