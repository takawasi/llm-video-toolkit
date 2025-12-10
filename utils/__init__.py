"""LLM Video Toolkit - 共通ユーティリティ"""

from .llm_wrapper import LLMWrapper
from .ffmpeg_wrapper import FFmpegWrapper

# WhisperWrapperは遅延ロード（whisperインストール不要でCLI動作可能に）
def __getattr__(name):
    if name == "WhisperWrapper":
        from .whisper_wrapper import WhisperWrapper
        return WhisperWrapper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["LLMWrapper", "FFmpegWrapper", "WhisperWrapper"]
