from __future__ import annotations

import json

import httpx

from ..config import settings


class LLMGateway:
    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(settings.llm_timeout_seconds)

    def _ensure_configured(self) -> None:
        if not settings.llm_api_key:
            raise ValueError("在线模型未配置：请设置 LLM_API_KEY 或 ARK_API_KEY。")
        if not settings.llm_model:
            raise ValueError("在线模型未配置：请设置 LLM_MODEL 或 ARK_MODEL。")

    def _endpoint(self) -> str:
        return settings.llm_base_url.rstrip("/") + "/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        if settings.llm_api_name:
            headers["X-Api-Name"] = settings.llm_api_name
        return headers

    def _payload(self, *, system_prompt: str, user_prompt: str, temperature: float) -> dict:
        payload = {
            "model": settings.llm_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if settings.llm_api_name:
            payload["user"] = settings.llm_api_name
        return payload

    async def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        self._ensure_configured()
        try:
            async with httpx.AsyncClient(timeout=self._timeout()) as client:
                response = await client.post(
                    self._endpoint(),
                    headers=self._headers(),
                    json=self._payload(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                    ),
                )
        except Exception as error:
            raise ValueError("在线模型调用失败，请检查网络或 LLM_BASE_URL。") from error
        return self._extract_text(response)

    def generate_text_sync(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        self._ensure_configured()
        try:
            with httpx.Client(timeout=self._timeout()) as client:
                response = client.post(
                    self._endpoint(),
                    headers=self._headers(),
                    json=self._payload(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                    ),
                )
        except Exception as error:
            raise ValueError("在线模型调用失败，请检查网络或 LLM_BASE_URL。") from error
        return self._extract_text(response)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict:
        content = await self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        return self._parse_json(content)

    def generate_json_sync(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict:
        content = self.generate_text_sync(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        return self._parse_json(content)

    def _extract_text(self, response: httpx.Response) -> str:
        if response.status_code == 401:
            raise ValueError("在线模型鉴权失败：API Key 无效或已过期。")
        if response.status_code >= 400:
            raise ValueError(f"在线模型调用失败（HTTP {response.status_code}）。")

        body = response.json()
        content = (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            raise ValueError("在线模型返回为空。")
        return content

    def _parse_json(self, content: str) -> dict:
        raw = content.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("模型返回格式异常，未找到 JSON。")
        snippet = raw[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError as error:
            raise ValueError("模型返回格式异常，JSON 解析失败。") from error
