#!/usr/bin/env python3
"""LLM Video Toolkit - CLI エントリポイント"""

import click
import yaml
from pathlib import Path

from modules.ffmpeg_assistant import FFmpegAssistant
from utils.llm_wrapper import LLMWrapper
# ClipCutterは遅延ロード（whisperインストール不要でffmpegコマンドのみ使用可能に）


def load_config() -> dict:
    """設定ファイルを読み込む"""
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """LLM Video Toolkit - 動画編集支援ツール

    自然言語でFFmpegコマンドを生成したり、
    動画からバズりそうな箇所を自動で切り出します。
    """
    pass


@cli.command()
@click.argument("instruction")
@click.option("-i", "--input", "input_file", required=True, help="入力動画ファイル")
@click.option("-o", "--output", "output_file", help="出力ファイル（省略時は自動生成）")
@click.option("--dry-run", is_flag=True, help="コマンド生成のみ（実行しない）")
@click.option("-y", "--yes", is_flag=True, help="確認なしで実行")
def ffmpeg(instruction, input_file, output_file, dry_run, yes):
    """自然言語でFFmpegコマンドを生成・実行

    例: python main.py ffmpeg "720pに変換" -i input.mp4 -o output.mp4
    """
    config = load_config()
    llm_config = config.get("llm", {})

    try:
        llm = LLMWrapper(model=llm_config.get("model", "claude-sonnet-4-20250514"))
        assistant = FFmpegAssistant(llm=llm)

        success, command, output = assistant.execute(
            instruction,
            input_file,
            output_file,
            confirm=not yes,
            dry_run=dry_run,
        )

        if dry_run:
            click.echo(f"\n生成コマンド:\n{command}")
        elif success:
            click.echo(click.style("\n成功!", fg="green"))
            click.echo(f"コマンド: {command}")
        else:
            click.echo(click.style("\n失敗", fg="red"))
            click.echo(f"エラー: {output}")

    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command()
@click.option("-i", "--input", "input_file", required=True, help="入力動画ファイル")
@click.option("-o", "--output-dir", help="出力ディレクトリ（省略時は./clips）")
@click.option("-n", "--num-clips", default=5, help="切り出すクリップ数")
@click.option("--min-duration", default=15, help="最小秒数")
@click.option("--max-duration", default=60, help="最大秒数")
@click.option("--language", default="ja", help="言語コード")
def clip(input_file, output_dir, num_clips, min_duration, max_duration, language):
    """動画からバズりそうな箇所を自動切り出し

    例: python main.py clip -i long_video.mp4 -n 5 -o ./clips
    """
    config = load_config()
    llm_config = config.get("llm", {})
    whisper_config = config.get("whisper", {})

    try:
        from modules.clip_cutter import ClipCutter
        llm = LLMWrapper(model=llm_config.get("model", "claude-sonnet-4-20250514"))
        cutter = ClipCutter(llm=llm)

        results = cutter.cut_clips(
            input_file,
            output_dir=output_dir,
            num_clips=num_clips,
            min_duration=min_duration,
            max_duration=max_duration,
            language=language,
        )

        success_count = len([r for r in results if r["success"]])
        click.echo(f"\n完了: {success_count} / {len(results)} クリップ")

        if success_count > 0:
            click.echo("\n切り出し結果:")
            for r in results:
                status = click.style("OK", fg="green") if r["success"] else click.style("FAIL", fg="red")
                click.echo(f"  [{status}] {Path(r['file']).name}")
                click.echo(f"        {r['start']} - {r['end']}: {r['reason']}")

    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command()
@click.option("-i", "--input", "input_file", required=True, help="入力動画ファイル")
@click.option("-o", "--output", "output_file", help="出力ファイル（SRTまたはMP4）")
@click.option("--burn", is_flag=True, help="字幕を動画に焼き込む")
@click.option("--no-correct", is_flag=True, help="LLM校正をスキップ")
@click.option("--language", default="ja", help="言語コード")
@click.option("--style", help="字幕スタイル（FontSize=24,Bold=1等）")
def caption(input_file, output_file, burn, no_correct, language, style):
    """動画から字幕を自動生成（SRT出力 or 焼き込み）

    例: python main.py caption -i input.mp4 -o output.srt
        python main.py caption -i input.mp4 -o output.mp4 --burn
    """
    config = load_config()
    llm_config = config.get("llm", {})

    try:
        from modules.auto_caption import AutoCaption
        llm = LLMWrapper(model=llm_config.get("model", "claude-sonnet-4-20250514"))
        captioner = AutoCaption(llm=llm)

        if burn:
            # 焼き込みモード
            if not output_file:
                output_file = str(Path(input_file).with_stem(
                    Path(input_file).stem + "_captioned"
                ).with_suffix(".mp4"))

            success = captioner.generate_and_burn(
                input_file,
                output_file,
                language=language,
                correct=not no_correct,
                style=style,
            )

            if success:
                click.echo(click.style("\n成功!", fg="green"))
            else:
                click.echo(click.style("\n失敗", fg="red"))
                raise SystemExit(1)
        else:
            # SRT出力モード
            segments, srt_file = captioner.generate(
                input_file,
                output_file=output_file,
                language=language,
                correct=not no_correct,
            )
            click.echo(click.style(f"\n成功! {len(segments)}セグメント", fg="green"))
            click.echo(f"出力: {srt_file}")

    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command()
