"""Clip Cutter - メインロジック"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_wrapper import LLMWrapper
from utils.whisper_wrapper import WhisperWrapper
from utils.ffmpeg_wrapper import FFmpegWrapper
from .transcriber import Transcriber
from .analyzer import ClipAnalyzer


class ClipCutter:
    """動画からバズりそうな箇所を自動切り出し"""

    def __init__(
        self,
        llm: LLMWrapper = None,
        whisper: WhisperWrapper = None,
    ):
        """
        初期化

        Args:
            llm: LLMWrapperインスタンス
            whisper: WhisperWrapperインスタンス
        """
        self.llm = llm or LLMWrapper()
        self.whisper = whisper
        self.transcriber = Transcriber(whisper=whisper)
        self.analyzer = ClipAnalyzer(llm=self.llm)
        self.ffmpeg = FFmpegWrapper()

    def cut_clips(
        self,
        input_file: str,
        output_dir: str = None,
        num_clips: int = 5,
        min_duration: int = 15,
        max_duration: int = 60,
        language: str = "ja",
    ) -> list[dict]:
        """
        動画からバズりそうな箇所を自動切り出し

        Args:
            input_file: 入力動画ファイル
            output_dir: 出力ディレクトリ（省略時は入力ファイルと同じ場所にclips/を作成）
            num_clips: 切り出すクリップ数
            min_duration: 最小秒数
            max_duration: 最大秒数
            language: 言語コード

        Returns:
            切り出し結果リスト [{"file": "clip_001.mp4", "start": "...", "end": "...", "reason": "..."}, ...]
        """
        input_path = Path(input_file)

        # 出力ディレクトリ設定
        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = input_path.parent / "clips"
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. 文字起こし
        print("文字起こし中...")
        transcript = self.transcriber.transcribe(input_file, language=language)
        print(f"  {len(transcript)}セグメント取得")

        # 2. バズ箇所分析
        print("バズ箇所分析中...")
        clips_info = self.analyzer.analyze(
            transcript,
            num_clips=num_clips,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        print(f"  {len(clips_info)}箇所特定")

        # 3. クリップ切り出し
        print("クリップ切り出し中...")
        results = []
        for i, clip in enumerate(clips_info):
            output_file = out_dir / f"clip_{i+1:03d}.mp4"

            success = self.ffmpeg.cut(
                input_file=str(input_path),
                output_file=str(output_file),
                start=clip["start"],
                end=clip["end"],
            )

            result = {
                "file": str(output_file),
                "start": clip["start"],
                "end": clip["end"],
                "reason": clip.get("reason", ""),
                "success": success,
            }
            results.append(result)

            status = "OK" if success else "FAILED"
            print(f"  [{status}] {output_file.name}: {clip['start']} - {clip['end']}")

        # 4. メタデータ出力
        self._save_metadata(results, out_dir / "metadata.json")

        return results

    def _save_metadata(self, results: list[dict], output_file: Path):
        """メタデータをJSONで保存"""
        import json

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"メタデータ保存: {output_file}")


def main():
    """CLI用エントリポイント"""
    import argparse

    parser = argparse.ArgumentParser(description="Clip Cutter - 動画自動切り出し")
    parser.add_argument("-i", "--input", required=True, help="入力動画ファイル")
    parser.add_argument("-o", "--output-dir", help="出力ディレクトリ")
    parser.add_argument("-n", "--num-clips", type=int, default=5, help="切り出すクリップ数")
    parser.add_argument("--min-duration", type=int, default=15, help="最小秒数")
    parser.add_argument("--max-duration", type=int, default=60, help="最大秒数")
    parser.add_argument("--language", default="ja", help="言語コード")

    args = parser.parse_args()

    cutter = ClipCutter()
    results = cutter.cut_clips(
        args.input,
        output_dir=args.output_dir,
        num_clips=args.num_clips,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        language=args.language,
    )

    print(f"\n完了: {len([r for r in results if r['success']])} / {len(results)} クリップ")


if __name__ == "__main__":
    main()
