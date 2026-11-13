"""Gọi AI Hybrid: Cloud LLM (Gemini / Groq / OpenAI với Multi-Key Rotation) + ML CPU (LinearSVC + RandomForest).

- Không phụ thuộc GPU cục bộ (Ollama chỉ giữ lại làm tùy chọn thủ công).
- Hỗ trợ xoay vòng nhiều API Key (KeyRotator học từ case study Homigo) để nhân hạn mức miễn phí và tự động chuyển key khi gặp HTTP 429.
- Khi không cấu hình Cloud API Key hoặc hết hạn mức, hệ thống dùng trực tiếp ML CPU (< 2ms/tin) + Bộ phân tích thực thể Đà Nẵng.
"""

import json
import logging
import time

import httpx

from .config import settings
from .db import SessionLocal, utcnow
from .models import AIUsage

log = logging.getLogger(__name__)
_ollama = {"ok": None, "t": 0.0}


class KeyRotator:
    """Bộ xoay vòng nhiều API Key theo chiến lược Least-Used kèm Cooldown khi chạm Rate Limit (HTTP 429)."""

    def __init__(self, raw_keys: str) -> None:
        self.raw_keys = raw_keys or ""
        self.keys: list[str] = [k.strip() for k in self.raw_keys.split(",") if k.strip()]
        self.usage_counts: dict[str, int] = {k: 0 for k in self.keys}
        self.cooldown_until: dict[str, float] = {k: 0.0 for k in self.keys}

    def next_key(self) -> str | None:
        if not self.keys:
            return None
        now = time.time()
        available = [k for k in self.keys if self.cooldown_until.get(k, 0.0) <= now]
        if not available:
            # Nếu mọi key đều đang cooldown, chọn key sắp hết hạn cooldown sớm nhất
            chosen = min(self.keys, key=lambda k: self.cooldown_until.get(k, 0.0))
        else:
            chosen = min(available, key=lambda k: self.usage_counts.get(k, 0))
        self.usage_counts[chosen] = self.usage_counts.get(chosen, 0) + 1
        return chosen

    def mark_rate_limited(self, key: str, cooldown_sec: int = 60) -> None:
        if key in self.cooldown_until:
            self.cooldown_until[key] = time.time() + max(1, cooldown_sec)


_rotators: dict[str, KeyRotator] = {}


def _get_rotator(provider: str, raw_keys: str) -> KeyRotator:
    rot = _rotators.get(provider)
    if rot is None or rot.raw_keys != (raw_keys or ""):
        rot = KeyRotator(raw_keys)
        _rotators[provider] = rot
    return rot


def _ollama_up() -> bool:
    if _ollama["ok"] is None or time.time() - _ollama["t"] > 30:
        try:
            _ollama["ok"] = httpx.get(f"{settings.ollama_url}/api/tags", timeout=2).status_code == 200
        except httpx.HTTPError:
            _ollama["ok"] = False
        _ollama["t"] = time.time()
    return bool(_ollama["ok"])


def llm_available() -> bool:
    if settings.llm_provider == "ollama":
        return _ollama_up()
    if settings.llm_provider == "gemini":
        return bool(_get_rotator("gemini", settings.gemini_api_key).keys)
    if settings.llm_provider == "openai":
        return bool(_get_rotator("openai", settings.openai_api_key).keys)
    return False


def model_name() -> str:
    return {"ollama": settings.ollama_model, "gemini": settings.gemini_model}.get(
        settings.llm_provider, settings.openai_model
    )


def active_ai_label() -> str:
    """Nhãn hiển thị kiến trúc AI đang vận hành trên trang Tổng quan hệ thống."""
    if llm_available():
        return f"{model_name()} + ML CPU (LinearSVC + RF)"
    return "ML CPU (LinearSVC + RF) · Bộ phân tích Đà Nẵng"


def record_usage(task: str, model: str, tokens: int, calls: int = 1) -> None:
    db = SessionLocal()
    try:
        day = utcnow().date()
        row = db.query(AIUsage).filter_by(day=day, task=task, model=model).first()
        if not row:
            row = AIUsage(day=day, task=task, model=model, calls=0, tokens=0, cost_vnd=0)
            db.add(row)
        row.calls += calls
        row.tokens += tokens
        if settings.llm_provider != "ollama":
            row.cost_vnd += tokens / 1000 * settings.llm_cost_per_1k_tokens_vnd
        db.commit()
    finally:
        db.close()


def chat_json(system: str, user: str, task: str, schema: dict | None = None) -> dict | None:
    if not llm_available():
        return None
    try:
        if settings.llm_provider == "ollama":
            r = httpx.post(
                f"{settings.ollama_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "format": schema or "json",
                    "think": False,
                    "stream": False,
                    "options": {"temperature": 0},
                },
                timeout=settings.ollama_timeout,
            )
            r.raise_for_status()
            data = r.json()
            text = data["message"]["content"]
            tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            record_usage(task, model_name(), int(tokens))
            return json.loads(text)

        if settings.llm_provider == "gemini":
            rotator = _get_rotator("gemini", settings.gemini_api_key)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
            body = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
            }
            for _ in range(max(1, len(rotator.keys))):
                key = rotator.next_key()
                if not key:
                    break
                r = httpx.post(url, params={"key": key}, json=body, timeout=20)
                if r.status_code == 429:
                    rotator.mark_rate_limited(key, cooldown_sec=60)
                    continue
                r.raise_for_status()
                data = r.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
                record_usage(task, model_name(), int(tokens))
                return json.loads(text)
            return None

        rotator = _get_rotator("openai", settings.openai_api_key)
        for _ in range(max(1, len(rotator.keys))):
            key = rotator.next_key()
            if not key:
                break
            r = httpx.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": settings.openai_model,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                },
                timeout=20,
            )
            if r.status_code == 429:
                rotator.mark_rate_limited(key, cooldown_sec=60)
                continue
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            record_usage(task, model_name(), int(tokens))
            return json.loads(text)
        return None
    except Exception as exc:
        log.warning("LLM lỗi (%s), chuyển sang ML CPU + bộ phân tích luật", exc)
        return None
