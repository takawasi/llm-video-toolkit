"""統合・クリップ生成: 音声とコメントのイベントを統合してハイライト抽出"""
import subprocess
from pathlib import Path
from typing import Optional

from .audio_analyzer import analyze_audio
from .comment_analyzer import analyze_comments


def merge_events(audio_events: list[dict],
                 comment_events: list[dict],
                 merge_window: float = 30.0) -> list[dict]:
    """音声イベントとコメントイベントを統合・スコアリング

    近接するイベントは統合し、スコアを加算。
    音声+コメント両方で検出された箇所は高スコア。

    Args:
        audio_events: 音声解析イベント
        comment_events: コメント解析イベント
        merge_window: 統合判定ウィンドウ（秒）

    Returns:
        統合・スコアリングされたイベントリスト
    """
    # 全イベントを時間順にソート
    all_events = []

    for e in audio_events:
        all_events.append({
            'time': e['time'],
            'score': e.get('score', 1.0),
            'sources': ['audio'],
            'type': e.get('type', 'audio')
        })

    for e in comment_events:
        all_events.append({
            'time': e['time'],
            'score': e.get('score', 1.0),
            'sources': ['comment'],
            'type': e.get('type', 'comment')
        })

    all_events.sort(key=lambda x: x['time'])

    # 近接イベントを統合
    merged = []
    for event in all_events:
        if not merged:
            merged.append(event)
            continue

        last = merged[-1]
        if event['time'] - last['time'] < merge_window:
            # 統合: スコア加算、ソース統合
            last['score'] += event['score']
            last['sources'] = list(set(last['sources'] + event['sources']))
            # 時間は中央に
            last['time'] = (last['time'] + event['time']) / 2
        else:
            merged.append(event)

    # スコア順にソート
    return sorted(merged, key=lambda x: x['score'], reverse=True)


def get_video_duration(video_path: str) -> float:
    """動画の長さを取得（秒）"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def generate_clips(video_path: str,
                   events: list[dict],
                   output_dir: str,
                   num_clips: int = 5,
                   clip_duration: float = 60.0,
                   padding: float = 5.0) -> list[str]:
    """上位イベントからクリップ生成

    Args:
        video_path: 元動画パス
        events: イベントリスト（スコア順想定）
        output_dir: 出力ディレクトリ
        num_clips: 生成クリップ数
        clip_duration: クリップの長さ（秒）
        padding: イベント前後の余白（秒）

    Returns:
        生成されたクリップのパスリスト
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    video_duration = get_video_duration(video_path)
    clips = []

    for i, event in enumerate(events[:num_clips]):
        # クリップの開始・終了時刻
        center = event['time']
        start = max(0, center - clip_duration / 2 - padding)
        duration = min(clip_duration + padding * 2, video_duration - start)

        # 出力ファイル名（時刻とスコアを含める）
        time_str = f"{int(center // 60):02d}m{int(center % 60):02d}s"
        score_str = f"score{event['score']:.1f}"
        output_path = f"{output_dir}/highlight_{i+1:02d}_{time_str}_{score_str}.mp4"

        # FFmpegでクリップ生成
        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", str(start),
            "-t", str(duration),
            "-c", "copy",  # 再エンコードなし（高速）
            "-y", output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            clips.append(output_path)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to create clip at {center}s: {e}")
            continue

    return clips


def generate_timestamp_list(events: list[dict],
                            output_path: str,
                            num_events: int = 20) -> str:
    """タイムスタンプリストを生成（YouTube用）

    Args:
        events: イベントリスト
        output_path: 出力ファイルパス
        num_events: 出力するイベント数

    Returns:
        出力ファイルパス
    """
    lines = ["# ハイライトタイムスタンプ\n"]

    for i, event in enumerate(events[:num_events], 1):
        time = event['time']
        hours = int(time // 3600)
        minutes = int((time % 3600) // 60)
        seconds = int(time % 60)

        if hours > 0:
            timestamp = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            timestamp = f"{minutes}:{seconds:02d}"

        sources = '+'.join(event.get('sources', ['unknown']))
        score = event.get('score', 0)

        lines.append(f"{timestamp} - ハイライト{i} (score: {score:.1f}, {sources})")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return output_path


def extract_highlights(video_path: str,
                       output_dir: str,
                       comment_log: Optional[str] = None,
                       num_clips: int = 5,
                       clip_duration: float = 60.0) -> dict:
    """メインエントリ: ハイライト抽出

    Args:
        video_path: 配信アーカイブ動画パス
        output_dir: 出力ディレクトリ
        comment_log: コメントログパス（オプション）
        num_clips: 生成クリップ数
        clip_duration: クリップの長さ（秒）

    Returns:
        {
            'clips': [クリップパスリスト],
            'timestamps': タイムスタンプファイルパス,
            'events': イベントリスト
        }
    """
    print(f"[archive-highlight] Analyzing: {video_path}")

    # 音声解析
    print("[archive-highlight] Analyzing audio...")
    audio_events = analyze_audio(video_path)
    print(f"[archive-highlight] Found {len(audio_events)} audio events")

    # コメント解析（あれば）
    comment_events = []
    if comment_log and Path(comment_log).exists():
        print(f"[archive-highlight] Analyzing comments: {comment_log}")
        comment_events = analyze_comments(comment_log)
        print(f"[archive-highlight] Found {len(comment_events)} comment events")

    # 統合
    print("[archive-highlight] Merging events...")
    events = merge_events(audio_events, comment_events)
    print(f"[archive-highlight] Merged into {len(events)} events")

    # クリップ生成
    print(f"[archive-highlight] Generating {num_clips} clips...")
    clips = generate_clips(video_path, events, output_dir, num_clips, clip_duration)

    # タイムスタンプリスト生成
    timestamp_path = f"{output_dir}/timestamps.txt"
    generate_timestamp_list(events, timestamp_path)

    print(f"[archive-highlight] Done! {len(clips)} clips generated")

    return {
        'clips': clips,
        'timestamps': timestamp_path,
        'events': events
    }
