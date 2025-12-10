"""Auto Tag - メイン処理"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_wrapper import LLMWrapper
from utils.whisper_wrapper import WhisperWrapper
from .prompts import ANALYZE_SYSTEM, TAG_PROMPT, GENRE_PROMPTS


class AutoTag:
    """タグ・説明文自動生成クラス"""

    def __init__(
        self,
        llm: LLMWrapper = None,
        whisper: WhisperWrapper = None,
        whisper_model: str = "base",
    ):
        """
        初期化

        Args:
            llm: LLMWrapperインスタンス
            whisper: WhisperWrapperインスタンス
            whisper_model: Whisperモデル名
        """
        self.llm = llm or LLMWrapper()
        self.whisper = whisper or WhisperWrapper(model=whisper_model)

    def generate(
        self,
        video_file: str,
        output_file: str = None,
        genre: str = "default",
        language: str = "ja",
    ) -> dict:
        """
        タグ・説明文を生成

        Args:
            video_file: 入力動画ファイル
            output_file: 出力JSONファイル（省略時は自動生成）
            genre: 動画ジャンル
            language: 言語コード

        Returns:
            生成結果 {"titles": [...], "tags": [...], "description": "...", "summary": "..."}
        """
        video_path = Path(video_file)
        if not video_path.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {video_file}")

        # 出力ファイル名
        if output_file is None:
            output_file = str(video_path.with_suffix(".tags.json"))

        # 1. Whisperで文字起こし
        print(f"[1/2] 音声認識中: {video_path.name}")
        transcript = self.whisper.transcribe_to_text(
            video_file,
            language=language,
            with_timestamps=True,
        )

        if not transcript.strip():
            raise ValueError("文字起こし結果が空です")

        # 文字起こしが長すぎる場合は切り詰め（トークン制限対策）
        max_chars = 15000
        if len(transcript) > max_chars:
            print(f"    文字起こしが長いため切り詰め（{len(transcript)} → {max_chars}文字）")
            transcript = transcript[:max_chars] + "\n...(以下省略)"

        # 2. LLMでメタデータ生成
        print("[2/2] メタデータ生成中")
        genre_desc = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["default"])
        prompt = TAG_PROMPT.format(genre=genre_desc, transcript=transcript)

        try:
            result = self.llm.generate_json(prompt, system=ANALYZE_SYSTEM)
        except Exception as e:
            raise ValueError(f"メタデータ生成失敗: {e}")

        # 結果を検証・補完
        result = self._validate_result(result)

        # JSON出力
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"[完了] {output_file}")
        return result

    def _validate_result(self, result: dict) -> dict:
        """結果を検証・補完"""
        # 必須フィールドの確認
        if "titles" not in result or not result["titles"]:
            result["titles"] = ["タイトル生成失敗"]

        if "tags" not in result or not result["tags"]:
            result["tags"] = []

        if "description" not in result:
            result["description"] = ""

        if "summary" not in result:
            result["summary"] = ""

        # タイトルは最大5個
        result["titles"] = result["titles"][:5]

        # タグは最大30個
        result["tags"] = result["tags"][:30]

        return result

    def print_result(self, result: dict) -> None:
        """結果を見やすく表示"""
        print("\n" + "=" * 50)
        print("【タイトル案】")
        for i, title in enumerate(result.get("titles", []), 1):
            print(f"  {i}. {title}")

        print("\n【タグ】")
        tags = result.get("tags", [])
        # 5個ずつ改行
        for i in range(0, len(tags), 5):
            chunk = tags[i:i+5]
            print("  " + ", ".join(chunk))

        print("\n【説明文】")
        desc = result.get("description", "")
        # 長い場合は先頭だけ表示
        if len(desc) > 300:
            print(f"  {desc[:300]}...")
        else:
            print(f"  {desc}")

        print("\n【要約】")
        print(f"  {result.get('summary', '')}")
        print("=" * 50)
