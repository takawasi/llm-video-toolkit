"""Clip Cutter - LLMによるバズ箇所分析"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_wrapper import LLMWrapper


ANALYSIS_SYSTEM_PROMPT = """あなたは動画コンテンツの分析エキスパートです。
与えられた文字起こしから、SNSでバズりそうな箇所を特定してください。

出力は必ずJSON配列のみ。説明や前置きは不要。"""

ANALYSIS_USER_PROMPT = """以下は動画の文字起こしです。
SNSでシェアされやすい「バズりそうな発言」を{num_clips}箇所特定してください。

【判定基準】
- 逆張り・意外な主張
- 強い言い切り
- 面白い言い回し
- 感情的なピーク
- 議論を呼びそうな内容
- キャッチーなフレーズ

【出力形式】
JSON配列で出力（他の文字は不要）:
[
  {{"start": "00:01:30", "end": "00:02:15", "reason": "理由を短く"}},
  ...
]

【注意】
- start/endはHH:MM:SS形式
- 各クリップは{min_duration}秒以上{max_duration}秒以下になるよう調整
- reasonは20文字以内

【文字起こし】
{transcript}"""


class ClipAnalyzer:
    """LLMを使ってバズりそうな箇所を分析"""

    def __init__(self, llm: LLMWrapper = None):
        """
        初期化

        Args:
            llm: LLMWrapperインスタンス（省略時は自動生成）
        """
        self.llm = llm or LLMWrapper()

    def analyze(
        self,
        transcript: list[dict],
        num_clips: int = 5,
        min_duration: int = 15,
        max_duration: int = 60,
    ) -> list[dict]:
        """
        文字起こしからバズりそうな箇所を特定

        Args:
            transcript: 文字起こしセグメントリスト
            num_clips: 切り出すクリップ数
            min_duration: 最小秒数
            max_duration: 最大秒数

        Returns:
            クリップ情報リスト [{"start": "00:01:30", "end": "00:02:15", "reason": "..."}, ...]
        """
        # 文字起こしをテキスト化
        transcript_text = self._format_transcript(transcript)

        # プロンプト生成
        prompt = ANALYSIS_USER_PROMPT.format(
            num_clips=num_clips,
            min_duration=min_duration,
            max_duration=max_duration,
            transcript=transcript_text,
        )

        # LLMで分析
        result = self.llm.generate_json(prompt, ANALYSIS_SYSTEM_PROMPT)

        # リストでない場合の対応
        if isinstance(result, dict) and "clips" in result:
            result = result["clips"]

        return result

    def _format_transcript(self, transcript: list[dict]) -> str:
        """文字起こしをテキスト形式に変換"""
        lines = []
        for seg in transcript:
            ts = self._format_timestamp(seg["start"])
            lines.append(f"[{ts}] {seg['text']}")
        return "\n".join(lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """秒数をHH:MM:SS形式に変換"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
