# Phase 0: 目標定義

**Project Name**: llm-video-toolkit
**Root Directory**: /home/heint/CB/プロジェクト/llm-video-toolkit/
**登記日時**: 2025-12-10 21:00

---

## 構造的定義

### State A (現在)
- 動画編集は手作業が多い（FFmpegコマンド覚えられない、毎回検索）
- 配信アーカイブの切り出し・ダイジェスト作成が面倒
- 配信者向けの統合ツールがない（個別ツールはあるが断片的）
- LLMで動画編集を支援するOSSは少ない（商用は高い）

### State B (目標)
- 自然言語で動画編集指示 → 自動実行
- 配信アーカイブから自動でショート切り出し・ダイジェスト生成
- 配信者向けの統合ツールキットとしてGitHub公開
- フリーツールのみで構成（FFmpeg, Whisper, moviepy等）

### Vector (手段)
- LLM（Opus 4.5 / Claude API）が編集指示を解釈
- FFmpeg / moviepy でコマンド・スクリプト生成
- Whisper で音声認識・字幕生成
- モジュール構成で機能追加しやすく

---

## モジュール構成

| モジュール | 機能 | 優先度 |
|-----------|------|--------|
| **ffmpeg-assistant** | 自然言語→FFmpegコマンド生成 | ◎ Phase 1 |
| **clip-cutter** | ショート動画自動切り出し | ◎ Phase 1 |
| **auto-caption** | Whisper字幕生成 + 焼き込み | ○ Phase 2 |
| **live-caption** | リアルタイム字幕 + OBS連携 | ○ Phase 2 |
| **stream-effects** | 配信演出投入（既存移植） | △ Phase 3 |
| **auto-digest** | アーカイブ自動ダイジェスト | △ Phase 3 |

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| 言語 | Python 3.11+ |
| 動画処理 | FFmpeg, moviepy |
| 音声認識 | Whisper, faster-whisper |
| LLM | Claude API (Opus 4.5) |
| 配信連携 | OBS WebSocket |
| Web UI（将来） | Next.js + FFmpeg.wasm |

---

## 差別化

```
既存ツールとの違い:
- 複数機能を統合したツールキット
- 配信者向けに特化（OBS連携、ショート切り出し）
- 日本語対応
- フリーツールのみで構成（依存コスト低）
- LLMを活用した判断（バズ箇所特定等）
```

---

## 公開方針

- GitHub Public（MIT License）
- llm-stream-effects の兄弟プロジェクトとして位置づけ
- VPSサービス化は将来検討

---

## 禁止事項

- 抽象語（適切/柔軟/多角的/検討/考慮）の使用禁止
- 出力は具体的・物理的記述のみ

---

## Phase 0完了: ✓

**次**: Phase 1 詳細設計 → 05_計画仮決定

---

*スッラ*
