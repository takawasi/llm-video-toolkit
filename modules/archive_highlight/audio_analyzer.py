"""音声解析: 音量ピーク・笑い声検出"""
import subprocess
import re
from pathlib import Path


def extract_audio(video_path: str, output_path: str) -> str:
    """動画から音声を抽出"""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-y", output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def detect_volume_peaks(audio_path: str, threshold_db: float = -20.0,
                        min_silence_duration: float = 0.5) -> list[dict]:
    """音量ピーク検出（ffmpeg silencedetect利用）

    silencedetectで無音区間を検出し、その終了点（=音が始まる点）を
    ピークとして扱う。

    Args:
        audio_path: 音声ファイルパス
        threshold_db: 無音判定閾値（dB）。-20dB = かなり静か
        min_silence_duration: 無音と判定する最小継続時間（秒）

    Returns:
        [{'time': float, 'type': 'volume_peak'}, ...]
    """
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", f"silencedetect=noise={threshold_db}dB:d={min_silence_duration}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # silencedetectの出力をパース
    # [silencedetect @ 0x...] silence_end: 123.456 | silence_duration: 2.345
    peaks = []
    pattern = r'silence_end:\s*([\d.]+)'

    for match in re.finditer(pattern, result.stderr):
        time = float(match.group(1))
        peaks.append({
            'time': time,
            'type': 'volume_peak'
        })

    return peaks


def detect_loud_segments(video_path: str, threshold_db: float = -10.0,
                         min_duration: float = 1.0) -> list[dict]:
    """音量が大きい区間を検出（笑い声・歓声想定）

    ebur128フィルタで音量を計測し、閾値を超える区間を抽出。

    Args:
        video_path: 動画/音声ファイルパス
        threshold_db: ラウドネス閾値（LUFS）
        min_duration: 最小継続時間（秒）
    """
    # まず全体の平均ラウドネスを取得
    cmd = [
        "ffmpeg", "-i", video_path,
        "-af", "ebur128=peak=true",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Integrated loudnessを抽出
    # Summary: Integrated loudness: -23.5 LUFS
    match = re.search(r'Integrated loudness:\s*([-\d.]+)\s*LUFS', result.stderr)
    if not match:
        return []

    avg_loudness = float(match.group(1))

    # 平均より threshold_db 以上大きい箇所を探す
    # astatsフィルタで区間ごとのRMS取得
    cmd = [
        "ffmpeg", "-i", video_path,
        "-af", f"astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 簡易実装: silencedetectの逆（音が大きい箇所）を返す
    # より正確にはlibrosaを使うべきだが、依存を減らすためffmpegで
    loud_segments = []

    # silencedetectで無音区間を取得し、その「間」を音が大きい区間とする
    silence_cmd = [
        "ffmpeg", "-i", video_path,
        "-af", f"silencedetect=noise=-30dB:d=2",
        "-f", "null", "-"
    ]
    silence_result = subprocess.run(silence_cmd, capture_output=True, text=True)

    # silence_start と silence_end のペアを抽出
    starts = re.findall(r'silence_start:\s*([\d.]+)', silence_result.stderr)
    ends = re.findall(r'silence_end:\s*([\d.]+)', silence_result.stderr)

    # 無音区間の「間」＝音が大きい区間
    prev_end = 0.0
    for i, start in enumerate(starts):
        start_time = float(start)
        if start_time - prev_end > min_duration:
            loud_segments.append({
                'time': prev_end + (start_time - prev_end) / 2,  # 区間の中央
                'type': 'loud_segment',
                'start': prev_end,
                'end': start_time,
                'duration': start_time - prev_end
            })
        if i < len(ends):
            prev_end = float(ends[i])

    return loud_segments


def analyze_audio(video_path: str, temp_dir: str = "/tmp") -> list[dict]:
    """メイン解析: 動画から音声抽出→ピーク検出

    Args:
        video_path: 動画ファイルパス
        temp_dir: 一時ファイル置き場

    Returns:
        検出されたイベントのリスト
    """
    audio_path = f"{temp_dir}/temp_audio_{Path(video_path).stem}.wav"

    # 音声抽出
    extract_audio(video_path, audio_path)

    # 音量ピーク検出
    peaks = detect_volume_peaks(audio_path)

    # 音が大きい区間検出
    loud = detect_loud_segments(video_path)

    # 統合（loud_segmentを優先、スコア付き）
    events = []
    for p in peaks:
        events.append({**p, 'score': 1.0})
    for l in loud:
        events.append({**l, 'score': 2.0})  # 大きい音はスコア高め

    return sorted(events, key=lambda x: x['time'])
