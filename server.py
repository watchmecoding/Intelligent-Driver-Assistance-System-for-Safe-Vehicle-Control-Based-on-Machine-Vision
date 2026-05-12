# server.py
from flask import Flask, Response, jsonify, request, render_template
import threading
import numpy as np
import cv2
import json
import time
import logging

app = Flask(__name__)


_lock     = threading.Lock()
_frame    = None
_state    = {}
_sessions = []

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/video_feed')
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
                frame = cv2.resize(frame, (640, 360),
                                   interpolation=cv2.INTER_LINEAR)

            _, jpeg = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   jpeg.tobytes() + b'\r\n')

    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/update', methods=['POST'])
def update():
    global _frame, _state
    f = request.files.get('frame')
    s = request.form.get('state', '{}')
    if f:
        nparr = np.frombuffer(f.read(), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is not None:
            with _lock:
                _frame = frame.copy()
                _state = json.loads(s)
    return 'OK', 200


@app.route('/state')
def get_state():
    with _lock:
        return jsonify(_state)

@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/push_sessions', methods=['POST'])
def push_sessions():
    global _sessions
    data = request.get_json(force=True)
    with _lock:
        _sessions = data or []
    return 'OK', 200

@app.route('/sessions')
def get_sessions():
    with _lock:
        return jsonify(_sessions)

@app.route('/favicon.ico')
def favicon():
    return '', 204

def push_frame_direct(frame_bgr, state_dict):
    global _frame, _state
    with _lock:
        if frame_bgr is not None:
            _frame = frame_bgr.copy()
        _state = state_dict


def run_server(host='0.0.0.0', port=5000):
    app.run(host=host, port=port, threaded=True, use_reloader=False)


if __name__ == '__main__':
    run_server()