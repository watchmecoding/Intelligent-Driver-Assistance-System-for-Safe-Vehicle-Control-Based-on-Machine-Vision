# server.py
from flask import Flask, Response, jsonify, request, render_template
import threading
import numpy as np
import cv2
import json
import time
import logging
import socket
import flask.cli


flask.cli.show_server_banner = lambda *args: None


def setup_server_logger(log_path="logs/dashboard_server.log"):
    logger = logging.getLogger("dashboard_server")

    if not logger.handlers:
        fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(fh)

    return logger


server_logger = setup_server_logger()

app = Flask(__name__)
app.logger.disabled = True
logging.getLogger("werkzeug").disabled = True

_lock = threading.Lock()
_frame = None
_state = {}
_sessions = []

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            with _lock:
                frame = _frame.copy() if _frame is not None else None

            if frame is None:
                time.sleep(0.02)
                continue

            h, w = frame.shape[:2]
            if w > 640:
                frame = cv2.resize(
                    frame,
                    (640, 360),
                    interpolation=cv2.INTER_LINEAR
                )

            ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if not ok:
                server_logger.warning("Не вдалося закодувати кадр у JPEG для /video_feed")
                time.sleep(0.02)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                jpeg.tobytes() +
                b"\r\n"
            )
            time.sleep(0.033)

    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/update", methods=["POST"])
def update():
    global _frame, _state

    try:
        f = request.files.get("frame")
        s = request.form.get("state", "{}")

        if f:
            nparr = np.frombuffer(f.read(), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                with _lock:
                    _frame = frame.copy()
                    _state = json.loads(s)
            else:
                server_logger.warning("Отримано frame, але cv2.imdecode повернув None")

        return "OK", 200

    except json.JSONDecodeError as e:
        server_logger.error(f"JSON state decode error in /update: {e}")
        return "Bad state JSON", 400

    except Exception as e:
        server_logger.exception(f"Помилка в /update: {e}")
        return "Server error", 500


@app.route("/state")
def get_state():
    with _lock:
        return jsonify(_state)


@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/push_sessions", methods=["POST"])
def push_sessions():
    global _sessions

    try:
        data = request.get_json(force=True)
        with _lock:
            _sessions = data or []

        server_logger.info(f"Оновлено список сесій: {len(_sessions)} записів")
        return "OK", 200

    except Exception as e:
        server_logger.exception(f"Помилка в /push_sessions: {e}")
        return "Server error", 500


@app.route("/sessions")
def get_sessions():
    with _lock:
        return jsonify(_sessions)


@app.route("/favicon.ico")
def favicon():
    return "", 204


def push_frame_direct(frame_bgr, state_dict):
    global _frame, _state
    with _lock:
        if frame_bgr is not None:
            _frame = frame_bgr.copy()
        _state = state_dict


def run_server(host="0.0.0.0", port=5000):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        server_logger.info(f"Дашборд доступний: http://{local_ip}:{port}")

    except Exception as e:
        local_ip = "127.0.0.1"
        server_logger.warning(f"Не вдалося визначити локальний IP, fallback на {local_ip}: {e}")

    try:
        server_logger.info(f"Запуск Flask сервера на {host}:{port}")
        app.run(host=host, port=port, threaded=True, use_reloader=False, debug=False)

    except OSError as e:
        server_logger.exception(f"Сервер не запустився: {e}")

    except Exception as e:
        server_logger.exception(f"Непередбачена помилка сервера: {e}")


if __name__ == "__main__":
    run_server()