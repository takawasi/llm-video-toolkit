"""Clip Cutter - Whisper連携（文字起こし）"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.whisper_wrapper import WhisperWrapper


class Transcriber:
    """動画の文字起こしを行うクラス"""

    def __init__(self, whisper: WhisperWrapper = None, model: str = "base"):
        """
        初期化

        Args:
            whisper: WhisperWrapperインスタンス（省略時は自動生成）
            model: Whisperモデル名
        """
        self.whisper = whisper or WhisperWrapper(model=model)

    def transcribe(
        self,
        video_file: str,
        language: str = "ja",
    ) -> list[dict]:
        """
        動画を文字起こし

        Args:
            video_file: 動画ファイルパス
            language: 言語コード

        Returns:
            セグメントリスト [{"start": 0.0, "end": 2.5, "text": "..."}, ...]
        """
        return self.whisper.transcribe(video_file, language=language)

    def transcribe_formatted(
        self,
        video_file: str,
        language: str = "ja",
    ) -> str:
        """
        文字起こし結果をフォーマット済みテキストで取得

        Args:
            video_file: 動画ファイルパス
            language: 言語コード

        Returns:
            タイムスタンプ付きテキスト
        """
        segments = self.transcribe(video_file, language)

        lines = []
        for seg in segments:
            ts_start = self._format_timestamp(seg["start"])
            ts_end = self._format_timestamp(seg["end"])
            lines.append(f"[{ts_start} - {ts_end}] {seg['text']}")

        return "\n".join(lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """秒数をHH:MM:SS形式に変換"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
