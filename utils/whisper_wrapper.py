"""Whisper Wrapper - 音声認識"""

import whisper


class WhisperWrapper:
    """Whisperのラッパークラス"""

    def __init__(self, model: str = "base", device: str = None):
        """
        初期化

        Args:
            model: Whisperモデル名（tiny, base, small, medium, large）
            device: 使用デバイス（cuda, cpu）。Noneで自動選択
        """
        self.model_name = model
        self.model = whisper.load_model(model, device=device)

    def transcribe(
        self,
        audio_file: str,
        language: str = "ja",
        word_timestamps: bool = False,
    ) -> list[dict]:
        """
        音声を文字起こし

        Args:
            audio_file: 音声/動画ファイルパス
            language: 言語コード
            word_timestamps: 単語レベルのタイムスタンプを取得するか

        Returns:
            セグメントリスト [{"start": 0.0, "end": 2.5, "text": "..."}, ...]
        """
        result = self.model.transcribe(
            audio_file,
            language=language,
            word_timestamps=word_timestamps,
        )

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            })

        return segments

    def transcribe_to_text(
        self,
        audio_file: str,
        language: str = "ja",
        with_timestamps: bool = True,
    ) -> str:
        """
        文字起こし結果をテキストで取得

        Args:
            audio_file: 音声/動画ファイルパス
            language: 言語コード
            with_timestamps: タイムスタンプを含めるか

        Returns:
            文字起こしテキスト
        """
        segments = self.transcribe(audio_file, language)

        if with_timestamps:
            lines = []
            for seg in segments:
                ts = self._format_timestamp(seg["start"])
                lines.append(f"[{ts}] {seg['text']}")
            return "\n".join(lines)
        else:
            return " ".join(seg["text"] for seg in segments)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """秒数をHH:MM:SS形式に変換"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
