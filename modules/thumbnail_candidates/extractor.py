"""Thumbnail Candidates - メイン処理"""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_wrapper import LLMWrapper
from utils.whisper_wrapper import WhisperWrapper
from .prompts import (
    COPYWRITE_SYSTEM, COPYWRITE_PROMPT,
    SCENE_ANALYZE_SYSTEM, SCENE_ANALYZE_PROMPT,
)


class ThumbnailCandidates:
    """サムネ素材出しクラス"""

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

    def extract(
        self,
        video_file: str,
        output_dir: str = None,
        num_frames: int = 5,
        language: str = "ja",
        tone: str = "default",
    ) -> list[dict]:
        """
        サムネ候補を抽出

        Args:
            video_file: 入力動画ファイル
            output_dir: 出力ディレクトリ（省略時は./thumbnails）
            num_frames: 抽出するフレーム数
            language: 言語コード
            tone: キャッチコピーのトーン（funny/serious/clickbait/default）

        Returns:
            結果リスト [{"timestamp": "01:32", "frame": "path", "copies": [...], ...}, ...]
        """
        video_path = Path(video_file)
        if not video_path.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {video_file}")

        # 出力ディレクトリ
        if output_dir is None:
            output_dir = "./thumbnails"
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 1. Whisperで文字起こし
        print(f"[1/4] 音声認識中: {video_path.name}")
        transcript = self.whisper.transcribe_to_text(
            video_file,
            language=language,
            with_timestamps=True,
        )

        if not transcript.strip():
            raise ValueError("文字起こし結果が空です")

        # 切り詰め
        max_chars = 15000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "\n...(以下省略)"

        # 2. LLMでサムネ向きシーンを分析
        print(f"[2/4] シーン分析中（{num_frames}箇所）")
        scenes = self._analyze_scenes(transcript, num_frames)

        if not scenes:
            raise ValueError("サムネ向きシーンが見つかりませんでした")

        # 3. フレームを抽出
        print(f"[3/4] フレーム抽出中")
        results = []
        for i, scene in enumerate(scenes):
            frame_path = output_path / f"frame_{i+1:02d}_{scene['timestamp'].replace(':', '_')}.jpg"

            success = self._extract_frame(
                video_file,
                scene["start"],
                str(frame_path),
            )

            results.append({
                "timestamp": scene["timestamp"],
                "start": scene["start"],
                "scene": scene["scene"],
                "reason": scene.get("reason", ""),
                "frame": str(frame_path) if success else None,
                "copies": [],
            })

        # 4. キャッチコピー生成
        print("[4/4] キャッチコピー生成中")
        results = self._generate_copies(results, transcript[:3000], tone)

        # captions.txt出力
        self._write_captions_file(results, output_path / "captions.txt")

        print(f"[完了] {output_path}")
        return results

    def _analyze_scenes(self, transcript: str, num_scenes: int) -> list[dict]:
        """サムネ向きシーンを分析"""
        prompt = SCENE_ANALYZE_PROMPT.format(
            transcript=transcript,
            num_scenes=num_scenes,
        )

        try:
            scenes = self.llm.generate_json(prompt, system=SCENE_ANALYZE_SYSTEM)
            return scenes[:num_scenes]
        except Exception as e:
            print(f"警告: シーン分析失敗 ({e})")
            return []

    def _extract_frame(self, video_file: str, timestamp: float, output_file: str) -> bool:
        """FFmpegでフレーム抽出"""
        cmd = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_file,
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            output_file,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _generate_copies(self, results: list[dict], summary: str, tone: str) -> list[dict]:
        """キャッチコピーを生成"""
        # シーン情報をまとめる
        scenes_text = ""
        for r in results:
            scenes_text += f"- {r['timestamp']}: {r['scene']}\n"

        prompt = COPYWRITE_PROMPT.format(
            summary=summary,
            scenes=scenes_text,
        )

        # トーン指定
        tone_hint = {
            "funny": "ユーモア・笑いを誘うコピーを優先",
            "serious": "真面目・信頼感のあるコピーを優先",
            "clickbait": "クリック欲を煽る強めのコピーを優先",
            "default": "",
        }.get(tone, "")

        if tone_hint:
            prompt += f"\n\n【トーン指定】\n{tone_hint}"

        try:
            copies_data = self.llm.generate_json(prompt, system=COPYWRITE_SYSTEM)

            # 結果にマージ
            for copy_item in copies_data:
                ts = copy_item.get("timestamp", "")
                for r in results:
                    if r["timestamp"] == ts:
                        r["copies"] = copy_item.get("copies", [])
                        break

        except Exception as e:
            print(f"警告: キャッチコピー生成失敗 ({e})")

        return results

    def _write_captions_file(self, results: list[dict], output_file: Path) -> None:
        """captions.txt出力"""
        lines = ["# サムネ用キャッチコピー案\n"]

        for r in results:
            lines.append(f"## {r['frame'] or 'frame_N/A'} ({r['timestamp']})")
            lines.append(f"シーン: {r['scene']}")
            if r.get("reason"):
                lines.append(f"理由: {r['reason']}")
            lines.append("コピー案:")
            for i, copy in enumerate(r.get("copies", []), 1):
                lines.append(f"  {i}. 「{copy}」")
            lines.append("")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def print_result(self, results: list[dict]) -> None:
        """結果を見やすく表示"""
        print("\n" + "=" * 50)
        for r in results:
            status = "✓" if r.get("frame") else "✗"
            print(f"[{status}] {r['timestamp']} - {r['scene']}")
            if r.get("copies"):
                for copy in r["copies"]:
                    print(f"    → 「{copy}」")
            print()
        print("=" * 50)
