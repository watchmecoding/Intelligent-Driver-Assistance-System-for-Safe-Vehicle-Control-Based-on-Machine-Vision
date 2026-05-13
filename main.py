# main.py
import cv2
import tkinter as tk
from PIL import Image, ImageTk
import time
import threading
import queue
from datetime import datetime
import numpy as np

from config import *
from face_detector import FaceDetector
from hand_detector import HandDetector
from arduino_controller import ArduinoController
from vehicle_controller import VehicleController
from ui_manager import UIManager
from db_logger import DatabaseLogger
from streaming_client import StreamingClient
from settings_manager import SettingsManager
from settings_window import SettingsWindow


class IntelligentDriverAssistanceSystem:
    def __init__(self):

        self.log_file = open("events_log.txt", "a", encoding="utf-8")

        self.db            = DatabaseLogger()
        self.face_detector = FaceDetector()
        self.hand_detector = HandDetector()
        self.arduino       = ArduinoController(log_callback=self.log_event)
        self.vehicle       = VehicleController(self.arduino)

        self.settings = SettingsManager()
        self.settings.load_from_db(self.db)
        self.settings.apply_to_vehicle(self.vehicle)

        self.window = tk.Tk()
        self.ui     = UIManager(self.window)
        self.ui.settings_callback = self.open_settings

        self.arduino.vehicle = self.vehicle

        self.cap     = cv2.VideoCapture(0)
        self.is_live = False
        self.frame_count = 0
        self._prev_brake = None

        self.streamer      = StreamingClient("http://localhost:5000")
        self._stream_queue = queue.Queue(maxsize=1)
        threading.Timer(2.5, self._push_sessions).start()
        threading.Thread(target=self._stream_worker, daemon=True).start()

        self.ui.start_button.config(command=self.toggle_live)
        self.ui.exit_button.config(command=self.exit_application)
        self.window.protocol("WM_DELETE_WINDOW", self.exit_application)

        self.start_blinking()

        self.face_missing_start_time = None
        self._face_missing_counted   = False
        self._yawn_emergency_counted = False

        # Метрики для стріму
        self._last_ear              = 0.0
        self._last_mar              = 0.0
        self._last_yaw              = 0.0
        self._last_pitch            = 0.0
        self._last_eye_closed_time  = 0.0
        self._last_tilt_time        = 0.0
        self.last_turn_signal_time  = 0.0
        self.last_forward_gaze_time = 0.0
        self.last_brake_countdown   = 0.0
        self._last_face_detected    = False
        self._head_down_logged      = False

        self._emergency_count    = 0
        self._face_missing_count = 0
        self._emergency_counted  = False

        self._driver_info  = self.db.get_driver_info()
        self._vehicle_info = self.db.get_vehicle_info()

        self._display_queue = queue.Queue(maxsize=1)

        self._running = True
        threading.Thread(target=self._processing_loop, daemon=True).start()

    def _processing_loop(self):
        while self._running:
            success, frame = self.cap.read()
            if not success or frame is None:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)

            if self.is_live:
                frame_rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_results = self.face_detector.process(frame_rgb)
                hand_results = self.hand_detector.process(frame_rgb)
                h, w, _      = frame.shape
                current_time = time.time()

                if self.vehicle.force_stop_requested:
                    self.vehicle.force_stop_requested = False
                    self.vehicle.set_speed(0, force_stop=True)
                    self.window.after(0, lambda: self.ui.update_speed_display(0, self.settings.max_speed_kmh))

                if face_results.multi_face_landmarks:
                    self._last_face_detected     = True
                    self.face_missing_start_time = None
                    self._face_missing_counted   = False

                    for lm in face_results.multi_face_landmarks:
                        metrics = self.face_detector.get_metrics(lm.landmark, w, h)
                        ear   = float(metrics['EAR'])
                        mar   = float(metrics['MAR'])
                        yaw   = float(metrics['yaw'])
                        pitch = float(metrics.get('pitch', 0))

                        self._last_ear   = ear
                        self._last_mar   = mar
                        self._last_yaw   = yaw
                        self._last_pitch = pitch

                        # Сонливість
                        drowsy_state, elapsed = self.vehicle.check_drowsiness(ear, current_time)
                        if self.vehicle.emergency_stop_active:
                            self.last_brake_countdown = round(max(0.0, self.settings.emergency_brake_dur - (current_time - self.vehicle.emergency_start_time)), 1)
                        else:
                            self.last_brake_countdown = 0.0
                        self._last_eye_closed_time = elapsed if drowsy_state in ("drowsy", "emergency") else 0.0

                        if drowsy_state == "emergency":
                            brake_progress = min((current_time - self.vehicle.emergency_start_time) / self.settings.emergency_brake_dur, 1.0)
                            remaining_sec  = max(0, self.settings.emergency_brake_dur - (current_time - self.vehicle.emergency_start_time))
                            _bp, _rs, _el = brake_progress, remaining_sec, elapsed
                            self.window.after(0, lambda bp=_bp, rs=_rs, el=_el: (
                                self.ui.warning_label.config(
                                    text=f"АВАРІЙНА ЗУПИНКА! Очі закриті {el:.1f}с\nГальмування: {int(bp*100)}% ({rs:.1f}с до зупинки)",
                                    fg=DANGER_COLOR),
                                self.ui.status_label.config(text="АВАРІЙНА ЗУПИНКА!", fg=DANGER_COLOR)
                            ))
                            self._increment_emergency()

                        elif drowsy_state == "drowsy":
                            if not self.vehicle.emergency_stop_active:
                                _rem = self.settings.stop_time - elapsed
                                _el  = elapsed
                                self.window.after(0, lambda el=_el, rem=_rem: self.ui.warning_label.config(
                                    text=f"Очі закриті {el:.1f}с\nАварійна зупинка через {rem:.1f}с",
                                    fg=WARNING_COLOR))

                        if self.vehicle.emergency_stop_active and drowsy_state not in ("drowsy", "emergency"):
                            brake_progress = min((current_time - self.vehicle.emergency_start_time) / self.settings.emergency_brake_dur, 1.0)
                            remaining_sec  = max(0, self.settings.emergency_brake_dur - (current_time - self.vehicle.emergency_start_time))
                            _bp, _rs = brake_progress, remaining_sec
                            self.window.after(0, lambda bp=_bp, rs=_rs: (
                                self.ui.warning_label.config(
                                    text=f"АВАРІЙНА ЗУПИНКА!\nГальмування: {int(bp*100)}% ({rs:.1f}с до зупинки)",
                                    fg=DANGER_COLOR),
                                self.ui.status_label.config(text="АВАРІЙНА ЗУПИНКА!", fg=DANGER_COLOR)
                            ))

                        # Позіхання
                        yawn_result = self.vehicle.check_yawning(mar, enable_yawns=self.settings.enable_yawns)
                        if yawn_result:
                            _yt = self.vehicle.yawn_times
                            _cy = self.vehicle.consecutive_yawns
                            _ey = self.settings.enable_yawns
                            self.window.after(0, lambda yt=_yt, cy=_cy, ey=_ey: self.ui.yawn_label.config(
                                text=f"Позіхань: {yt}" + (f" (підряд: {cy})" if ey else "")))
                            if self.vehicle.emergency_stop_active and not self._yawn_emergency_counted:
                                self._yawn_emergency_counted = True
                                self._increment_emergency()

                        # Нахил голови
                        tilt_state, tilt_elapsed, tilt_dir = self.vehicle.check_head_tilt(pitch, current_time)
                        self._last_tilt_time = tilt_elapsed if tilt_state in ("tilt_warning", "tilt_emergency") else 0.0

                        # Поворот голови
                        head_state, head_elapsed = self.vehicle.update_head_position(yaw, current_time)
                        self.last_turn_signal_time  = head_elapsed if head_state in ('left_waiting', 'right_waiting') else 0.0
                        self.last_forward_gaze_time = head_elapsed if head_state == 'straight_waiting' else 0.0

                        if tilt_state == "tilt_emergency":
                            brake_progress = min((current_time - self.vehicle.emergency_start_time) / self.settings.emergency_brake_dur, 1.0)
                            remaining_sec  = max(0.0, self.settings.emergency_brake_dur - (current_time - self.vehicle.emergency_start_time))
                            _bp, _rs, _td, _p = brake_progress, remaining_sec, tilt_dir, pitch
                            self.window.after(0, lambda bp=_bp, rs=_rs, td=_td, p=_p: (
                                self.ui.head_status_label.config(
                                    text=f"⚠ Голова {td}! ({abs(p):.0f}°) — АВАРІЙНА ЗУПИНКА",
                                    fg=DANGER_COLOR),
                                self.ui.warning_label.config(
                                    text=f"НАХИЛ ГОЛОВИ {td.upper()} ({abs(p):.0f}°)\nГальмування: {int(bp*100)}% ({rs:.1f}с)",
                                    fg=DANGER_COLOR)
                            ))
                            self._increment_emergency()
                            if not self._head_down_logged:
                                self.log_event(f"НАХИЛ ГОЛОВИ {tilt_dir} ({pitch:.1f}°)")
                                self._head_down_logged = True

                        elif tilt_state == "tilt_warning":
                            _rem = self.settings.tilt_time - tilt_elapsed
                            _td, _p = tilt_dir, pitch
                            self.window.after(0, lambda td=_td, p=_p, rem=_rem: (
                                self.ui.head_status_label.config(
                                    text=f"Нахил {td} ({abs(p):.0f}°) — аварійна зупинка через {rem:.1f}с",
                                    fg=WARNING_COLOR),
                                self.ui.warning_label.config(
                                    text=f"Нахил голови {td} ({abs(p):.0f}°)\nАварійна зупинка через {rem:.1f}с",
                                    fg=WARNING_COLOR)
                            ))
                            self._head_down_logged = False

                        else:
                            self._head_down_logged = False
                            _hs, _he, _y, _p = head_state, head_elapsed, yaw, pitch

                            def _update_head_ui(hs=_hs, he=_he, y=_y):
                                if hs == "left_on":
                                    self.ui.head_status_label.config(text=f"Напрямок: ВЛІВО ({abs(y):.0f}°) — Поворотник ВКЛ", fg=WARNING_COLOR)
                                    self.log_event("Автоповоротник ВЛІВО")
                                elif hs == "left_waiting":
                                    self.ui.head_status_label.config(text=f"Напрямок: Вліво ({abs(y):.0f}°) [{he:.1f}с]", fg=TEXT_COLOR)
                                elif hs == "right_on":
                                    self.ui.head_status_label.config(text=f"Напрямок: ВПРАВО ({y:.0f}°) — Поворотник ВКЛ", fg=WARNING_COLOR)
                                    self.log_event("Автоповоротник ВПРАВО")
                                elif hs == "right_waiting":
                                    self.ui.head_status_label.config(text=f"Напрямок: Вправо ({y:.0f}°) [{he:.1f}с]", fg=TEXT_COLOR)
                                elif hs == "straight_off":
                                    self.ui.head_status_label.config(text="Напрямок: Прямо", fg=SUCCESS_COLOR)
                                    self.log_event("Автоповоротники вимкнено")
                                elif hs == "straight_waiting":
                                    self.ui.head_status_label.config(text=f"Напрямок: Прямо [{he:.1f}с] — Вимкнення...", fg=TEXT_COLOR)
                                else:
                                    self.ui.head_status_label.config(text="Напрямок: Прямо", fg=SUCCESS_COLOR)
                            self.window.after(0, _update_head_ui)

                            peace_remaining = self.settings.peace_cooldown - (current_time - self.vehicle.last_peace_time)

                            if self.settings.enable_yawns and not self.vehicle.emergency_stop_active and drowsy_state not in ("drowsy", "emergency"):
                                _rem_y = self.settings.max_allowed_yawns - self.vehicle.consecutive_yawns
                                _cy    = self.vehicle.consecutive_yawns
                                if _cy > 0 and _rem_y <= 2:
                                    self.window.after(0, lambda cy=_cy, ry=_rem_y: self.ui.warning_label.config(
                                        text=f"{cy} позіхань підряд!\nДо аварійної зупинки: {ry}",
                                        fg=WARNING_COLOR))

                            if not self.vehicle.emergency_stop_active and drowsy_state not in ("drowsy", "emergency"):
                                if 0 < peace_remaining < self.settings.peace_cooldown:
                                    _pr = peace_remaining
                                    self.window.after(0, lambda pr=_pr: self.ui.warning_label.config(
                                        text=f"Аварійку вимкнено\nРух доступний через {pr:.1f}с",
                                        fg=WARNING_COLOR))

                        # Bbox + метрики на кадрі
                        bbox  = self.face_detector.draw_landmarks(frame_rgb, lm.landmark, w, h)
                        color = (0, 0, 255) if self.vehicle.emergency_stop_active else (0, 255, 0)
                        cv2.rectangle(frame_rgb, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                        text = f"EAR:{ear:.2f}  MAR:{mar:.2f}  YAW:{yaw:.0f}  Pitch:{pitch:.0f}"
                        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)

                        # Темний прямокутник під текстом
                        overlay = frame_rgb.copy()
                        cv2.rectangle(overlay, (5, 8), (tw + 15, th + 25), (0, 0, 0), -1)
                        cv2.addWeighted(overlay, 0.4, frame_rgb, 0.6, 0, frame_rgb)

                        # Текст поверх
                        cv2.putText(frame_rgb, text,
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

                    if not self.vehicle.emergency_stop_active and self.vehicle.eye_closed_start_time is None:
                        remaining_yawns = self.settings.max_allowed_yawns - self.vehicle.consecutive_yawns
                        peace_remaining = self.settings.peace_cooldown - (current_time - self.vehicle.last_peace_time)
                        if drowsy_state == "drowsy":
                            pass
                        elif tilt_state in ("tilt_warning", "tilt_emergency"):
                            pass
                        elif self.settings.enable_yawns and self.vehicle.consecutive_yawns > 0 and remaining_yawns <= 2:
                            pass
                        elif 0 < peace_remaining < self.settings.peace_cooldown:
                            pass
                        else:
                            self.window.after(0, lambda: self.ui.warning_label.config(text="Немає попереджень", fg=SUCCESS_COLOR))
                        self.window.after(0, self._update_yawn_limit_label)

                    self.frame_count += 1

                    if self.vehicle.emergency_stop_active:
                        smoothed = self.vehicle.set_speed(0)
                        _sm = smoothed
                        self.window.after(0, lambda sm=_sm: self.ui.update_speed_display(sm, self.settings.max_speed_kmh))

                    # Жести
                    if hand_results.multi_hand_landmarks:
                        for hand_landmarks in hand_results.multi_hand_landmarks:
                            self.hand_detector.draw_landmarks(frame_rgb, hand_landmarks)
                            gesture = self.hand_detector.detect_gesture(hand_landmarks)

                            if gesture['is_peace']:
                                fully_stopped     = self.vehicle.manual_speed < 0.1
                                peace_cooldown_ok = (current_time - self.vehicle.last_peace_time > 1.5)

                                if self.vehicle.emergency_stop_active and fully_stopped and peace_cooldown_ok:
                                    self.vehicle.deactivate_emergency()
                                    self._emergency_counted      = False
                                    self._yawn_emergency_counted = False
                                    _yt = self.vehicle.yawn_times
                                    self.window.after(0, lambda yt=_yt: (
                                        self.ui.yawn_label.config(text=f"Позіхань: {yt} (підряд: 0)"),
                                        self.ui.warning_label.config(text="Аварійку вимкнено жестом peace", fg=SUCCESS_COLOR),
                                        self.ui.status_label.config(text="Система активна", fg=SUCCESS_COLOR)
                                    ))
                                    self.log_event("Аварійку вимкнено жестом peace")

                                elif self.vehicle.emergency_stop_active and not fully_stopped:
                                    self.window.after(0, lambda: self.ui.gesture_label.config(
                                        text="Peace: зачекайте повної зупинки", fg=WARNING_COLOR))
                                    continue

                                self.window.after(0, lambda: self.ui.gesture_label.config(text="Peace Sign", fg=SUCCESS_COLOR))

                            else:
                                if self.vehicle.can_control_speed():
                                    pinch_dist = gesture['pinch_distance']
                                    if pinch_dist < PINCH_STOP:
                                        speed = 0
                                    elif pinch_dist > PINCH_MAX:
                                        speed = 100
                                    else:
                                        speed = ((pinch_dist - PINCH_STOP) / (PINCH_MAX - PINCH_STOP)) * 100

                                    smoothed = self.vehicle.set_speed(speed)
                                    _sm, _sp = smoothed, speed
                                    self.window.after(0, lambda sm=_sm: self.ui.update_speed_display(sm, self.settings.max_speed_kmh))

                                    _pd, _sp2 = pinch_dist, int(speed)
                                    self.window.after(0, lambda sp=_sp2: self.ui.gesture_label.config(
                                        text=f"Щипок: {sp}%", fg=TEXT_COLOR))
                                    cv2.putText(frame_rgb,
                                                f"Pinch: {pinch_dist:.3f}",
                                                (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                                else:
                                    _rem = self.settings.peace_cooldown - (current_time - self.vehicle.last_peace_time)
                                    self.window.after(0, lambda r=_rem: self.ui.gesture_label.config(
                                        text=f"Почекайте {r:.1f}с після peace" if r > 0 else "АВАРІЙКА! Покажіть peace sign",
                                        fg=WARNING_COLOR))
                    else:
                        if not self.vehicle.emergency_stop_active:
                            if self.vehicle.can_control_speed():
                                self.window.after(0, lambda: self.ui.gesture_label.config(
                                    text="Розведіть пальці для руху", fg=TEXT_COLOR))
                            else:
                                _rem = self.settings.peace_cooldown - (current_time - self.vehicle.last_peace_time)
                                self.window.after(0, lambda r=_rem: self.ui.gesture_label.config(
                                    text=f"Почекайте {r:.1f}с після peace" if r > 0 else "Розведіть пальці для руху",
                                    fg=WARNING_COLOR if r > 0 else TEXT_COLOR))
                        else:
                            fully_stopped = self.vehicle.manual_speed < 0.1
                            _ms = int(self.vehicle.manual_speed)
                            self.window.after(0, lambda fs=fully_stopped, ms=_ms: self.ui.gesture_label.config(
                                text="Покажіть peace sign для вимкнення" if fs else f"Гальмування... ({ms}%)",
                                fg=WARNING_COLOR if fs else DANGER_COLOR))

                # Обличчя не знайдено
                else:
                    self._last_face_detected   = False
                    self._head_down_logged     = False
                    self._last_eye_closed_time = 0.0
                    self._last_tilt_time       = 0.0

                    if self.vehicle.emergency_stop_active:
                        self.last_brake_countdown = round(
                            max(0.0, self.settings.emergency_brake_dur - (current_time - self.vehicle.emergency_start_time)), 1)
                    else:
                        self.last_brake_countdown = 0.0

                    if self.face_missing_start_time is None:
                        self.face_missing_start_time = current_time

                    if not self._face_missing_counted:
                        self._face_missing_counted = True
                        self._face_missing_count  += 1
                        _fmc = self._face_missing_count
                        self.window.after(0, lambda c=_fmc: self.ui.face_missing_count_label.config(
                            text=f"Зникнень обличчя: {c}", fg=WARNING_COLOR))
                        self.log_event("Обличчя зникло")

                    elapsed = current_time - self.face_missing_start_time

                    if self.settings.enable_face_missing and elapsed > self.settings.face_missing_time and not self.vehicle.emergency_stop_active:
                        self.vehicle.emergency_stop_active = True
                        self.vehicle.emergency_signal      = True
                        self.vehicle.emergency_start_time  = current_time
                        self.vehicle.emergency_start_speed = self.vehicle.manual_speed
                        self.arduino.send_alarm(True)
                        self._increment_emergency()
                        self.log_event(f"АВАРІЙКА: обличчя відсутнє {elapsed:.1f}с")

                    if self.vehicle.emergency_stop_active:
                        brake_progress = min((current_time - self.vehicle.emergency_start_time) / self.settings.emergency_brake_dur, 1.0)
                        remaining_sec  = max(0.0, self.settings.emergency_brake_dur - (current_time - self.vehicle.emergency_start_time))
                        smoothed = self.vehicle.set_speed(0)
                        _sm, _el, _bp, _rs = smoothed, elapsed, brake_progress, remaining_sec
                        self.window.after(0, lambda sm=_sm, el=_el, bp=_bp, rs=_rs: (
                            self.ui.update_speed_display(sm, self.settings.max_speed_kmh),
                            self.ui.warning_label.config(
                                text=f"ОБЛИЧЧЯ ЗНИКЛО! ({el:.1f}с)\nГальмування: {int(bp*100)}% ({rs:.1f}с до зупинки)",
                                fg=DANGER_COLOR),
                            self.ui.status_label.config(text="АВАРІЙНА ЗУПИНКА! (обличчя відсутнє)", fg=DANGER_COLOR),
                            self.ui.gesture_label.config(text="Покажіть peace sign для вимкнення", fg=DANGER_COLOR)
                        ))
                    else:
                        _rem = max(0.0, self.settings.face_missing_time - elapsed)
                        _el  = elapsed
                        self.window.after(0, lambda el=_el, rem=_rem: self.ui.warning_label.config(
                            text=f"Обличчя не виявлено ({el:.1f}с)\nАварійка через {rem:.1f}с",
                            fg=WARNING_COLOR if rem > 1.0 else DANGER_COLOR))
                        self.window.after(0, lambda: self.ui.gesture_label.config(text="Рух заблоковано", fg=DANGER_COLOR))

                    self.window.after(0, lambda: self.ui.head_status_label.config(text="Обличчя відсутнє", fg=DANGER_COLOR))

                # Гальмо + сигнали
                brake_active = self.vehicle.update_brake_signal()
                if brake_active != self._prev_brake:
                    self.arduino.send_signal("BRAKE", 1 if brake_active else 0)
                    self._prev_brake = brake_active

                frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            # Підготовка кадру для відображення
            frame_rgb_out = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb_out, (640, 480))

            # Кладемо в display_queue (старий дропається)
            if self._display_queue.full():
                try: self._display_queue.get_nowait()
                except queue.Empty: pass
            try: self._display_queue.put_nowait(frame_resized)
            except queue.Full: pass

            # Стрімінг
            if self.is_live:
                if self._stream_queue.full():
                    try: self._stream_queue.get_nowait()
                    except queue.Empty: pass
                try: self._stream_queue.put_nowait(frame_resized.copy())
                except queue.Full: pass

    def _update_display(self):
        try:
            frame_rgb = self._display_queue.get_nowait()
            im_pil = Image.fromarray(frame_rgb)
            imgtk  = ImageTk.PhotoImage(image=im_pil)
            self.ui.video_label.imgtk = imgtk
            self.ui.video_label.configure(image=imgtk)
        except queue.Empty:
            pass
        self.window.after(30, self._update_display)

    def _push_sessions(self):
        def _do():
            data = self.db.get_sessions_summary()
            self.streamer.push_sessions(data)
        threading.Thread(target=_do, daemon=True).start()

    def log_event(self, message):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"[{ts}] {message}\n")
        self.log_file.flush()

    def _update_yawn_limit_label(self):
        if not self.settings.enable_yawns:
            self.ui.yawn_limit_label.config(text="Контроль позіхань вимкнено", fg=TEXT_COLOR)
            self.ui.yawn_limit_label.config(
                text=f"Ліміт: {self.vehicle.max_allowed_yawns} позіхань", fg=WARNING_COLOR)
        else:
            self.ui.yawn_limit_label.config(text="Обмеження: НЕМАЄ", fg=SUCCESS_COLOR)

    def _increment_emergency(self):
        if self.vehicle.emergency_stop_active and not self._emergency_counted:
            self._emergency_counted = True
            self._emergency_count  += 1
            _ec = self._emergency_count
            self.window.after(0, lambda c=_ec: self.ui.emergency_count_label.config(
                text=f"Аварійних зупинок: {c}", fg=DANGER_COLOR))

    def toggle_live(self):
        if self.is_live:
            self.is_live = False
            self.ui.start_button_text.set("Запустити")
            self.ui.start_button.config(style="Start.TButton")
            self.ui.status_label.config(text="Систему призупинено", fg=WARNING_COLOR)

            self.db.end_session(
                total_yawns=self.vehicle.yawn_times,
                emergency_count=self._emergency_count,
                face_missing_count=self._face_missing_count)
            self._push_sessions()
            self.vehicle.reset_all_yawn_counters()

            self.frame_count             = 0
            self._prev_brake             = None
            self.face_missing_start_time = None
            self._face_missing_counted   = False
            self._head_down_logged       = False
            self._emergency_counted      = False
            self._emergency_count        = 0
            self._face_missing_count     = 0
            self._yawn_emergency_counted = False

            self._last_ear             = 0.0
            self._last_mar             = 0.0
            self._last_yaw             = 0.0
            self._last_pitch           = 0.0
            self._last_eye_closed_time = 0.0
            self._last_tilt_time       = 0.0

            self.ui.emergency_count_label.config(text="Аварійних зупинок: 0", fg=TEXT_COLOR)
            self.ui.face_missing_count_label.config(text="Зникнень обличчя: 0", fg=TEXT_COLOR)
            self.ui.yawn_label.config(text="Позіхань: 0")
            self.ui.yawn_limit_label.config(text="Обмеження: НЕМАЄ", fg=SUCCESS_COLOR)

            self.vehicle.speed_buffer.clear()
            self.vehicle.set_speed(0, force_stop=True)
            self.ui.update_speed_display(0, self.settings.max_speed_kmh)

            self.vehicle.left_turn_signal      = False
            self.vehicle.right_turn_signal     = False
            self.vehicle.emergency_signal      = False
            self.vehicle.emergency_stop_active = False
            self.arduino.send_signal("LEFT",      0)
            self.arduino.send_signal("RIGHT",     0)
            self.arduino.send_signal("EMERGENCY", 0)
            self.arduino.send_signal("BRAKE",     0)
            self.arduino.send_alarm(False)
            self._prev_brake = None

            self.ui.update_signals(False, False, False, False)
            self.ui.warning_label.config(text="Немає попереджень", fg=SUCCESS_COLOR)
            self.ui.head_status_label.config(text="Напрямок: Не визначено", fg=TEXT_COLOR)
            self.ui.gesture_label.config(text="Розведіть пальці для руху", fg=TEXT_COLOR)
            self._push_stopped_state()
        else:
            self.is_live = True
            self.ui.start_button_text.set("Зупинити")
            self.ui.start_button.config(style="Stop.TButton")
            self.ui.status_label.config(text="Система активна", fg=SUCCESS_COLOR)
            profile_id = 1 if self.settings.using_defaults else 2
            self.db.start_session(settings_profile_id=profile_id)
            self._push_sessions()
            self._update_yawn_limit_label()

    def open_settings(self):
        SettingsWindow(
            self.window, self.settings, self.db,
            vehicle=self.vehicle,
            on_apply=self._on_settings_applied)

    def _on_settings_applied(self):
        self._update_yawn_limit_label()

    def _push_stopped_state(self):
        def _do():
            state = {
                'is_live': False,
                'ear': 0.0, 'mar': 0.0, 'yaw': 0.0, 'pitch': 0.0,
                'eye_closed_time': 0.0, 'tilt_time': 0.0,
                'speed': 0, 'consecutive_yawns': 0,
                'brake_countdown':    0.0,
                'face_missing_time': 0.0,
                'emergency': False,
                'left_signal': False, 'right_signal': False,
                'brake_active': False, 'face_detected': False,
                'yawns': 0,
                'current_max_yawns': self.settings.max_allowed_yawns,
                'emergency_count': 0, 'face_missing_count': 0,
                'driver': self._driver_info,
                'vehicle': self._vehicle_info,
                'emergency_cooldown': round(max(0.0, self.settings.peace_cooldown - (time.time() - self.vehicle.last_peace_time)), 1),
                'settings': {
                    'max_speed_kmh':          self.settings.max_speed_kmh,
                    'ear_threshold':          self.settings.ear_threshold,
                    'mar_threshold':          self.settings.mar_threshold,
                    'stop_time':              self.settings.stop_time,
                    'emergency_brake_dur':    self.settings.emergency_brake_dur,
                    'pitch_down_threshold':   self.settings.pitch_down_threshold,
                    'pitch_up_threshold':     self.settings.pitch_up_threshold,
                    'tilt_time':              self.settings.tilt_time,
                    'head_turn_angle_left':   self.settings.head_turn_angle_left,
                    'head_turn_angle_right':  self.settings.head_turn_angle_right,
                    'max_allowed_yawns':      self.settings.max_allowed_yawns,
                    'enable_drowsiness':      self.settings.enable_drowsiness,
                    'enable_tilt':            self.settings.enable_tilt,
                    'enable_turn_signals':    self.settings.enable_turn_signals,
                    'enable_yawns':           self.settings.enable_yawns,
                    'face_missing_threshold': self.settings.face_missing_time,
                    'enable_face_missing':    self.settings.enable_face_missing,
                },
            }
            self.streamer.send_update(np.zeros((360, 640, 3), dtype=np.uint8), state)
        threading.Thread(target=_do, daemon=True).start()

    def start_blinking(self):
        self.blink_all()

    def blink_all(self):
        self.ui.blink_state = not getattr(self.ui, 'blink_state', False)
        b = self.ui.blink_state

        is_emergency = self.vehicle.emergency_stop_active

        if is_emergency:
            val = "1" if b else "0"
            self.arduino.send_signal("LEFT",      val)
            self.arduino.send_signal("RIGHT",     val)
            self.arduino.send_signal("EMERGENCY", val)
        else:
            self.arduino.send_signal("LEFT",  "1" if (self.vehicle.left_turn_signal  and b) else "0")
            self.arduino.send_signal("RIGHT", "1" if (self.vehicle.right_turn_signal and b) else "0")
            self.arduino.send_signal("EMERGENCY", "0")

        brake_active = self.vehicle.update_brake_signal() if self.is_live else False
        if is_emergency:
            self.ui.update_signals_emergency(b, brake_active)
        else:
            self.ui.update_signals(
                (self.vehicle.left_turn_signal  or is_emergency) and b,
                (self.vehicle.right_turn_signal or is_emergency) and b,
                is_emergency and b,
                brake_active)

        self.window.after(333, self.blink_all)

    def _stream_worker(self):
        while True:
            try:
                frame = self._stream_queue.get(timeout=1.0)
                if frame is None:
                    break
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                state = {
                    'is_live':           self.is_live,
                    'ear':               round(self._last_ear,   2),
                    'mar':               round(self._last_mar,   2),
                    'yaw':               round(self._last_yaw,   1),
                    'pitch':             round(self._last_pitch, 1),
                    'eye_closed_time':   round(self._last_eye_closed_time, 1),
                    'tilt_time':         round(self._last_tilt_time,       1),
                    'brake_countdown':   round(self.last_brake_countdown, 1),
                    'peace_countdown':   round(max(0.0, self.settings.peace_cooldown - (time.time() - self.vehicle.last_peace_time)), 1),
                    'face_missing_time': round(time.time() - self.face_missing_start_time, 1) if self.face_missing_start_time and not self._last_face_detected else 0.0,
                    'turn_signal_time':  round(self.last_turn_signal_time, 1),
                    'forward_gaze_time': round(self.last_forward_gaze_time, 1),
                    'speed':             int(self.vehicle.manual_speed),
                    'consecutive_yawns': self.vehicle.consecutive_yawns,
                    'emergency':         self.vehicle.emergency_stop_active,
                    'left_signal':       self.vehicle.left_turn_signal or self.vehicle.emergency_stop_active,
                    'right_signal':      self.vehicle.right_turn_signal or self.vehicle.emergency_stop_active,
                    'brake_active':      self._prev_brake if self._prev_brake is not None else False,
                    'face_detected':     self._last_face_detected,
                    'yawns':             self.vehicle.yawn_times,
                    'yawn_emergency':    self.vehicle.emergency_stop_active and self._yawn_emergency_counted,
                    'current_max_yawns': self.vehicle.max_allowed_yawns,
                    'emergency_count':   self._emergency_count,
                    'face_missing_count':self._face_missing_count,
                    'driver':            self._driver_info,
                    'vehicle':           self._vehicle_info,
                    'settings': {
                        'max_speed_kmh':          self.settings.max_speed_kmh,
                        'ear_threshold':          self.settings.ear_threshold,
                        'mar_threshold':          self.settings.mar_threshold,
                        'stop_time':              self.settings.stop_time,
                        'emergency_brake_dur':    self.settings.emergency_brake_dur,
                        'peace_cooldown':         self.settings.peace_cooldown,
                        'turn_signal_delay':      self.settings.head_turn_time,
                        'forward_gaze_cancel':    self.settings.head_turn_off_time,
                        'pitch_down_threshold':   self.settings.pitch_down_threshold,
                        'pitch_up_threshold':     self.settings.pitch_up_threshold,
                        'tilt_time':              self.settings.tilt_time,
                        'head_turn_angle_left':   self.settings.head_turn_angle_left,
                        'head_turn_angle_right':  self.settings.head_turn_angle_right,
                        'max_allowed_yawns':      self.settings.max_allowed_yawns,
                        'enable_drowsiness':      self.settings.enable_drowsiness,
                        'enable_tilt':            self.settings.enable_tilt,
                        'enable_turn_signals':    self.settings.enable_turn_signals,
                        'enable_yawns':           self.settings.enable_yawns,
                        'face_missing_threshold': self.settings.face_missing_time,
                        'enable_face_missing':    self.settings.enable_face_missing,
                    },
                }
                self.streamer.send_update(frame_bgr, state)
            except queue.Empty:
                continue

    def exit_application(self):
        self._running = False
        self.is_live  = False
        if self.db.session_id is not None:
            self.db.end_session(
                total_yawns=self.vehicle.yawn_times,
                emergency_count=self._emergency_count,
                face_missing_count=self._face_missing_count)
        try:
            self._stream_queue.put_nowait(None)
        except queue.Full:
            try: self._stream_queue.get_nowait()
            except queue.Empty: pass
            self._stream_queue.put_nowait(None)
        self.cap.release()
        self.arduino.close()
        self.db.close()
        self.streamer.close()
        self.log_file.close()
        self.window.destroy()

    def run(self):
        self._update_display()
        self.window.mainloop()


if __name__ == "__main__":
    app = IntelligentDriverAssistanceSystem()
    app.run()