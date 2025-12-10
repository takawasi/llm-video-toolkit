"""LLM Wrapper - Claude API連携"""

import os
import json
import re
from anthropic import Anthropic


class LLMWrapper:
    """Claude APIのラッパークラス"""

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-20250514"):
        """
        初期化

        Args:
            api_key: Anthropic API Key（省略時は環境変数ANTHROPIC_API_KEY）
            model: 使用するモデル
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")
        self.model = model
        self.client = Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, system: str = None) -> str:
        """
        プロンプトを送信してレスポンスを取得

        Args:
            prompt: ユーザープロンプト
            system: システムプロンプト

        Returns:
            レスポンステキスト
        """
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def generate_json(self, prompt: str, system: str = None) -> dict:
        """
        JSON形式でレスポンスを取得

        Args:
            prompt: ユーザープロンプト
            system: システムプロンプト

        Returns:
            パースされたJSON
        """
        # JSONを返すよう指示を追加
        json_system = (system or "") + "\n\n出力は有効なJSONのみ。他の文字は不要。"

        response_text = self.generate(prompt, json_system)

        # JSONを抽出（```json ... ``` 形式にも対応）
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
        if json_match:
            response_text = json_match.group(1)

        # 配列またはオブジェクトを検出
        array_match = re.search(r"\[[\s\S]*\]", response_text)
        object_match = re.search(r"\{[\s\S]*\}", response_text)

        if array_match:
            return json.loads(array_match.group())
        elif object_match:
            return json.loads(object_match.group())
        else:
            raise ValueError(f"Failed to parse JSON from response: {response_text[:200]}")
