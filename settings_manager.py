# settings_manager.py

class SettingsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._set_defaults()

    def _set_defaults(self):
        self.using_defaults       = True
        # Загальні
        self.max_speed_kmh        = 120
        # Сонливість
        self.ear_threshold        = 0.25
        self.mar_threshold        = 0.6   
        self.stop_time            = 4.0
        self.emergency_brake_dur  = 5.0
        self.peace_cooldown       = 2.0
        self.enable_drowsiness    = True
        # Нахил голови
        self.pitch_down_threshold = 50.0
        self.pitch_up_threshold   = 40.0
        self.tilt_time            = 2.0
        self.enable_tilt          = True
        # Поворотники
        self.head_turn_angle_left  = 15.0
        self.head_turn_angle_right = 15.0
        self.head_turn_time        = 2.0
        self.head_turn_off_time    = 2.0
        self.enable_turn_signals   = True
        # Позіхання
        self.max_allowed_yawns    = 5
        self.enable_yawns         = True
        # Зникнення обличчя
        self.face_missing_time    = 3.0
        self.enable_face_missing  = True

    def _apply_dict(self, data):
        float_fields = [
            'ear_threshold', 'mar_threshold',
            'stop_time', 'emergency_brake_dur', 'peace_cooldown',
            'pitch_down_threshold', 'pitch_up_threshold', 'tilt_time',
            'head_turn_angle_left', 'head_turn_angle_right',
            'head_turn_time', 'head_turn_off_time','face_missing_time',
        ]
        int_fields  = ['max_allowed_yawns', 'max_speed_kmh']
        bool_fields = [
            'enable_drowsiness', 'enable_tilt',
            'enable_turn_signals', 'enable_yawns', 'enable_face_missing',
        ]
        for f in float_fields:
            if data.get(f) is not None:
                setattr(self, f, float(data[f]))
        for f in int_fields:
            if data.get(f) is not None:
                setattr(self, f, int(data[f]))
        for f in bool_fields:
            if data.get(f) is not None:
                setattr(self, f, bool(data[f]))

    def load_from_db(self, db_logger):
        data = db_logger.load_settings()
        if not data:
            print("Налаштувань в БД нема — defaults")
            return
        self._apply_dict(data)
        self.using_defaults = False
        print("Налаштування завантажено (профіль користувача)")

    def reset_to_defaults(self, db_logger):
        db_logger.reset_settings_to_default()
        data = db_logger.load_default_settings()
        if data:
            self._apply_dict(data)
        self.using_defaults = True
        print("Налаштування скинуто до заводських")

    def save_to_db(self, db_logger):
        db_logger.save_settings(self)
        self.using_defaults = False

    def apply_to_vehicle(self, vehicle):
        vehicle.max_allowed_yawns = self.max_allowed_yawns
        if not self.enable_yawns and vehicle.yawn_speed_limit:
            vehicle.yawn_speed_limit  = False
            vehicle.consecutive_yawns = 0
            vehicle.speed_buffer.clear()
