"""Whisper streaming: マイク入力→リアルタイム文字起こし"""
import threading
import queue
import tempfile
import wave
import os
from typing import Optional, Callable


class WhisperStream:
    """Whisperによるリアルタイム音声認識

    音声チャンクをバッファリングし、一定量溜まったらWhisperで処理。
    faster-whisper使用で高速化。
    """

    def __init__(self, model_size: str = "base", language: str = "ja",
                 device: str = "cpu", compute_type: str = "int8"):
        """
        Args:
            model_size: Whisperモデルサイズ（tiny/base/small/medium/large）
            language: 言語コード
            device: 処理デバイス（cpu/cuda）
            compute_type: 計算精度（int8/float16/float32）
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type

        self.model = None
        self.audio_queue: queue.Queue = queue.Queue()
        self.text_queue: queue.Queue = queue.Queue()
        self.running = False
        self._thread: Optional[threading.Thread] = None

        # 音声バッファ設定
        self.sample_rate = 16000
        self.buffer_seconds = 3  # 3秒分溜まったら処理
        self.buffer_size = self.sample_rate * 2 * self.buffer_seconds  # 16bit = 2bytes

    def _load_model(self):
        """モデルを遅延ロード"""
        if self.model is None:
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            except ImportError:
                # faster-whisperがない場合は通常のwhisperを試す
                import whisper
                self.model = whisper.load_model(self.model_size)
                self._use_faster_whisper = False
            else:
                self._use_faster_whisper = True

    def start(self):
        """ストリーミング処理開始"""
        self._load_model()
        self.running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """ストリーミング処理停止"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def push_audio(self, audio_chunk: bytes):
        """音声チャンクをキューに追加

        Args:
            audio_chunk: 16kHz, 16bit, mono のPCMデータ
        """
        self.audio_queue.put(audio_chunk)

    def get_text(self, timeout: float = 0.1) -> Optional[str]:
        """認識テキストを取得

        Args:
            timeout: 待機時間（秒）

        Returns:
            認識テキスト（なければNone）
        """
        try:
            return self.text_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _process_loop(self):
        """バックグラウンド処理ループ"""
        buffer = b''

        while self.running:
            try:
                # キューから音声を取得
                chunk = self.audio_queue.get(timeout=0.5)
                buffer += chunk

                # バッファが十分溜まったら処理
                if len(buffer) >= self.buffer_size:
                    text = self._transcribe(buffer)
                    if text:
                        self.text_queue.put(text)
                    buffer = b''

            except queue.Empty:
                # タイムアウト - 残りバッファがあれば処理
                if len(buffer) > self.sample_rate * 2:  # 1秒以上あれば
                    text = self._transcribe(buffer)
                    if text:
                        self.text_queue.put(text)
                    buffer = b''

    def _transcribe(self, audio_data: bytes) -> str:
        """音声データを文字起こし"""
        # 一時ファイルに書き出し
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
            # WAVヘッダー付きで書き出し
            with wave.open(f, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.sample_rate)
                wav.writeframes(audio_data)

        try:
            if self._use_faster_whisper:
                segments, _ = self.model.transcribe(
                    temp_path,
                    language=self.language,
                    beam_size=1,
                    vad_filter=True
                )
                text = ' '.join(seg.text.strip() for seg in segments)
            else:
                result = self.model.transcribe(
                    temp_path,
                    language=self.language,
                    fp16=False
                )
                text = result['text'].strip()

            return text

        finally:
            os.unlink(temp_path)


class AudioCapture:
    """マイク音声キャプチャ

    PyAudioを使用してマイクから音声をキャプチャし、
    コールバックで音声チャンクを渡す。
    """

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        """
        Args:
            sample_rate: サンプリングレート
            chunk_size: 1回のコールバックで渡すサンプル数
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._pa = None
        self._stream = None

    def start(self, callback: Callable[[bytes], None]):
        """キャプチャ開始

        Args:
            callback: 音声チャンクを受け取るコールバック関数
        """
        import pyaudio

        self._pa = pyaudio.PyAudio()
        self._callback = callback

        def stream_callback(in_data, frame_count, time_info, status):
            callback(in_data)
            return (None, pyaudio.paContinue)

        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=stream_callback
        )
        self._stream.start_stream()

    def stop(self):
        """キャプチャ停止"""
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()

    def list_devices(self) -> list[dict]:
        """利用可能な入力デバイス一覧を取得"""
        import pyaudio

        pa = pyaudio.PyAudio()
        devices = []

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })

        pa.terminate()
        return devices
