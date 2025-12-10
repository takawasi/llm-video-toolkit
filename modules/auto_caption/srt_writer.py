"""Auto Caption - SRTファイル出力"""

from pathlib import Path


def format_srt_timestamp(seconds: float) -> str:
    """秒数をSRT形式のタイムスタンプに変換

    Args:
        seconds: 秒数（小数点以下含む）

    Returns:
        SRT形式タイムスタンプ（HH:MM:SS,mmm）
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[dict], output_path: str) -> None:
    """セグメントリストをSRTファイルに出力

    Args:
        segments: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]
        output_path: 出力SRTファイルパス
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, seg in enumerate(segments, start=1):
        start_ts = format_srt_timestamp(seg["start"])
        end_ts = format_srt_timestamp(seg["end"])
        text = seg["text"]

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")  # 空行

    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def segments_to_srt_string(segments: list[dict]) -> str:
    """セグメントリストをSRT形式の文字列に変換

    Args:
        segments: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]

    Returns:
        SRT形式の文字列
    """
    lines = []
    for i, seg in enumerate(segments, start=1):
        start_ts = format_srt_timestamp(seg["start"])
        end_ts = format_srt_timestamp(seg["end"])
        text = seg["text"]

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)
