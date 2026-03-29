# vehicle_controller.py
import time
from collections import deque
from config import *
from settings_manager import SettingsManager

class VehicleController:
    def __init__(self, arduino_controller):
        self.arduino   = arduino_controller
        self.settings  = SettingsManager()

        self.emergency_stop_active = False
        self.emergency_signal      = False
        self.emergency_start_time  = 0.0
        self.emergency_start_speed = 0.0

        self.yawn_speed_limit  = False
        self.left_turn_signal  = False
        self.right_turn_signal = False

        self.yawn_times        = 0
        self.consecutive_yawns = 0
        self.max_allowed_yawns = self.settings.max_allowed_yawns
        self.yawns_depleted    = False

        self.eye_closed_start_time  = None
        self.tilt_down_start_time = None
        self.tilt_up_start_time   = None
        self.head_turn_left_start   = None
        self.head_turn_right_start  = None
        self.head_straight_start    = None
        self.last_peace_time        = 0
        self.last_gesture_time      = 0

        self.manual_speed   = 0
        self.prev_speed     = 0
        self.speed_buffer   = deque(maxlen=SPEED_BUFFER_SIZE)
        self.brake_cooldown = 0

        self.yawn_frame_count = 0
        self.is_yawning       = False

    # Поворот голови
    def update_head_position(self, yaw, current_time):
        s = self.settings

        if not s.enable_turn_signals:
            self.left_turn_signal      = False
            self.right_turn_signal     = False
            self.head_turn_left_start  = None
            self.head_turn_right_start = None
            return "disabled", 0

        angle_left  = s.head_turn_angle_left
        angle_right = s.head_turn_angle_right
        on_time     = s.head_turn_time
        off_time    = s.head_turn_off_time

        if yaw < -angle_left:
            if self.head_turn_left_start is None:
                self.head_turn_left_start = current_time
            self.head_turn_right_start = None
            self.head_straight_start   = None
            elapsed = current_time - self.head_turn_left_start
            if elapsed >= on_time:
                if not self.left_turn_signal:
                    self.left_turn_signal  = True
                    self.right_turn_signal = False
                return "left_on", elapsed
            return "left_waiting", elapsed

        elif yaw > angle_right:
            if self.head_turn_right_start is None:
                self.head_turn_right_start = current_time
            self.head_turn_left_start  = None
            self.head_straight_start   = None
            elapsed = current_time - self.head_turn_right_start
            if elapsed >= on_time:
                if not self.right_turn_signal:
                    self.right_turn_signal = True
                    self.left_turn_signal  = False
                return "right_on", elapsed
            return "right_waiting", elapsed

        else:
            if self.head_straight_start is None:
                self.head_straight_start = current_time
            self.head_turn_left_start  = None
            self.head_turn_right_start = None
            elapsed = current_time - self.head_straight_start
            if (self.left_turn_signal or self.right_turn_signal) and \
            elapsed >= off_time:
                self.left_turn_signal  = False
                self.right_turn_signal = False
                return "straight_off", elapsed
            elif self.left_turn_signal or self.right_turn_signal:
                return "straight_waiting", elapsed
            return "straight", elapsed

    # Сонливість
    def check_drowsiness(self, EAR, current_time):
        s = self.settings
        if not s.enable_drowsiness:
            self.eye_closed_start_time = None
            return "disabled", 0

        if EAR < s.ear_threshold:
            if self.eye_closed_start_time is None:
                self.eye_closed_start_time = current_time
            elapsed = current_time - self.eye_closed_start_time
            if elapsed >= s.stop_time:
                if not self.emergency_stop_active:
                    self.emergency_stop_active = True
                    self.emergency_signal      = True
                    self.emergency_start_time  = time.time()
                    self.emergency_start_speed = self.manual_speed
                    self.arduino.send_alarm(True)
                return "emergency", elapsed
            return "drowsy", elapsed
        else:
            self.eye_closed_start_time = None
            return "awake", 0

    # Нахил голови
    def check_head_tilt(self, pitch, current_time):
        s = self.settings
        if not s.enable_tilt:
            self.tilt_down_start_time = None
            self.tilt_up_start_time   = None
            return "disabled", 0, ""

        going_down = pitch < 0 and abs(pitch) >= s.pitch_down_threshold
        going_up   = pitch > 0 and abs(pitch) >= s.pitch_up_threshold

        if going_down:
            self.tilt_up_start_time = None
            if self.tilt_down_start_time is None:
                self.tilt_down_start_time = current_time
            elapsed   = current_time - self.tilt_down_start_time
            direction = "вниз"

        elif going_up:
            self.tilt_down_start_time = None
            if self.tilt_up_start_time is None:
                self.tilt_up_start_time = current_time
            elapsed   = current_time - self.tilt_up_start_time
            direction = "вгору"

        else:
            self.tilt_down_start_time = None
            self.tilt_up_start_time   = None
            return "tilt_ok", 0, ""

        if elapsed >= s.tilt_time:
            if not self.emergency_stop_active:
                self.emergency_stop_active = True
                self.emergency_signal      = True
                self.emergency_start_time  = current_time
                self.emergency_start_speed = self.manual_speed
                self.arduino.send_alarm(True)
            return "tilt_emergency", elapsed, direction

        return "tilt_warning", elapsed, direction

    # Позіхання
    def check_yawning(self, MAR, enable_yawns=True):
        if MAR > self.settings.mar_threshold:
            self.yawn_frame_count += 1
            if self.yawn_frame_count >= 3:
                if not self.is_yawning:
                    self.yawn_times += 1
                    self.is_yawning  = True

                    if enable_yawns:
                        self.consecutive_yawns += 1
                        if self.consecutive_yawns >= self.max_allowed_yawns \
                        and not self.yawns_depleted:
                            if not self.yawn_speed_limit:
                                self.yawn_speed_limit = True
                                if self.manual_speed > 50:
                                    self.speed_buffer.clear()
                                    for _ in range(SPEED_BUFFER_SIZE):
                                        self.speed_buffer.append(50)
                                    self.manual_speed = 50
                                    self.arduino.send_speed(50)
                            return "limited"
                    return True
        else:
            self.yawn_frame_count = 0
            self.is_yawning       = False
        return False


    # Швидкість
    def set_speed(self, speed_percent, force_stop=False):
        s = self.settings

        if force_stop:
            self.speed_buffer.clear()
            self.manual_speed = 0.0
            self.arduino.send_speed(0)
            return 0

        if self.emergency_stop_active:
            elapsed   = time.time() - self.emergency_start_time
            dur       = s.emergency_brake_dur
            progress  = min(elapsed / dur, 1.0)
            target    = max(0.0, self.emergency_start_speed * (1.0 - progress))
            self.manual_speed = target
            self.arduino.send_speed(target)
            return 0 if target < 5 else round(target)

        if self.yawns_depleted and speed_percent > 50:
            speed_percent = 50
        if self.yawn_speed_limit and speed_percent > 50:
            speed_percent = 50

        self.speed_buffer.append(speed_percent)
        smoothed = sum(self.speed_buffer) / len(self.speed_buffer)

        if self.yawn_speed_limit and smoothed > 50:
            smoothed = 50

        self.manual_speed = smoothed
        self.arduino.send_speed(smoothed)
        return 0 if smoothed < 5 else round(smoothed)

    # Аварійка OFF
    def deactivate_emergency(self):
        self.emergency_stop_active = False
        self.emergency_signal      = False
        self.emergency_start_speed = 0.0
        self.tilt_down_start_time  = None
        self.tilt_up_start_time    = None 
        self.arduino.send_alarm(False)
        self.speed_buffer.clear()
        self.last_peace_time = time.time()

    def can_control_speed(self):
        if self.emergency_stop_active:
            return False
        if time.time() - self.last_peace_time < self.settings.peace_cooldown:
            return False
        return True

    def deactivate_yawn_limit(self):
        if self.yawn_speed_limit:
            self.yawn_speed_limit  = False
            self.consecutive_yawns = 0
            self.max_allowed_yawns -= 1
            if self.max_allowed_yawns <= 0:
                self.yawns_depleted    = True
                self.max_allowed_yawns = 0
            current = self.manual_speed
            self.speed_buffer.clear()
            for _ in range(SPEED_BUFFER_SIZE):
                self.speed_buffer.append(current)
            self.last_peace_time = time.time()
            return True
        return False

    def reset_yawn_limit(self):
        if self.yawns_depleted:
            return
        self.yawn_speed_limit  = False
        self.consecutive_yawns = 0
        self.max_allowed_yawns = max(0, self.max_allowed_yawns - 1)
        if self.max_allowed_yawns <= 0:
            self.yawns_depleted = True
        self.speed_buffer.clear()

    def reset_all_yawn_counters(self):
        self.yawn_times        = 0
        self.consecutive_yawns = 0
        self.yawn_speed_limit  = False
        self.yawn_frame_count  = 0
        self.is_yawning        = False
        self.max_allowed_yawns = self.settings.max_allowed_yawns
        self.yawns_depleted    = False

    def update_brake_signal(self):
        if self.manual_speed <= 0:
            self.prev_speed     = 0
            self.brake_cooldown = 0
            return True

        if self.emergency_stop_active:
            self.prev_speed = self.manual_speed
            return True

        if self.manual_speed < self.prev_speed - 2:
            self.brake_cooldown = 10
            result = True
        elif self.brake_cooldown > 0:
            self.brake_cooldown -= 1
            result = True
        else:
            result = False

        self.prev_speed = self.manual_speed
        return result