@click.option("-i", "--input", "input_file", required=True, help="入力動画ファイル")
@click.option("-o", "--output", "output_file", help="出力JSONファイル")
@click.option("--genre", default="default",
              type=click.Choice(["gaming", "vlog", "tech", "entertainment", "education", "music", "default"]),
              help="動画ジャンル")
@click.option("--language", default="ja", help="言語コード")
def tag(input_file, output_file, genre, language):
    """動画からタイトル案・タグ・説明文を自動生成

    例: python main.py tag -i input.mp4
        python main.py tag -i input.mp4 --genre gaming -o metadata.json
    """
    config = load_config()
    llm_config = config.get("llm", {})

    try:
        from modules.auto_tag import AutoTag
        llm = LLMWrapper(model=llm_config.get("model", "claude-sonnet-4-20250514"))
        tagger = AutoTag(llm=llm)

        result = tagger.generate(
            input_file,
            output_file=output_file,
            genre=genre,
            language=language,
        )

        # 結果を表示
        tagger.print_result(result)
        click.echo(click.style("\n成功!", fg="green"))

    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command()
@click.option("-i", "--input", "input_file", required=True, help="入力動画ファイル")
@click.option("-o", "--output-dir", help="出力ディレクトリ（省略時は./thumbnails）")
@click.option("-n", "--num-frames", default=5, help="抽出するフレーム数")
@click.option("--tone", default="default",
              type=click.Choice(["funny", "serious", "clickbait", "default"]),
              help="キャッチコピーのトーン")
@click.option("--language", default="ja", help="言語コード")
def thumbnail(input_file, output_dir, num_frames, tone, language):
    """サムネ候補フレームを抽出 + キャッチコピー案生成

    例: python main.py thumbnail -i input.mp4 -o ./thumbnails
        python main.py thumbnail -i input.mp4 -n 10 --tone clickbait
    """
    config = load_config()
    llm_config = config.get("llm", {})

    try:
        from modules.thumbnail_candidates import ThumbnailCandidates
        llm = LLMWrapper(model=llm_config.get("model", "claude-sonnet-4-20250514"))
        extractor = ThumbnailCandidates(llm=llm)

        results = extractor.extract(
            input_file,
            output_dir=output_dir,
            num_frames=num_frames,
            language=language,
            tone=tone,
        )

        # 結果を表示
        extractor.print_result(results)

        success_count = len([r for r in results if r.get("frame")])
        click.echo(click.style(f"\n成功! {success_count}フレーム抽出", fg="green"))

    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command()
@click.option("-i", "--input", "input_file", required=True, help="配信アーカイブ動画")
@click.option("-o", "--output-dir", default="./highlights", help="出力ディレクトリ")
@click.option("-c", "--comments", "comment_log", help="コメントログ（JSON/CSV）")
@click.option("-n", "--num-clips", default=5, help="抽出クリップ数")
@click.option("--duration", default=60, help="クリップの長さ（秒）")
def highlight(input_file, output_dir, comment_log, num_clips, duration):
    """配信アーカイブからハイライトを自動抽出

    音声解析（音量ピーク・笑い声）とコメントログ（急増箇所）を
    組み合わせて、盛り上がった箇所を自動検出・切り出し。

    例: python main.py highlight -i archive.mp4 -o ./highlights
        python main.py highlight -i archive.mp4 -c comments.json -n 10
    """
    try:
        from modules.archive_highlight import extract_highlights

        click.echo(f"解析中: {input_file}")
        if comment_log:
            click.echo(f"コメントログ: {comment_log}")

        result = extract_highlights(
            input_file,
            output_dir,
            comment_log=comment_log,
            num_clips=num_clips,
            clip_duration=duration,
        )

        click.echo(click.style(f"\n成功! {len(result['clips'])}クリップ生成", fg="green"))
        click.echo(f"\n生成されたクリップ:")
        for clip in result['clips']:
            click.echo(f"  {clip}")
        click.echo(f"\nタイムスタンプ: {result['timestamps']}")

    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command("live-caption")
