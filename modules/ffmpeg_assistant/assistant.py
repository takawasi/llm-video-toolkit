"""FFmpeg Assistant - メインロジック"""

import sys
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm_wrapper import LLMWrapper
from utils.ffmpeg_wrapper import FFmpegWrapper
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class FFmpegAssistant:
    """自然言語からFFmpegコマンドを生成・実行"""

    def __init__(self, llm: LLMWrapper = None):
        """
        初期化

        Args:
            llm: LLMWrapperインスタンス（省略時は自動生成）
        """
        self.llm = llm or LLMWrapper()
        self.ffmpeg = FFmpegWrapper()

    def generate_command(
        self,
        instruction: str,
        input_file: str,
        output_file: str = None,
    ) -> str:
        """
        自然言語指示からFFmpegコマンドを生成

        Args:
            instruction: 自然言語の編集指示
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス（省略時は自動生成）

        Returns:
            生成されたFFmpegコマンド
        """
        input_path = Path(input_file)

        # 出力ファイルが未指定なら自動生成
        if not output_file:
            output_file = str(
                input_path.parent / f"{input_path.stem}_out{input_path.suffix}"
            )

        # ファイル情報を取得
        try:
            file_info = self.ffmpeg.get_file_info(input_file)
            file_info_str = self.ffmpeg.format_info(file_info)
        except Exception as e:
            file_info_str = f"取得失敗: {e}"

        # プロンプト生成
        prompt = USER_PROMPT_TEMPLATE.format(
            instruction=instruction,
            input_file=input_file,
            output_file=output_file,
            file_info=file_info_str,
        )

        # LLMでコマンド生成
        command = self.llm.generate(prompt, SYSTEM_PROMPT)

        # 余分な文字を除去
        command = command.strip()
        if command.startswith("```"):
            lines = command.split("\n")
            command = "\n".join(lines[1:-1]) if len(lines) > 2 else lines[1] if len(lines) > 1 else ""
        command = command.strip()

        return command

    def execute(
        self,
        instruction: str,
        input_file: str,
        output_file: str = None,
        confirm: bool = True,
        dry_run: bool = False,
    ) -> tuple[bool, str, str]:
        """
        コマンド生成→実行

        Args:
            instruction: 自然言語の編集指示
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス
            confirm: 実行前に確認を表示するか
            dry_run: コマンド生成のみ（実行しない）

        Returns:
            (成功フラグ, 生成コマンド, 出力/エラーメッセージ)
        """
        # コマンド生成
        command = self.generate_command(instruction, input_file, output_file)

        if dry_run:
            return True, command, "Dry run - not executed"

        if confirm:
            print(f"\n生成コマンド:\n{command}\n")
            response = input("実行しますか？ [y/N]: ")
            if response.lower() != "y":
                return False, command, "Cancelled by user"

        # 実行
        success, output = self.ffmpeg.run(command)

        return success, command, output


def main():
    """CLI用エントリポイント"""
    import argparse

    parser = argparse.ArgumentParser(description="FFmpeg Assistant")
    parser.add_argument("instruction", help="編集指示（自然言語）")
    parser.add_argument("-i", "--input", required=True, help="入力ファイル")
    parser.add_argument("-o", "--output", help="出力ファイル")
    parser.add_argument("--dry-run", action="store_true", help="コマンド生成のみ")
    parser.add_argument("-y", "--yes", action="store_true", help="確認なしで実行")

    args = parser.parse_args()

    assistant = FFmpegAssistant()
    success, command, output = assistant.execute(
        args.instruction,
        args.input,
        args.output,
        confirm=not args.yes,
        dry_run=args.dry_run,
    )

    if success:
        print(f"\n成功:\n{output}")
    else:
        print(f"\n失敗:\n{output}")


if __name__ == "__main__":
    main()
