# streaming_client.py
import cv2
import json
import queue
import threading
import requests

class StreamingClient:
    def __init__(self, server_url):
        self.url       = server_url.rstrip('/')
        self.connected = False
        self._queue    = queue.Queue(maxsize=1)
        self._session  = requests.Session()
        threading.Thread(target=self._worker, daemon=True).start()
        self._ping()

    def _ping(self):
        try:
            r = self._session.get(f"{self.url}/state", timeout=1)
            self.connected = r.status_code == 200
        except Exception:
            self.connected = False

    def send_update(self, frame_bgr, state: dict):
        try:
            self._queue.put_nowait((frame_bgr, state))
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait((frame_bgr, state))
            except queue.Full:
                pass

    def push_sessions(self, sessions: list):
        def _do():
            try:
                self._session.post(
                    f"{self.url}/push_sessions",
                    json=sessions,
                    timeout=2.0)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _worker(self):
        while True:
            try:
                frame, state = self._queue.get(timeout=1.0)
                _, jpeg = cv2.imencode(
                    '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                self._session.post(
                    f"{self.url}/update",
                    files={'frame': ('f.jpg', jpeg.tobytes(), 'image/jpeg')},
                    data={'state': json.dumps(state, default=str)},
                    timeout=0.5)
                self.connected = True
            except queue.Empty:
                continue
            except Exception:
                self.connected = False

    def close(self):
        self._session.close()
