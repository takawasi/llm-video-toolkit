# llm-video-toolkit

**Natural language FFmpeg wrapper powered by LLM.**

Turn `"cut first 30 seconds"` into actual ffmpeg commands. No more googling FFmpeg syntax.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/takawasi/llm-video-toolkit.git
cd llm-video-toolkit

# 2. Install
pip install -r requirements.txt

# 3. Run
export ANTHROPIC_API_KEY="your-key"
python main.py ffmpeg "convert to 720p" -i input.mp4 -o output.mp4
```

That's it. The tool generates and executes the FFmpeg command for you.

---

## What It Does

| You say | Tool generates |
|---------|----------------|
| "convert to 720p" | `ffmpeg -i input.mp4 -vf scale=-1:720 output.mp4` |
| "remove audio" | `ffmpeg -i input.mp4 -an output.mp4` |
| "cut first 30 seconds" | `ffmpeg -i input.mp4 -t 30 -c copy output.mp4` |
| "extract audio as mp3" | `ffmpeg -i input.mp4 -vn -acodec mp3 output.mp3` |

---

## Features

| Module | Description |
|--------|-------------|
| **ffmpeg-assistant** | Natural language → FFmpeg command generation |
| **clip-cutter** | Auto-detect "viral moments" in long videos |
| **auto-caption** | Whisper transcription + LLM correction + burn-in |
| **auto-tag** | Generate titles, tags, descriptions for uploads |
| **thumbnail-candidates** | Extract best frames + generate caption ideas |
| **archive-highlight** | Extract highlights from stream archives |
| **live-caption** | Real-time captions with OBS integration |
| **stream-digest** | Auto-generate highlight reels |

---

## Usage Examples

### ffmpeg-assistant

```bash
# Basic
python main.py ffmpeg "convert to 720p" -i input.mp4 -o output.mp4

# Preview command without executing
python main.py ffmpeg "remove audio" -i input.mp4 --dry-run

# Skip confirmation
python main.py ffmpeg "cut first 30 seconds" -i input.mp4 -o clip.mp4 -y
```

### clip-cutter

```bash
# Auto-extract 5 viral-worthy clips
python main.py clip -i long_video.mp4 -n 5 -o ./clips
```

### auto-caption

```bash
# Generate SRT
python main.py caption -i input.mp4 -o output.srt

# Burn captions into video
python main.py caption -i input.mp4 -o output.mp4 --burn
```

---

## API Configuration

Currently uses **Claude API** (Anthropic).

```bash
export ANTHROPIC_API_KEY="your-key"
```

OpenAI and local LLM support planned for future releases.

---

## Requirements

- **Python 3.11+**
- **FFmpeg** (must be in PATH)
- **API Key** (Claude, OpenAI, or local LLM)
- **Whisper** (for caption features, optional)

---

## Why This Tool?

1. **No more FFmpeg syntax googling** - Just describe what you want
2. **Streamers & YouTubers** - Optimized for content creation workflows
3. **CLI-first** - Fast, scriptable, no GUI overhead
4. **Transparent** - Shows generated command before execution

---

## License

MIT License - Use it, modify it, ship it.

---

## Links

- [GitHub](https://github.com/takawasi/llm-video-toolkit)
- [Demo Page](https://takawasi-social.com/llm-video-toolkit/)

---

Made with Claude Code
