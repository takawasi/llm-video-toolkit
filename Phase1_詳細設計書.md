# Phase 1: 詳細設計書

**Project**: llm-video-toolkit
**作成日**: 2025-12-10
**Phase 0**: [Phase0_目標定義.md](./Phase0_目標定義.md)

---

## 1. アーキテクチャ概要

```
┌─────────────────────────────────────────────────────┐
│                    llm-video-toolkit                 │
├─────────────────────────────────────────────────────┤
│  CLI / API Layer                                     │
│    main.py (エントリポイント)                         │
├─────────────────────────────────────────────────────┤
│  Modules                                             │
│    ├── ffmpeg_assistant/  (自然言語→FFmpegコマンド)   │
│    ├── clip_cutter/       (ショート切り出し)          │
│    ├── auto_caption/      (字幕生成+焼き込み)         │
│    └── ...                                           │
├─────────────────────────────────────────────────────┤
│  Utils                                               │
│    ├── llm_wrapper.py     (Claude API)               │
│    ├── ffmpeg_wrapper.py  (FFmpeg実行)               │
│    └── whisper_wrapper.py (音声認識)                 │
└─────────────────────────────────────────────────────┘
```

---

## 2. モジュール詳細設計

### 2.1 ffmpeg-assistant

**目的**: 自然言語の指示からFFmpegコマンドを生成・実行

**入力**:
- 自然言語の編集指示（例: 「この動画を720pに変換して」）
- 入力ファイルパス

**出力**:
- FFmpegコマンド
- 実行結果（成功/失敗）
- 出力ファイル

**処理フロー**:
```
1. ユーザー入力受付（自然言語）
2. LLM（Claude）にコマンド生成依頼
3. FFmpegコマンド取得
4. ユーザー確認（オプション）
5. FFmpeg実行
6. 結果返却
```

**プロンプト設計**:
```
あなたはFFmpegのエキスパートです。
ユーザーの指示に従って、適切なFFmpegコマンドを生成してください。

【ルール】
- 出力は ffmpeg コマンドのみ
- コメントや説明は不要
- 入力ファイルは {input_file} として参照
- 出力ファイルは {output_file} として参照

【ユーザー指示】
{user_instruction}

【入力ファイル情報】
{file_info}
```

**ファイル構成**:
```
modules/ffmpeg_assistant/
├── __init__.py
├── assistant.py      # メインロジック
├── prompts.py        # プロンプトテンプレート
└── presets.py        # よく使うコマンドプリセット
```

---

### 2.2 clip-cutter

**目的**: 長尺動画から「バズりそうな箇所」を自動で切り出し

**入力**:
- 動画ファイル
- 切り出し条件（オプション: 長さ、数、縦横比）

**出力**:
- 切り出された短尺動画（複数）
- 切り出し箇所のメタデータ

**処理フロー**:
```
1. Whisperで全編文字起こし
2. LLMに「バズりそうな発言」を特定させる
3. タイムスタンプ抽出
4. 各箇所をFFmpegでカット
5. （オプション）縦動画変換、字幕焼き込み
```

**バズ判定プロンプト**:
```
以下は動画の文字起こしです。
SNSでシェアされやすい「バズりそうな発言」を5箇所特定してください。

【判定基準】
- 逆張り・意外な主張
- 強い言い切り
- 面白い言い回し
- 感情的なピーク
- 議論を呼びそうな内容

【出力形式】
JSON形式で出力:
[
  {"start": "00:01:30", "end": "00:02:15", "reason": "理由"},
  ...
]

【文字起こし】
{transcript}
```

**ファイル構成**:
```
modules/clip_cutter/
├── __init__.py
├── cutter.py         # メインロジック
├── transcriber.py    # Whisper連携
├── analyzer.py       # LLMによる分析
└── exporter.py       # 動画出力
```

---

### 2.3 auto-caption

**目的**: 動画に字幕を自動生成・焼き込み

**入力**:
- 動画ファイル
- 字幕スタイル（オプション）

**出力**:
- 字幕付き動画
- SRTファイル（オプション）

**処理フロー**:
```
1. Whisperで文字起こし
2. タイムスタンプ付きセグメント生成
3. SRTファイル生成
4. FFmpegで字幕焼き込み
```

**ファイル構成**:
```
modules/auto_caption/
├── __init__.py
├── caption.py        # メインロジック
├── srt_generator.py  # SRT生成
└── styles.py         # 字幕スタイル定義
```

---

## 3. 共通ユーティリティ

### 3.1 llm_wrapper.py

```python
# インターフェース
class LLMWrapper:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        ...

    def generate(self, prompt: str, system: str = None) -> str:
        """プロンプトを送信してレスポンスを取得"""
        ...

    def generate_json(self, prompt: str, system: str = None) -> dict:
        """JSON形式でレスポンスを取得"""
        ...
```

### 3.2 ffmpeg_wrapper.py

```python
# インターフェース
class FFmpegWrapper:
    @staticmethod
    def run(command: str) -> tuple[bool, str]:
        """FFmpegコマンドを実行"""
        ...

    @staticmethod
    def get_file_info(filepath: str) -> dict:
        """動画ファイル情報を取得"""
        ...

    @staticmethod
    def cut(input_file: str, output_file: str, start: str, end: str) -> bool:
        """動画をカット"""
        ...
```

### 3.3 whisper_wrapper.py

```python
# インターフェース
class WhisperWrapper:
    def __init__(self, model: str = "base"):
        ...

    def transcribe(self, audio_file: str) -> list[dict]:
        """音声を文字起こし（タイムスタンプ付き）"""
        # Returns: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]
        ...
```

---

## 4. CLI設計

```bash
# ffmpeg-assistant
llm-video-toolkit ffmpeg "この動画を720pに変換して" -i input.mp4 -o output.mp4

# clip-cutter
llm-video-toolkit clip -i long_video.mp4 -n 5 --vertical --caption

# auto-caption
llm-video-toolkit caption -i video.mp4 -o captioned.mp4 --style default
```

---

## 5. 設定ファイル

```yaml
# config/settings.yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY

whisper:
  model: base  # tiny, base, small, medium, large
  language: ja

ffmpeg:
  path: ffmpeg  # or /usr/bin/ffmpeg

output:
  default_dir: ./output
  video_format: mp4
  video_codec: libx264
```

---

## 6. 依存関係

```
# requirements.txt
anthropic>=0.18.0
openai-whisper>=20231117
moviepy>=1.0.3
click>=8.1.0
pyyaml>=6.0
```

---

## 7. 実装優先度

| 順序 | 対象 | 理由 |
|------|------|------|
| 1 | utils/ | 全モジュールの基盤 |
| 2 | ffmpeg-assistant | 最もシンプル、単独で価値あり |
| 3 | clip-cutter | メイン機能、Whisper統合 |
| 4 | auto-caption | clip-cutterの派生 |
| 5 | CLI | 全モジュール統合 |

---

## 8. Phase 1 完了条件

- [ ] utils/ 3ファイル実装完了
- [ ] ffmpeg-assistant 動作確認
- [ ] clip-cutter 動作確認
- [ ] CLI基本動作

---

*スッラ*
