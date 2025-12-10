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
def info():
    """ツール情報を表示"""
    click.echo("LLM Video Toolkit v0.1.0")
    click.echo()
    click.echo("利用可能なコマンド:")
    click.echo("  ffmpeg  - 自然言語でFFmpegコマンドを生成・実行")
    click.echo("  clip    - 動画からバズりそうな箇所を自動切り出し")
    click.echo()
    click.echo("詳細: python main.py [COMMAND] --help")


if __name__ == "__main__":
    cli()
