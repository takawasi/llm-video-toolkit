"""OBS WebSocket連携: 字幕テキストをOBSに送信"""
import json
import hashlib
import base64
import threading
from typing import Optional, Callable


class OBSConnector:
    """OBS WebSocket接続・テキストソース更新

    OBS Studio 28以降のWebSocket 5.x プロトコルに対応。
    """

    def __init__(self, host: str = "localhost", port: int = 4455,
                 password: str = ""):
        """
        Args:
            host: OBS WebSocketホスト
            port: OBS WebSocketポート
            password: OBS WebSocketパスワード（空文字で認証なし）
        """
        self.host = host
        self.port = port
        self.password = password
        self._ws = None
        self._connected = False
        self._message_id = 0

    def connect(self) -> bool:
        """OBS WebSocketに接続

        Returns:
            接続成功ならTrue
        """
        try:
            import websocket
        except ImportError:
            # websocket-clientがない場合はobs-websocket-pyを試す
            return self._connect_obswebsocket()

        url = f"ws://{self.host}:{self.port}"

        try:
            self._ws = websocket.create_connection(url, timeout=5)

            # Hello メッセージを受信
            hello = json.loads(self._ws.recv())
            if hello.get('op') != 0:
                return False

            # 認証が必要な場合
            auth_required = hello.get('d', {}).get('authentication')
            if auth_required and self.password:
                auth_response = self._generate_auth(
                    auth_required['challenge'],
                    auth_required['salt']
                )
                identify_msg = {
                    'op': 1,
                    'd': {
                        'rpcVersion': 1,
                        'authentication': auth_response
                    }
                }
            else:
                identify_msg = {
                    'op': 1,
                    'd': {'rpcVersion': 1}
                }

            self._ws.send(json.dumps(identify_msg))

            # Identified を待つ
            response = json.loads(self._ws.recv())
            if response.get('op') == 2:
                self._connected = True
                return True

            return False

        except Exception as e:
            print(f"OBS connection error: {e}")
            return False

    def _connect_obswebsocket(self) -> bool:
        """obs-websocket-py を使用した接続（フォールバック）"""
        try:
            from obswebsocket import obsws, requests as obs_requests
            self._ws = obsws(self.host, self.port, self.password)
            self._ws.connect()
            self._connected = True
            self._use_obswebsocket = True
            return True
        except Exception as e:
            print(f"OBS connection error (obswebsocket): {e}")
            return False

    def _generate_auth(self, challenge: str, salt: str) -> str:
        """OBS WebSocket認証文字列を生成"""
        secret = base64.b64encode(
            hashlib.sha256(
                (self.password + salt).encode()
            ).digest()
        ).decode()

        auth = base64.b64encode(
            hashlib.sha256(
                (secret + challenge).encode()
            ).digest()
        ).decode()

        return auth

    def disconnect(self):
        """切断"""
        if self._ws:
            try:
                if hasattr(self, '_use_obswebsocket') and self._use_obswebsocket:
                    self._ws.disconnect()
                else:
                    self._ws.close()
            except:
                pass
        self._connected = False

    def set_text(self, source_name: str, text: str) -> bool:
        """テキストソースの内容を更新

        Args:
            source_name: OBSのテキストソース名
            text: 表示するテキスト

        Returns:
            成功ならTrue
        """
        if not self._connected:
            return False

        try:
            if hasattr(self, '_use_obswebsocket') and self._use_obswebsocket:
                from obswebsocket import requests as obs_requests
                self._ws.call(obs_requests.SetInputSettings(
                    inputName=source_name,
                    inputSettings={"text": text}
                ))
            else:
                self._message_id += 1
                request = {
                    'op': 6,
                    'd': {
                        'requestType': 'SetInputSettings',
                        'requestId': str(self._message_id),
                        'requestData': {
                            'inputName': source_name,
                            'inputSettings': {'text': text}
                        }
                    }
                }
                self._ws.send(json.dumps(request))
                # レスポンスを受信（非同期だが簡易実装）
                self._ws.recv()

            return True

        except Exception as e:
            print(f"OBS set_text error: {e}")
            return False

    def clear_text(self, source_name: str) -> bool:
        """テキストをクリア"""
        return self.set_text(source_name, "")

    @property
    def is_connected(self) -> bool:
        """接続状態"""
        return self._connected


