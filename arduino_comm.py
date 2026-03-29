# arduino_comm.py
import serial
import serial.tools.list_ports
import time
from config import *


class ArduinoController:
    def __init__(self, log_callback=None):
        self.serial       = None
        self.connected    = False
        self.log_callback = log_callback
        self._last_speed  = -1
        self.connect()

    def connect(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if any(k in port.description
                   for k in ('Arduino', 'CH340', 'USB')):
                try:
                    self.serial = serial.Serial(
                        port.device, 9600, timeout=1)
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

    def send_command(self, command):
        if self.connected and self.serial:
            try:
                self.serial.write(f"{command}\n".encode())
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"Помилка команди: {e}")

    def send_signal(self, signal, state):
        if self.connected and self.serial:
            try:
                self.serial.write(f"{signal}:{state}\n".encode())
            except Exception as e:
                if self.log_callback:
                    self.log_callback(
                        f"Помилка сигналу {signal}: {e}")

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
