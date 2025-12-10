"""FFmpeg Wrapper - FFmpegコマンド実行"""

import subprocess
import json
import shlex
from pathlib import Path


class FFmpegWrapper:
    """FFmpegのラッパークラス"""

    @staticmethod
    def run(command: str) -> tuple[bool, str]:
        """
        FFmpegコマンドを実行

        Args:
            command: 実行するFFmpegコマンド（文字列）

        Returns:
            (成功フラグ, 出力/エラーメッセージ)
        """
        try:
            # コマンドをパース
            if command.startswith("ffmpeg "):
                args = shlex.split(command)
            else:
                args = shlex.split(f"ffmpeg {command}")

            # -y オプション追加（上書き確認スキップ）
            if "-y" not in args:
                args.insert(1, "-y")

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=600,  # 10分タイムアウト
            )

            if result.returncode == 0:
                return True, result.stderr  # FFmpegは進捗をstderrに出力
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Timeout: command took longer than 10 minutes"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_file_info(filepath: str) -> dict:
        """
        ffprobeで動画ファイル情報を取得

        Args:
            filepath: 動画ファイルパス

        Returns:
            ファイル情報（duration, width, height等）
        """
        if not Path(filepath).exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            filepath,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)

        # 必要な情報を抽出
        info = {
            "filepath": filepath,
            "duration": float(data.get("format", {}).get("duration", 0)),
            "size": int(data.get("format", {}).get("size", 0)),
            "bit_rate": int(data.get("format", {}).get("bit_rate", 0)),
        }

        # ビデオストリーム情報
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["width"] = stream.get("width")
                info["height"] = stream.get("height")
                info["codec"] = stream.get("codec_name")
                info["fps"] = eval(stream.get("r_frame_rate", "0/1"))
                break

        # オーディオストリーム情報
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                info["audio_codec"] = stream.get("codec_name")
                info["sample_rate"] = int(stream.get("sample_rate", 0))
                break

        return info

    @staticmethod
    def cut(
        input_file: str,
        output_file: str,
        start: str,
        end: str,
        reencode: bool = False,
    ) -> bool:
        """
        動画をカット

        Args:
            input_file: 入力ファイル
            output_file: 出力ファイル
            start: 開始時刻（HH:MM:SS or 秒数）
            end: 終了時刻（HH:MM:SS or 秒数）
            reencode: 再エンコードするか（精度向上、時間増）

        Returns:
            成功フラグ
        """
        if reencode:
            # 再エンコード（精度高、遅い）
            cmd = f'-ss {start} -to {end} -i "{input_file}" -c:v libx264 -c:a aac "{output_file}"'
        else:
            # コピー（高速、キーフレーム依存）
            cmd = f'-ss {start} -to {end} -i "{input_file}" -c copy "{output_file}"'

        success, _ = FFmpegWrapper.run(cmd)
        return success

    @staticmethod
    def format_info(info: dict) -> str:
        """
        ファイル情報を人間可読形式に整形

        Args:
            info: get_file_info()の戻り値

        Returns:
            整形された文字列
        """
        duration_min = info.get("duration", 0) / 60
        size_mb = info.get("size", 0) / (1024 * 1024)

        lines = [
            f"Duration: {duration_min:.1f} min ({info.get('duration', 0):.1f} sec)",
            f"Resolution: {info.get('width', '?')}x{info.get('height', '?')}",
            f"Video Codec: {info.get('codec', '?')}",
            f"Audio Codec: {info.get('audio_codec', '?')}",
            f"Size: {size_mb:.1f} MB",
        ]
        return "\n".join(lines)