class CaptionDisplay:
    """字幕表示管理

    行数制限・スクロール・フェード管理を行う。
    """

    def __init__(self, max_lines: int = 3, max_chars_per_line: int = 40,
                 fade_after_seconds: float = 5.0):
        """
        Args:
            max_lines: 最大表示行数
            max_chars_per_line: 1行あたりの最大文字数
            fade_after_seconds: 自動消去までの秒数（0で無効）
        """
        self.max_lines = max_lines
        self.max_chars_per_line = max_chars_per_line
        self.fade_after_seconds = fade_after_seconds

        self._lines: list[str] = []
        self._fade_timer: Optional[threading.Timer] = None
        self._fade_callback: Optional[Callable] = None

    def add_text(self, text: str) -> str:
        """テキストを追加して表示文字列を返す

        Args:
            text: 追加するテキスト

        Returns:
            現在の表示文字列（改行区切り）
        """
        # 長い文は分割
        while len(text) > self.max_chars_per_line:
            self._lines.append(text[:self.max_chars_per_line])
            text = text[self.max_chars_per_line:]

        if text:
            self._lines.append(text)

        # 行数制限
        if len(self._lines) > self.max_lines:
            self._lines = self._lines[-self.max_lines:]

        # フェードタイマーリセット
        self._reset_fade_timer()

        return self.get_display_text()

    def get_display_text(self) -> str:
        """現在の表示文字列を取得"""
        return '\n'.join(self._lines)

    def clear(self):
        """クリア"""
        self._lines = []
        self._cancel_fade_timer()

    def set_fade_callback(self, callback: Callable):
        """フェード時のコールバックを設定"""
        self._fade_callback = callback

    def _reset_fade_timer(self):
        """フェードタイマーをリセット"""
        self._cancel_fade_timer()

        if self.fade_after_seconds > 0 and self._fade_callback:
            self._fade_timer = threading.Timer(
                self.fade_after_seconds,
                self._on_fade
            )
            self._fade_timer.daemon = True
            self._fade_timer.start()

    def _cancel_fade_timer(self):
        """フェードタイマーをキャンセル"""
        if self._fade_timer:
            self._fade_timer.cancel()
            self._fade_timer = None

    def _on_fade(self):
        """フェード実行"""
        self._lines = []
        if self._fade_callback:
            self._fade_callback()


class LiveCaptionManager:
    """リアルタイム字幕の統合管理

    WhisperStream + OBSConnector + CaptionDisplay を統合。
    """

    def __init__(self, obs_host: str = "localhost", obs_port: int = 4455,
                 obs_password: str = "", source_name: str = "字幕",
                 whisper_model: str = "base", language: str = "ja"):
        """
        Args:
            obs_host: OBS WebSocketホスト
            obs_port: OBS WebSocketポート
            obs_password: OBS WebSocketパスワード
            source_name: OBSのテキストソース名
            whisper_model: Whisperモデルサイズ
            language: 言語コード
        """
        from .whisper_stream import WhisperStream, AudioCapture

        self.source_name = source_name

        self.whisper = WhisperStream(model_size=whisper_model, language=language)
        self.obs = OBSConnector(obs_host, obs_port, obs_password)
        self.display = CaptionDisplay()
        self.audio = AudioCapture()

        self._running = False
        self._process_thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """リアルタイム字幕を開始

        Returns:
            開始成功ならTrue
        """
        # OBS接続
        if not self.obs.connect():
            print("Failed to connect to OBS")
            return False

        # フェード時にOBSをクリア
        self.display.set_fade_callback(
            lambda: self.obs.clear_text(self.source_name)
        )

        # Whisper開始
        self.whisper.start()

        # 音声キャプチャ開始
        self.audio.start(self.whisper.push_audio)

        # テキスト処理スレッド開始
        self._running = True
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

        return True

    def stop(self):
        """停止"""
        self._running = False

        if self._process_thread:
            self._process_thread.join(timeout=2.0)

        self.audio.stop()
        self.whisper.stop()
        self.obs.clear_text(self.source_name)
        self.obs.disconnect()

    def _process_loop(self):
        """テキスト処理ループ"""
        while self._running:
            text = self.whisper.get_text(timeout=0.1)
            if text:
                display_text = self.display.add_text(text)
                self.obs.set_text(self.source_name, display_text)
                print(f"[字幕] {text}")
