# Phase 0: 目標定義 - 配信連携拡張

**Project Name**: llm-video-toolkit / 配信連携拡張（Phase3）
**Abstract Goal**: VTuber/配信者向けアーカイブ自動処理・リアルタイム字幕
**Core Vector**: 配信後作業の自動化 → 切り抜き・ダイジェスト量産
**Root Directory**: /home/heint/CB/プロジェクト/llm-video-toolkit/
**登記日時**: 2025-12-12
**Phase 0完了**: ✓

---

## 背景

llm-video-toolkit Phase1-2 完了済み:
- ffmpeg-assistant（自然言語→FFmpeg）
- clip-cutter（バズ箇所検出）
- auto-caption（字幕生成）
- auto-tag（メタデータ生成）
- thumbnail-candidates（サムネ素材出し）

streaming-system-v2 との連携を強化し、VTuber/配信者の「配信後作業」を自動化する。

---

## ターゲットユーザー

| ペルソナ | 特徴 | ニーズ |
|---------|------|--------|
| **個人VTuber** | 編集時間なし、配信で精一杯 | 自動切り抜き、ハイライト抽出 |
| **切り抜き師** | 素材探しが大変 | 盛り上がり箇所の自動検出 |
| **配信者（非VTuber）** | アーカイブ放置 | ダイジェスト自動生成 |

---

## 新規モジュール

### 1. archive-highlight（優先度: 高）

**目的**: 配信アーカイブから盛り上がり箇所を自動抽出

**入力**:
- 配信アーカイブ動画（MP4/MKV）
- コメントログ（JSON/CSV）※オプション

**処理**:
1. 音声解析（音量ピーク、笑い声検出）
2. コメントログ解析（急増箇所、特定ワード）
3. clip-cutterベースでクリップ生成

**出力**:
- ハイライトクリップ（5-10本）
- タイムスタンプリスト

### 2. live-caption-obs（優先度: 中）

**目的**: 配信中リアルタイム字幕

**入力**:
- マイク音声（リアルタイム）

**処理**:
1. Whisper streaming で音声認識
2. OBS WebSocket で字幕送信

**出力**:
- OBS上に字幕オーバーレイ

### 3. stream-digest（優先度: 低）

**目的**: 2-3時間配信を5-10分ダイジェストに

**入力**:
- 配信アーカイブ
- archive-highlightの出力

**処理**:
1. ハイライト箇所を時系列で繋ぎ
2. トランジション挿入
3. 要約テロップ生成

**出力**:
- ダイジェスト動画

---

## 成功指標

| 指標 | 目標 |
|------|------|
| archive-highlight 処理時間 | 配信時間の1/10以下 |
| ハイライト検出精度 | 80%以上が「見せ場」 |
| live-caption 遅延 | 2秒以内 |

---

## 関連

- [llm-video-toolkit README](../README.md)
- [streaming-system-v2](../../streaming-system-v2/)
- [clip-cutter モジュール](../modules/clip_cutter.py)

---

*2025-12-12 作成*
