"""Auto Caption - メイン処理"""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_wrapper import LLMWrapper
from utils.whisper_wrapper import WhisperWrapper
from .corrector import Corrector
from .srt_writer import write_srt


class AutoCaption:
    """字幕自動生成クラス"""

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
        self.corrector = Corrector(llm=self.llm)

    def generate(
        self,
        video_file: str,
        output_file: str = None,
        language: str = "ja",
        correct: bool = True,
    ) -> tuple[list[dict], str]:
        """
        字幕を生成

        Args:
            video_file: 入力動画ファイル
            output_file: 出力SRTファイル（省略時は自動生成）
            language: 言語コード
            correct: LLMによる校正を行うか

        Returns:
            (セグメントリスト, 出力ファイルパス)
        """
        video_path = Path(video_file)
        if not video_path.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {video_file}")

        # 出力ファイル名
        if output_file is None:
            output_file = str(video_path.with_suffix(".srt"))

        # 1. Whisperで文字起こし
        print(f"[1/3] 音声認識中: {video_path.name}")
        segments = self.whisper.transcribe(video_file, language=language)

        if not segments:
            raise ValueError("文字起こし結果が空です")

        # 2. LLMで校正（オプション）
        if correct:
            print(f"[2/3] 校正中（{len(segments)}セグメント）")
            segments = self.corrector.correct(segments)
        else:
            print("[2/3] 校正スキップ")

        # 3. SRT出力
        print(f"[3/3] SRT出力: {output_file}")
        write_srt(segments, output_file)

        return segments, output_file

    def generate_and_burn(
        self,
        video_file: str,
        output_file: str,
        language: str = "ja",
        correct: bool = True,
        style: str = None,
    ) -> bool:
        """
        字幕を生成して動画に焼き込み

        Args:
            video_file: 入力動画ファイル
            output_file: 出力動画ファイル
            language: 言語コード
            correct: LLMによる校正を行うか
            style: 字幕スタイル（FontSize, PrimaryColour等）

        Returns:
            成功したかどうか
        """
        video_path = Path(video_file)

        # まずSRTを生成
        srt_file = str(video_path.with_suffix(".srt"))
        segments, srt_file = self.generate(
            video_file,
            output_file=srt_file,
            language=language,
            correct=correct,
        )

        # FFmpegで焼き込み
        print(f"[+] 字幕焼き込み中: {output_file}")

        # スタイル設定
        if style:
            force_style = f":force_style='{style}'"
        else:
            # デフォルトスタイル（白文字、太字、下部配置）
            force_style = ":force_style='FontSize=24,PrimaryColour=&Hffffff,Bold=1,Alignment=2'"

        # FFmpegコマンド
        # 注: Windows対応のため、SRTパスのバックスラッシュをエスケープ
        srt_escaped = srt_file.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg",
            "-i", video_file,
            "-vf", f"subtitles={srt_escaped}{force_style}",
            "-c:a", "copy",
            "-y",  # 上書き
            output_file,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"[完了] {output_file}")
                return True
            else:
                print(f"[失敗] FFmpegエラー: {result.stderr}")
                return False

        except FileNotFoundError:
            print("[失敗] FFmpegが見つかりません")
            return False
