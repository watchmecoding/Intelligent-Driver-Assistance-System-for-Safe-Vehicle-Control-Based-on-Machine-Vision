# arduino_controller.py
import serial
import serial.tools.list_ports
import time
import threading
from config import *


class ArduinoController:
    def __init__(self, log_callback=None):
        self.serial               = None
        self.connected            = False
        self.log_callback         = log_callback
        self.vehicle              = None
        self.speed_reset_callback = None 
        self._last_speed          = -1
        self._reconnecting        = False
        self._write_lock          = threading.Lock()  # ← ДОДАТИ
        threading.Thread(target=self.connect, daemon=True).start()

    def connect(self):
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
        except Exception:
            pass
        self.serial = None
                
        ports = serial.tools.list_ports.comports()

        for p in ports:
            print(f"Ардуїно підключено на порті: {p.device} | {p.description} | {p.hwid}")

        for port in ports:
            if any(k in port.description
                   for k in ('Arduino', 'CH340', 'USB')):
                try:
                    self.serial = serial.Serial(
                        port.device, 9600, timeout=0.1)
                    time.sleep(2)
                    self.connected = True
                    if self.log_callback:
                        self.log_callback(
                            f"Arduino підключено: {port.device}")
                    return
                except Exception as e:
                    if self.log_callback:
                        self.log_callback(
                            f"Помилка підключення Arduino: {e}")
        if self.log_callback:
            self.log_callback("Arduino не знайдено")

    def _handle_disconnect(self, reason):
        if not self.connected:
            return
        print(f"Arduino відключено: {reason}")
        if self.log_callback:
            self.log_callback(f"Arduino відключено: {reason}")
        self.connected = False
        # Намагаємось зупинити серво перед reconnect
        try:
            if self.serial and self.serial.is_open:
                self.serial.write(b"SPEED:0\n")
                self.serial.write(b"ALARM:0\n")
        except Exception:
            pass
        if self.vehicle:
            self.vehicle.force_stop_requested = True
        self._try_reconnect()

    def send_command(self, command):
        if not self.connected or not self.serial:
            return
        with self._write_lock:
            try:
                self.serial.write(f"{command}\n".encode())
            except Exception as e:
                self._handle_disconnect(str(e))

    def send_signal(self, signal, state):
        if not self.connected or not self.serial:
            return
        with self._write_lock:
            try:
                self.serial.write(f"{signal}:{state}\n".encode())
            except Exception as e:
                self._handle_disconnect(str(e))

    def _try_reconnect(self, delay=1.0):
        if self._reconnecting:
            return
        self._reconnecting = True

        def _worker():
            i = 0
            while not self.connected:
                i += 1
                if self.log_callback:
                    self.log_callback(f"Спроба перепідключення Arduino ({i})...")
                self.connect()
                if self.connected:
                    self._last_speed = -1
                    self._reconnecting = False
                    return
                time.sleep(delay)
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

    def close(self):
        for signal in ['LEFT', 'RIGHT', 'EMERGENCY', 'BRAKE']:
            self.send_signal(signal, 0)
        self.send_alarm(False)
        self.send_command("STOP")
        time.sleep(0.1)
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