@click.option("--obs-host", default="localhost", help="OBS WebSocketホスト")
@click.option("--obs-port", default=4455, help="OBS WebSocketポート")
@click.option("--obs-password", default="", help="OBS WebSocketパスワード")
@click.option("--source", default="字幕", help="OBSテキストソース名")
@click.option("--model", default="base", help="Whisperモデル（tiny/base/small/medium/large）")
@click.option("--language", default="ja", help="言語コード")
def live_caption(obs_host, obs_port, obs_password, source, model, language):
    """リアルタイム字幕をOBSに送信

    マイク入力をWhisperでリアルタイム認識し、
    OBSのテキストソースに字幕を表示。

    例: python main.py live-caption --source "字幕テキスト"
        python main.py live-caption --model small --obs-password secret
    """
    try:
        from modules.live_caption import LiveCaptionManager

        manager = LiveCaptionManager(
            obs_host=obs_host,
            obs_port=obs_port,
            obs_password=obs_password,
            source_name=source,
            whisper_model=model,
            language=language,
        )

        click.echo(f"OBS接続中: {obs_host}:{obs_port}")
        click.echo(f"テキストソース: {source}")
        click.echo(f"Whisperモデル: {model}")
        click.echo()

        if not manager.start():
            click.echo(click.style("OBS接続失敗", fg="red"))
            raise SystemExit(1)

        click.echo(click.style("リアルタイム字幕開始！", fg="green"))
        click.echo("Ctrl+C で停止")
        click.echo()

        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n停止中...")
            manager.stop()
            click.echo("完了")

    except ImportError as e:
        click.echo(click.style(f"依存関係エラー: {e}", fg="red"))
        click.echo("必要: pip install faster-whisper pyaudio websocket-client")
        raise SystemExit(1)
    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command()
@click.option("-i", "--input", "input_file", required=True, help="配信アーカイブ動画")
@click.option("-o", "--output", "output_file", default="./digest.mp4", help="出力パス")
@click.option("-c", "--comments", "comment_log", default=None, help="コメントログ（JSON/CSV）")
@click.option("-n", "--num-clips", default=10, help="ハイライト数")
@click.option("--duration", default=60, help="各クリップの長さ（秒）")
@click.option("--title", default=None, help="タイトルカードテキスト")
@click.option("--transition/--no-transition", default=False, help="トランジション追加")
def digest(input_file, output_file, comment_log, num_clips, duration, title, transition):
    """配信アーカイブからダイジェスト動画を生成

    ハイライト箇所を自動抽出し、連結してダイジェスト動画を作成。
    タイトルカードやトランジション効果もオプションで追加可能。

    例: python main.py digest -i archive.mp4 -o digest.mp4
        python main.py digest -i archive.mp4 --title "配信ダイジェスト" --transition
    """
    try:
        from modules.stream_digest import build_digest

        click.echo(f"ダイジェスト生成中: {input_file}")
        click.echo(f"ハイライト数: {num_clips}")
        if title:
            click.echo(f"タイトル: {title}")
        if transition:
            click.echo("トランジション: 有効")

        result = build_digest(
            input_file, output_file,
            comment_log=comment_log,
            num_highlights=num_clips,
            clip_duration=duration,
            title=title,
            with_transition=transition
        )

        click.echo(click.style(f"\n成功!", fg="green"))
        click.echo(f"出力: {result}")

    except Exception as e:
        click.echo(click.style(f"エラー: {e}", fg="red"))
        raise SystemExit(1)


@cli.command()
def info():
    """ツール情報を表示"""
    click.echo("LLM Video Toolkit v0.5.0")
    click.echo()
    click.echo("利用可能なコマンド:")
    click.echo("  ffmpeg       - 自然言語でFFmpegコマンドを生成・実行")
    click.echo("  clip         - 動画からバズりそうな箇所を自動切り出し")
    click.echo("  caption      - 字幕自動生成（SRT出力 or 焼き込み）")
    click.echo("  tag          - タイトル案・タグ・説明文を自動生成")
    click.echo("  thumbnail    - サムネ候補フレーム抽出 + キャッチコピー案")
    click.echo("  highlight    - 配信アーカイブからハイライト自動抽出")
    click.echo("  digest       - 配信アーカイブからダイジェスト動画生成")
    click.echo("  live-caption - リアルタイム字幕（Whisper + OBS連携）")
    click.echo()
    click.echo("詳細: python main.py [COMMAND] --help")


if __name__ == "__main__":
    cli()
