"""LLM 서비스 추상화.

UPSTAGE API 키가 있으면 실제 Solar Chat API를 호출하고,
키가 없거나 호출이 실패하면 개발용 fallback 응답을 사용합니다.
"""

from __future__ import annotations

import httpx

from app.config import settings


class LLMService:
    """설정된 Upstage Solar 모델을 감싸는 작은 래퍼."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.llm_model
        self.api_key = settings.upstage_api_key
        self.base_url = settings.upstage_base_url.rstrip("/")
        self.timeout_seconds = settings.llm_timeout_seconds

    def _fallback_response(self, user_prompt: str) -> str:
        """실제 API 사용이 불가할 때 쓰는 결정론적 로컬 폴백."""

        head = f"[{self.model_name}:fallback]"
        clipped = user_prompt.strip().replace("\n", " ")[:140]
        return f"{head} {clipped}"

    def _call_upstage(self, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
        """Upstage Chat Completions API를 호출한다.

        Upstage는 OpenAI 호환 chat completions 인터페이스를 제공하므로,
        `POST /chat/completions` 형식으로 요청합니다.
        """

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "stream": False,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        choices = payload.get("choices", [])
        if not choices:
            raise ValueError("Upstage API returned no choices")

        message = choices[0].get("message", {})
        content = message.get("content", "").strip()
        if not content:
            raise ValueError("Upstage API returned empty content")

        return content

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
        """가능하면 Upstage를 사용해 프롬프트에서 텍스트를 생성한다."""

        if not self.api_key:
            return self._fallback_response(user_prompt)

        try:
            return self._call_upstage(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
        except (httpx.HTTPError, ValueError):
            return self._fallback_response(user_prompt)


llm_service = LLMService()
