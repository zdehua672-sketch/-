"""
LLM Bridge — 大模型API统一接入层

支持 OpenAI 兼容接口（包括 Azure OpenAI、本地 ollama 等）和 Anthropic Claude。
通过环境变量或配置文件切换后端，所有写作/审稿代理通过此模块调用 LLM。

用法:
    from llm_bridge import LLMClient

    client = LLMClient(model="gpt-4o")  # 或 claude-sonnet-4-20250514
    response = client.chat([
        {"role": "system", "content": "你是一个审稿专家。"},
        {"role": "user", "content": "请检查这篇论文..."},
    ])
    print(response)
"""

import os
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """
    大模型客户端 — 统一调用接口

    支持后端:
      - openai: OpenAI / Azure OpenAI / 任何兼容接口 (ollama, vllm...)
      - anthropic: Claude API

    配置方式（优先级：函数参数 > 环境变量 > 默认值）:
      环境变量              | 说明
      ---------------------|-------------------------------
      LLM_BACKEND          | openai / anthropic
      LLM_API_KEY          | API密钥
      LLM_API_BASE         | API基础URL
      LLM_MODEL            | 模型名
      LLM_MAX_TOKENS       | 最大生成token数 (默认4096)
      LLM_TEMPERATURE      | 温度 (默认0.7)
    """

    def __init__(
        self,
        backend: str = None,
        api_key: str = None,
        api_base: str = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        self.backend = backend or os.environ.get("LLM_BACKEND", "openai")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.api_base = api_base or os.environ.get("LLM_API_BASE", "")
        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o")
        self.max_tokens = max_tokens or int(os.environ.get("LLM_MAX_TOKENS", "4096"))
        self.temperature = temperature or float(os.environ.get("LLM_TEMPERATURE", "0.7"))

        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化底层客户端"""
        if self.backend == "anthropic":
            self._init_anthropic()
        else:
            self._init_openai()

    def _init_openai(self):
        """初始化 OpenAI 兼容客户端"""
        try:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key or "sk-placeholder"}
            if self.api_base:
                kwargs["base_url"] = self.api_base
            self._client = OpenAI(**kwargs)
            logger.info(f"OpenAI client initialized: model={self.model}, base={self.api_base or 'default'}")
        except ImportError:
            logger.warning("openai 包未安装。运行: pip install openai")
            self._client = None

    def _init_anthropic(self):
        """初始化 Anthropic Claude 客户端"""
        try:
            import anthropic
            kwargs = {"api_key": self.api_key}
            self._client = anthropic.Anthropic(**kwargs)
            logger.info(f"Anthropic client initialized: model={self.model}")
        except ImportError:
            logger.warning("anthropic 包未安装。运行: pip install anthropic")
            self._client = None

    @property
    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        return self._client is not None and bool(self.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """
        发送聊天请求

        Parameters
        ----------
        messages : list of dict
            [{"role": "user", "content": "..."}, ...]
        system : str, optional
            系统提示（部分后端需要独立字段）
        max_tokens : int, optional
            最大生成token数
        temperature : float, optional
            温度参数

        Returns
        -------
        str: 模型回复
        """
        if not self.is_available:
            return self._fallback_response(messages, system)

        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            if self.backend == "anthropic":
                return self._chat_anthropic(messages, system, max_tokens, temperature)
            return self._chat_openai(messages, system, max_tokens, temperature)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._fallback_response(messages, system)

    def _chat_openai(self, messages, system, max_tokens, temperature):
        """调用 OpenAI 兼容接口"""
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(messages)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def _chat_anthropic(self, messages, system, max_tokens, temperature):
        """调用 Anthropic Claude 接口"""
        api_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            api_kwargs["system"] = system

        response = self._client.messages.create(**api_kwargs)
        return response.content[0].text

    def _fallback_response(self, messages: List[Dict], system: str = None) -> str:
        """
        LLM不可用时的降级回复

        返回一个模板说明，提示用户配置API密钥
        """
        # 尝试用规则提取最后一个用户消息的关键信息
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        logger.warning("LLM not available - using fallback template")

        # 检测请求类型并返回相应模板
        if last_user_msg and ("审稿" in last_user_msg or "review" in last_user_msg.lower()):
            return (
                "【LLM 未配置】请配置 API 密钥以启用 AI 审稿。\n\n"
                "配置方法：\n"
                "  export LLM_API_KEY='your-api-key'\n"
                "  export LLM_MODEL='gpt-4o'  # 或 claude-sonnet-4-20250514\n\n"
                "或使用 .env 文件：\n"
                "  LLM_BACKEND=openai\n"
                "  LLM_API_KEY=sk-...\n"
                "  LLM_MODEL=gpt-4o\n"
            )
        if last_user_msg and ("写" in last_user_msg or "生成" in last_user_msg or "write" in last_user_msg.lower()):
            return (
                "【LLM 未配置】请配置 API 密钥以启用 AI 论文写作。\n\n"
                "当前系统使用规则模板生成内容，需要 LLM 支持才能生成完整论文。\n"
                "配置方法同上。"
            )
        return (
            "【LLM 未配置】\n"
            "请通过环境变量配置 API 密钥以启用 AI 功能：\n"
            f"  export LLM_API_KEY='your-key' (当前: {'已设置' if self.api_key else '未设置'})\n"
            f"  export LLM_BACKEND='openai' (当前: {self.backend})\n"
            f"  export LLM_MODEL='gpt-4o' (当前: {self.model})\n"
        )

    def generate_text(
        self,
        prompt: str,
        system: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """单轮文本生成快捷方法"""
        return self.chat(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def review_paper(self, paper_text: str, language: str = "zh") -> str:
        """审稿专用方法"""
        system_prompt = (
            "你是一位严谨的学术论文审稿专家。请检查论文的科学性、逻辑性、"
            "语言表达和格式规范。给出具体的修改建议和评分（0-10）。"
            if language == "zh"
            else "You are a rigorous academic paper reviewer. Check scientific validity, "
            "logical flow, language quality and formatting. Provide specific revision "
            "suggestions and scores (0-10)."
        )
        user_prompt = (
            f"请审阅以下{'中文' if language == 'zh' else ''}学术论文，"
            f"指出所有问题并按严重程度分类（CRITICAL/MAJOR/MINOR），"
            f"给出改进建议和综合评分：\n\n{paper_text[:8000]}"
        )
        return self.generate_text(user_prompt, system=system_prompt)

    def write_section(
        self,
        section_name: str,
        motivation: str,
        data_summary: str = "",
        context: str = "",
        language: str = "zh",
    ) -> str:
        """论文写作专用方法"""
        system_prompt = (
            "你是一位经验丰富的学术论文作者。请根据给定的动机、数据和分析结果，"
            "撰写论文某个章节。要求逻辑清晰、表达准确、引用规范。"
            if language == "zh"
            else "You are an experienced academic paper author. Write a paper section "
            "based on the given motivation, data and analysis. Be logical, precise and well-referenced."
        )
        user_prompt = (
            f"请撰写论文的「{section_name}」章节。\n\n"
            f"研究动机：{motivation}\n\n"
            f"{'数据摘要：' + data_summary + chr(10)*2 if data_summary else ''}"
            f"{'上下文：' + context + chr(10)*2 if context else ''}"
            f"语言：{'中文' if language == 'zh' else 'English'}"
        )
        return self.generate_text(user_prompt, system=system_prompt)