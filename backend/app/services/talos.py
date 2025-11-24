import requests
from app.config import BASE_HEADERS, AUTH_TOKEN
from app.utils.text import json_to_text_global, sanitize_text_global


def call_talos(url: str, prompt: str, multiround_convo: int = 1, extra_headers=None, timeout=(15, 180)) -> str:
    headers = dict(BASE_HEADERS)
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    if extra_headers:
        headers.update(extra_headers)

    payload = {"agency_goal": prompt, "multiround_convo": multiround_convo}
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return sanitize_text_global(json_to_text_global(resp.json()))

