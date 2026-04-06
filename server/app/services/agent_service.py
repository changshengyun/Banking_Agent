from __future__ import annotations

import json
from functools import lru_cache

import httpx

from ..config import settings
from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.common import SuggestedAction, ToolUsage
from .bank_host import BankHostService, get_bank_host_service
from .outdoor_knowledge import OutdoorKnowledgeService


class AgentService:
    def __init__(
        self,
        bank_host: BankHostService | None = None,
        outdoor_knowledge: OutdoorKnowledgeService | None = None,
    ) -> None:
        self.bank_host = bank_host or get_bank_host_service()
        self.outdoor_knowledge = outdoor_knowledge or OutdoorKnowledgeService()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        latest_message = request.messages[-1].content.strip()
        self.bank_host.repository.add_chat_message(
            request.context.session_id,
            "user",
            latest_message,
        )

        response = await self._live_chat_response(latest_message)

        self.bank_host.repository.add_chat_message(
            request.context.session_id,
            "assistant",
            response.assistant_message,
        )
        return response

    def evaluate_secondary_intercept(
        self,
        *,
        user_reply: str,
        semantic_summary: str,
        risk_category: str,
        risk_level: str,
        matched_keywords: list[str],
        follow_up_questions: list[str],
    ) -> tuple[str, float, list[str], str]:
        if not settings.llm_api_key:
            raise ValueError("在线模型未配置：请设置 LLM_API_KEY 或 ARK_API_KEY。")
        if not settings.llm_model:
            raise ValueError("在线模型未配置：请设置 LLM_MODEL 或 ARK_MODEL。")

        prompt = (
            "你是银行风控二次质询模型。请根据上下文判断是否允许继续转账。\n"
            "返回严格 JSON，不要返回额外文本。字段如下：\n"
            "{"
            '"secondary_decision":"pass_secondary 或 block_secondary",'
            '"final_risk_after_secondary":0到1之间小数,'
            '"reasons":["原因1","原因2"],'
            '"assistant_message":"给用户的简短结论"'
            "}\n"
            f"预检语义摘要：{semantic_summary}\n"
            f"知识库风险分类：{risk_category}\n"
            f"知识库风险等级：{risk_level}\n"
            f"命中关键词：{'、'.join(matched_keywords) if matched_keywords else '无'}\n"
            f"建议追问点：{'；'.join(follow_up_questions) if follow_up_questions else '无'}\n"
            f"用户二次解释：{user_reply.strip()}"
        )
        content = self._call_openai_compatible_sync(prompt)
        parsed = self._parse_secondary_json(content)
        return (
            parsed["secondary_decision"],
            float(parsed["final_risk_after_secondary"]),
            list(parsed["reasons"]),
            parsed["assistant_message"],
        )

    async def _live_chat_response(self, latest_message: str) -> ChatResponse:
        if not settings.llm_api_key:
            raise ValueError(
                "在线模型未配置：请设置 LLM_API_KEY 或 ARK_API_KEY。"
            )
        if not settings.llm_model:
            raise ValueError("在线模型未配置：请设置 LLM_MODEL 或 ARK_MODEL。")

        prompt = self._build_live_prompt(latest_message)
        content = await self._try_live_langchain_response(prompt)
        if content is None:
            content = await self._call_openai_compatible_chat(prompt)

        return ChatResponse(
            assistant_message=content,
            used_tools=[
                ToolUsage(
                    name="ark_chat",
                    summary=f"调用在线模型 {settings.llm_model} 生成回复",
                )
            ],
            suggested_actions=[
                SuggestedAction(label="返回首页", action="refresh_dashboard")
            ],
        )

    def _build_live_prompt(self, latest_message: str) -> str:
        dashboard = self.bank_host.get_dashboard()
        bill_summary = self.bank_host.build_bill_summary()
        risk_summary = self.bank_host.explain_last_risk_event()
        return (
            "你是银行 App 内的演示版智能助手。请基于已知上下文，简洁、专业地回答用户。\n"
            f"账户余额：活期 {dashboard.cash_balance:.2f} 元，理财 {dashboard.wealth_balance:.2f} 元。\n"
            f"账单摘要：{bill_summary}\n"
            f"最近风控：{risk_summary}\n"
            f"用户问题：{latest_message}"
        )

    async def _try_live_langchain_response(self, prompt: str) -> str | None:
        try:
            from langchain_openai import ChatOpenAI
        except Exception:
            return None

        try:
            client = ChatOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model=settings.llm_model,
                temperature=0.2,
            )
            result = await client.ainvoke(prompt)
        except Exception:
            return None

        content = str(getattr(result, "content", "")).strip()
        return content or None

    async def _call_openai_compatible_chat(self, prompt: str) -> str:
        endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        if settings.llm_api_name:
            headers["X-Api-Name"] = settings.llm_api_name

        model_candidates = [settings.llm_model]
        if settings.llm_api_name and settings.llm_api_name not in model_candidates:
            model_candidates.append(settings.llm_api_name)

        last_error = "方舟接口调用失败。"
        for model_name in model_candidates:
            payload = {
                "model": model_name,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是银行 App 内的演示版智能助手，请准确回答并给出简洁建议。",
                    },
                    {"role": "user", "content": prompt},
                ],
            }
            if settings.llm_api_name:
                payload["user"] = settings.llm_api_name

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(endpoint, headers=headers, json=payload)
            except Exception as error:
                raise ValueError(
                    "方舟在线模型调用失败，请检查网络或 LLM_BASE_URL。"
                ) from error

            if response.status_code == 401:
                raise ValueError("方舟鉴权失败：API Key 无效或已过期。")

            if response.status_code >= 400:
                last_error = f"方舟接口调用失败（HTTP {response.status_code}，model={model_name}）。"
                continue

            body = response.json()
            content = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if content:
                return content
            last_error = f"方舟返回为空（model={model_name}）。"

        raise ValueError(
            f"{last_error} 请参考豆包 API 文档检查 model 是否为有效接入点（Endpoint）或可用模型名。"
        )

    def _call_openai_compatible_sync(self, prompt: str) -> str:
        endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        if settings.llm_api_name:
            headers["X-Api-Name"] = settings.llm_api_name

        payload = {
            "model": settings.llm_model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": "你是银行风控决策模型，请严格按 JSON 输出。",
                },
                {"role": "user", "content": prompt},
            ],
        }
        if settings.llm_api_name:
            payload["user"] = settings.llm_api_name

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(endpoint, headers=headers, json=payload)
        except Exception as error:
            raise ValueError("在线模型调用失败，请检查网络或 LLM_BASE_URL。") from error

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
            raise ValueError("在线模型返回为空，无法完成二次校验。")
        return content

    def _parse_secondary_json(self, content: str) -> dict:
        raw = content.strip()
        if not raw:
            raise ValueError("二次校验返回为空。")

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("二次校验返回格式异常，未找到 JSON。")

        snippet = raw[start : end + 1]
        try:
            payload = json.loads(snippet)
        except json.JSONDecodeError as error:
            raise ValueError("二次校验返回格式异常，JSON 解析失败。") from error

        decision = str(payload.get("secondary_decision", "")).strip()
        if decision not in {"pass_secondary", "block_secondary"}:
            raise ValueError("二次校验返回缺少有效 secondary_decision。")

        try:
            risk = float(payload.get("final_risk_after_secondary", 1.0))
        except (TypeError, ValueError) as error:
            raise ValueError("二次校验返回的风险分值无效。") from error

        reasons_raw = payload.get("reasons", [])
        reasons = [str(item).strip() for item in reasons_raw if str(item).strip()]
        if not reasons:
            reasons = ["模型未返回详细原因。"]

        assistant_message = str(payload.get("assistant_message", "")).strip()
        if not assistant_message:
            assistant_message = "二次校验已完成。"

        return {
            "secondary_decision": decision,
            "final_risk_after_secondary": max(0.0, min(1.0, risk)),
            "reasons": reasons,
            "assistant_message": assistant_message,
        }


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    return AgentService()
