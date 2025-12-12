"""ダイジェスト生成: ハイライトを繋いで短尺動画作成"""
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional


def create_concat_file(clip_paths: list[str], output_path: str) -> str:
    """FFmpeg concat用ファイル作成"""
    with open(output_path, 'w') as f:
        for clip in clip_paths:
            # パスをエスケープ
            escaped = clip.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    return output_path


def add_transition(clip1: str, clip2: str, output: str,
                   transition: str = "fade", duration: float = 0.5) -> str:
    """2クリップ間にトランジション追加

    Args:
        clip1: 前クリップパス
        clip2: 後クリップパス
        output: 出力パス
        transition: トランジション種類（fade, wipeleft, circleclose等）
        duration: トランジション時間（秒）

    Returns:
        出力パス
    """
    # クリップの長さを取得
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        clip1
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    clip1_duration = float(result.stdout.strip())
    offset = max(0, clip1_duration - duration)

    cmd = [
        "ffmpeg",
        "-i", clip1, "-i", clip2,
        "-filter_complex",
        f"[0:v][1:v]xfade=transition={transition}:duration={duration}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={duration}[a]",
        "-map", "[v]", "-map", "[a]",
        "-y", output
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output


def generate_title_card(text: str, duration: float, output: str,
                        width: int = 1920, height: int = 1080,
                        font_size: int = 72) -> str:
    """タイトルカード生成

    Args:
        text: タイトルテキスト
        duration: 表示時間（秒）
        output: 出力パス
        width: 横幅
        height: 高さ
        font_size: フォントサイズ

    Returns:
        出力パス
    """
    # テキストをエスケープ
    escaped_text = text.replace("'", "\\'").replace(":", "\\:")

    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"color=c=black:s={width}x{height}:d={duration}",
        "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:d={duration}",
        "-vf", f"drawtext=text='{escaped_text}':fontcolor=white:fontsize={font_size}:"
               f"x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        "-shortest",
        "-y", output
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output


def concat_clips(clip_paths: list[str], output: str,
                 with_transition: bool = False,
                 transition_type: str = "fade",
                 transition_duration: float = 0.5) -> str:
    """クリップを連結

    Args:
        clip_paths: クリップパスリスト
        output: 出力パス
        with_transition: トランジション追加
        transition_type: トランジション種類
        transition_duration: トランジション時間

    Returns:
        出力パス
    """
    if not clip_paths:
        raise ValueError("クリップが指定されていません")

    if len(clip_paths) == 1:
        # 1クリップのみ - コピー
        subprocess.run(["cp", clip_paths[0], output], check=True)
        return output

    if with_transition:
        # トランジション付き（重い）
        current = clip_paths[0]
        temp_dir = tempfile.mkdtemp(prefix="digest_")

        try:
            for i, clip in enumerate(clip_paths[1:], 1):
                temp_output = os.path.join(temp_dir, f"trans_{i}.mp4")
                current = add_transition(
                    current, clip, temp_output,
                    transition_type, transition_duration
                )
            # 最終出力
            subprocess.run(["cp", current, output], check=True)
        finally:
            # 一時ファイル削除
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        # 単純連結（軽い）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for clip in clip_paths:
                escaped = clip.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")
            concat_file = f.name

        try:
            cmd = [
                "ffmpeg",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-y", output
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        finally:
            os.unlink(concat_file)

    return output


def build_digest(video_path: str, output_path: str,
                 highlight_clips: list[str] = None,
                 comment_log: str = None,
                 num_highlights: int = 10,
                 title: str = None,
                 with_transition: bool = False,
                 clip_duration: float = 60.0) -> str:
    """メインエントリ: ダイジェスト生成

    配信アーカイブからハイライトを抽出し、ダイジェスト動画を生成。
    既存のハイライトクリップを渡すことも可能。

    Args:
        video_path: 元動画パス
        output_path: 出力パス
        highlight_clips: 既存のハイライトクリップ（なければ自動抽出）
        comment_log: コメントログパス
        num_highlights: ハイライト数
        title: タイトルカード（なければスキップ）
        with_transition: トランジション追加
        clip_duration: 各クリップの長さ（秒）

    Returns:
        出力パス
    """
    clips = []
    temp_files = []

    try:
        # タイトルカード
        if title:
            title_card = tempfile.NamedTemporaryFile(
                suffix='.mp4', delete=False, prefix='digest_title_'
            ).name
            temp_files.append(title_card)
            generate_title_card(title, 3.0, title_card)
            clips.append(title_card)
            print(f"[digest] タイトルカード生成: {title}")

        # ハイライトクリップ
        if highlight_clips:
            # 既存クリップを使用
            clips.extend(highlight_clips)
            print(f"[digest] 既存クリップ使用: {len(highlight_clips)}個")
        else:
            # archive-highlight で自動抽出
            from modules.archive_highlight import extract_highlights

            highlight_dir = tempfile.mkdtemp(prefix='digest_highlights_')
            temp_files.append(highlight_dir)

            print(f"[digest] ハイライト抽出中: {video_path}")
            result = extract_highlights(
                video_path, highlight_dir,
                comment_log=comment_log,
                num_clips=num_highlights,
                clip_duration=clip_duration
            )
            clips.extend(result['clips'])
            print(f"[digest] {len(result['clips'])}個のハイライト抽出完了")

        # 連結
        if not clips or (title and len(clips) == 1):
            raise ValueError("ハイライトが見つかりません")

        print(f"[digest] {len(clips)}クリップを連結中...")
        concat_clips(clips, output_path, with_transition)

        print(f"[digest] 完了: {output_path}")
        return output_path

    finally:
        # 一時ファイル/ディレクトリ削除（タイトルカードのみ）
        import shutil
        for temp in temp_files:
            if os.path.isdir(temp):
                # ハイライトディレクトリは残す（デバッグ用）
                pass
            elif os.path.isfile(temp):
                try:
                    os.unlink(temp)
                except:
                    pass
