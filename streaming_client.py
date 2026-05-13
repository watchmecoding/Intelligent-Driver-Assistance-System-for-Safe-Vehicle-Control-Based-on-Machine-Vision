# streaming_client.py
import cv2
import json
import queue
import threading
import requests
import server as _server
import time
class StreamingClient:
    def __init__(self, server_url):
        self.url       = server_url.rstrip('/')
        self.connected = False
        self._queue    = queue.Queue(maxsize=2)
        self._session  = requests.Session()

        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(
            target=_server.run_server,
            kwargs={'host': '0.0.0.0', 'port': 5000},
            daemon=True,
        ).start()

        time.sleep(0.5)
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
        try:
            self._session.post(
                f"{self.url}/push_sessions",
                json=sessions,
                timeout=1.0)
        except Exception:
            pass

    def _worker(self):
        while True:
            try:
                frame, state = self._queue.get(timeout=1.0)
                _server.push_frame_direct(frame, state)
                self.connected = True
            except queue.Empty:
                continue
            except Exception:
                self.connected = False

    def close(self):
        self._session.close()
