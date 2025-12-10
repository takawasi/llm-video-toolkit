"""Auto Caption - LLM校正処理"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_wrapper import LLMWrapper
from .prompts import CORRECTION_SYSTEM, CORRECTION_PROMPT


class Corrector:
    """Whisper出力をLLMで校正するクラス"""

    def __init__(self, llm: LLMWrapper = None):
        """
        初期化

        Args:
            llm: LLMWrapperインスタンス（省略時は自動生成）
        """
        self.llm = llm or LLMWrapper()

    def correct(self, segments: list[dict]) -> list[dict]:
        """
        セグメントリストを校正

        Args:
            segments: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]

        Returns:
            校正済みセグメントリスト
        """
        # セグメントが多すぎる場合は分割処理
        if len(segments) > 50:
            return self._correct_chunked(segments, chunk_size=50)

        # JSON形式で渡す
        segments_json = json.dumps(segments, ensure_ascii=False, indent=2)
        prompt = CORRECTION_PROMPT.format(segments=segments_json)

        try:
            corrected = self.llm.generate_json(prompt, system=CORRECTION_SYSTEM)
            return corrected
        except Exception as e:
            # 校正失敗時は元のセグメントを返す
            print(f"警告: LLM校正失敗 ({e})。元のテキストを使用します。")
            return segments

    def _correct_chunked(self, segments: list[dict], chunk_size: int = 50) -> list[dict]:
        """
        長いセグメントリストを分割して校正

        Args:
            segments: 全セグメント
            chunk_size: 1回のAPI呼び出しで処理するセグメント数

        Returns:
            校正済み全セグメント
        """
        corrected_all = []

        for i in range(0, len(segments), chunk_size):
            chunk = segments[i:i + chunk_size]
            corrected_chunk = self.correct(chunk)
            corrected_all.extend(corrected_chunk)

        return corrected_all
