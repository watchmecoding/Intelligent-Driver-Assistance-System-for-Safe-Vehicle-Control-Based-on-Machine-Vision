# arduino_controller.py
import serial
import serial.tools.list_ports
import time
import threading
from config import *

class ArduinoController:
    def __init__(self, log_callback=None):
        self.serial = None
        self.connected = False
        self.log_callback = log_callback
        self.vehicle = None
        self.speed_reset_callback = None

        self._last_speed = -1
        self._last_signals = {}
        self._reconnecting = False
        self._write_lock = threading.Lock()
        self._reader_running = False
        self._reader_thread = None

        self.command_sent_callback = None

        threading.Thread(target=self.connect, daemon=True).start()

    def connect(self):
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
        except Exception:
            pass

        self.serial = None
        self.connected = False
        self._reader_running = False

        ports = serial.tools.list_ports.comports()

        for p in ports:
            print(f"Ардуїно підключено на порті: {p.device} | {p.description} | {p.hwid}")

        for port in ports:
            if any(k in port.description for k in ("Arduino", "CH340", "USB")):
                try:
                    ser = serial.Serial(port.device, 115200, timeout=0.1)
                    time.sleep(2)

                    try:
                        ser.reset_input_buffer()
                        ser.reset_output_buffer()
                    except Exception:
                        pass

                    self.serial = ser
                    self.connected = True
                    self._reader_running = True
                    self._last_speed = -1
                    self._last_signals.clear()

                    if self._reader_thread is None or not self._reader_thread.is_alive():
                        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
                        self._reader_thread.start()

                    if self.log_callback:
                        self.log_callback(f"Arduino підключено: {port.device}")
                    return

                except Exception as e:
                    if self.log_callback:
                        self.log_callback(f"Помилка підключення Arduino: {e}")

        if self.log_callback:
            self.log_callback("Arduino не знайдено")

    def _handle_disconnect(self, reason):
        if not self.connected and not self.serial:
            return

        print(f"Arduino відключено: {reason}")
        if self.log_callback:
            self.log_callback(f"Arduino відключено: {reason}")

        self.connected = False
        self._reader_running = False
        self._last_speed = -1
        self._last_signals.clear()

        try:
            if self.serial and self.serial.is_open:
                try:
                    self.serial.write(b"SPEED:0\n")
                    self.serial.write(b"ALARM:0\n")
                    self.serial.flush()
                except Exception:
                    pass

                try:
                    self.serial.reset_input_buffer()
                    self.serial.reset_output_buffer()
                except Exception:
                    pass

                self.serial.close()
        except Exception:
            pass

        self.serial = None

        if self.vehicle:
            self.vehicle.force_stop_requested = True

        self._try_reconnect()

    def send_command(self, command):
        with self._write_lock:
            if not self.connected or not self.serial:
                return

            try:
                self.serial.write(f"{command}\n".encode())
                if self.command_sent_callback:
                    self.command_sent_callback(command)
            except Exception as e:
                self._handle_disconnect(str(e))

    def send_signal(self, signal, state):
        with self._write_lock:
            if self._last_signals.get(signal) == state:
                return

            if not self.connected or not self.serial:
                return

            try:
                self.serial.write(f"{signal}:{state}\n".encode())
                self._last_signals[signal] = state
                if self.command_sent_callback:
                    self.command_sent_callback(f"{signal}:{state}")
            except Exception as e:
                self._handle_disconnect(str(e))

    def _try_reconnect(self, delay=1.0):
        if self._reconnecting:
            return

        self._reconnecting = True

        def _worker():
            i = 0
            try:
                while not self.connected:
                    i += 1
                    if self.log_callback:
                        self.log_callback(f"Спроба перепідключення Arduino ({i})...")

                    self.connect()
                    if self.connected:
                        return

                    time.sleep(delay)
            finally:
                self._reconnecting = False

        threading.Thread(target=_worker, daemon=True).start()

    def send_speed(self, speed_percent):
        speed = int(round(speed_percent))
        speed = max(0, min(100, speed))

        if speed == self._last_speed:
            return

        self._last_speed = speed
        self.send_command(f"SPEED:{speed}")

    def send_alarm(self, active):
        self.send_signal("ALARM", 1 if active else 0)

    def _reader_loop(self):
        while self._reader_running:
            if not self.connected or not self.serial:
                time.sleep(0.05)
                continue

            try:
                line = self.serial.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                if self.log_callback:
                    self.log_callback(f"SERIAL:{line}")

            except Exception as e:
                self._handle_disconnect(str(e))
                break

    def close(self):
        self._reader_running = False

        with self._write_lock:
            try:
                if self.serial and self.serial.is_open:
                    for signal in ["LEFT", "RIGHT", "EMERGENCY", "BRAKE"]:
                        self.serial.write(f"{signal}:0\n".encode())
                    self.serial.write(b"ALARM:0\n")
                    self.serial.write(b"STOP\n")
                    self.serial.flush()

                    try:
                        self.serial.reset_input_buffer()
                        self.serial.reset_output_buffer()
                    except Exception:
                        pass

                    time.sleep(0.1)
                    self.serial.close()
            except Exception:
                pass

        self.connected = False
        self.serial = None
        self._last_speed = -1
        self._last_signals.clear()