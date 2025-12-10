# llm-video-toolkit

LLM活用の動画制作・配信支援ツールキット

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## 特徴

- **自然言語でFFmpegを操作** - 「720pに変換して」「音声を削除」など日本語で指示
- **バズ箇所自動検出** - LLMが動画から「シェアされそうな部分」を特定
- **配信者向け** - ショート動画切り出し、アーカイブ編集に最適化

---

## クイックスタート

```bash
# クローン
git clone https://github.com/takawasi/llm-video-toolkit.git
cd llm-video-toolkit

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
export ANTHROPIC_API_KEY="your-api-key"

# 動作確認
python main.py --help
```

---

## 使い方

### ffmpeg-assistant: 自然言語でFFmpegコマンド生成

```bash
# 基本
python main.py ffmpeg "720pに変換して" -i input.mp4 -o output.mp4

# 確認なしで実行
python main.py ffmpeg "音声を削除" -i input.mp4 -o silent.mp4 -y

# コマンド確認のみ（実行しない）
python main.py ffmpeg "最初の30秒だけ切り出し" -i input.mp4 --dry-run
```

### clip-cutter: バズ箇所自動切り出し

```bash
# 5箇所自動切り出し
python main.py clip -i long_video.mp4 -n 5 -o ./clips

# 秒数指定
python main.py clip -i video.mp4 -n 3 --min-duration 20 --max-duration 45
```

---

### auto-caption: 字幕自動生成

```bash
# SRT出力のみ
python main.py caption -i input.mp4 -o output.srt

# 字幕を動画に焼き込み
python main.py caption -i input.mp4 -o output.mp4 --burn

# LLM校正をスキップ（高速）
python main.py caption -i input.mp4 -o output.srt --no-correct

# スタイル指定
python main.py caption -i input.mp4 -o output.mp4 --burn --style "FontSize=32,Bold=1"
```

### auto-tag: タイトル・タグ・説明文生成

```bash
# 基本
python main.py tag -i input.mp4

# ジャンル指定（より最適化された提案）
python main.py tag -i input.mp4 --genre gaming
python main.py tag -i input.mp4 --genre vlog
python main.py tag -i input.mp4 --genre tech

# 出力ファイル指定
python main.py tag -i input.mp4 -o metadata.json
```

**出力例**:
```json
{
  "titles": ["【衝撃】〇〇すぎた件", "〇〇してみた結果www", ...],
  "tags": ["〇〇", "〇〇解説", "〇〇やってみた", ...],
  "description": "この動画では〇〇について...",
  "summary": "動画の要約"
}
```

### thumbnail-candidates: サムネ素材出し

```bash
# 基本（5枚抽出）
python main.py thumbnail -i input.mp4 -o ./thumbnails

# 枚数指定
python main.py thumbnail -i input.mp4 -n 10

# キャッチコピーのトーン指定
python main.py thumbnail -i input.mp4 --tone funny      # ユーモア重視
python main.py thumbnail -i input.mp4 --tone clickbait  # クリック誘発重視
```

**出力**:
```
./thumbnails/
├── frame_01_01_32.jpg   # 1分32秒のフレーム
├── frame_02_03_45.jpg
├── ...
└── captions.txt         # キャッチコピー案
```

※最終的なサムネイル作成は人間が行う想定（素材出しまでがAIの役割）

---

## モジュール構成

| モジュール | 機能 | 状態 |
|-----------|------|------|
| **ffmpeg-assistant** | 自然言語→FFmpegコマンド生成 | ✅ 完了 |
| **clip-cutter** | ショート動画自動切り出し | ✅ 完了 |
| **auto-caption** | Whisper字幕生成 + LLM校正 + 焼き込み | ✅ 完了 |
| **auto-tag** | タグ・説明文・タイトル案生成 | ✅ 完了 |
| **thumbnail-candidates** | サムネ素材出し + キャッチコピー案 | ✅ 完了 |
| **live-caption** | リアルタイム字幕 + OBS連携 | 📋 予定 |

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| 言語 | Python 3.11+ |
| 動画処理 | FFmpeg |
| 音声認識 | OpenAI Whisper |
| LLM | Claude API (Anthropic) |

---

## 依存ライブラリ

| ライブラリ | ライセンス | 用途 |
|-----------|-----------|------|
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | MIT | Claude API |
| [openai-whisper](https://github.com/openai/whisper) | MIT | 音声認識 |
| [click](https://github.com/pallets/click) | BSD-3-Clause | CLI |
| [pyyaml](https://github.com/yaml/pyyaml) | MIT | 設定ファイル |

---

## 必要環境

- Python 3.11+
- FFmpeg（システムにインストール済み）
- Anthropic API Key

---

## ライセンス

MIT License - 詳細は [LICENSE](./LICENSE) を参照

---

## 作者

- **TAKAWASI** - [GitHub](https://github.com/takawasi)

---

## 関連リンク

- [紹介ページ](https://takawasi-social.com/llm-video-toolkit/) - 使い方・デモ
