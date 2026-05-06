# settings_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from config import (BG_COLOR, PANEL_BG, ACCENT_COLOR,
                    TEXT_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR)


class SettingsWindow:
    def __init__(self, parent, settings_manager, db_logger,
                 vehicle=None, on_apply=None):
        self.settings = settings_manager
        self.db       = db_logger
        self.vehicle  = vehicle
        self.on_apply = on_apply

        self.win = tk.Toplevel(parent)
        self.win.title("Налаштування системи")
        self.win.configure(bg=BG_COLOR)
        self.win.resizable(False, False)
        self.win.grab_set()

        tk.Label(self.win, text="Налаштування",
                 font=("Segoe UI", 16, "bold"),
                 bg=ACCENT_COLOR, fg=TEXT_COLOR,
                 pady=12).pack(fill=tk.X)

        outer = tk.Frame(self.win, bg=BG_COLOR)
        outer.pack(fill=tk.BOTH, expand=True)

        canvas    = tk.Canvas(outer, bg=BG_COLOR, bd=0,
                              highlightthickness=0, width=520, height=500)
        scrollbar = ttk.Scrollbar(outer, orient="vertical",
                                  command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.body = tk.Frame(canvas, bg=BG_COLOR)
        win_id = canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>",
                       lambda e: canvas.configure(
                           scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        self.win.bind("<MouseWheel>",
                      lambda e: canvas.yview_scroll(
                          int(-1 * (e.delta / 120)), "units"))

        self._vars = {}
        self._build_body()

        btn_frame = tk.Frame(self.win, bg=PANEL_BG, pady=10)
        btn_frame.pack(fill=tk.X)

        style = ttk.Style()
        for name, bg, active in [
            ("Cancel.TButton",  "#555555", "#444444"),
            ("Reset.TButton",   "#32159b", "#2a1868"),
            ("Apply2.TButton",  "#01966e", "#026b4f"),
        ]:
            style.configure(name, font=("Segoe UI", 11),
                            foreground="white", background=bg, relief="flat")
            style.map(name, background=[('active', active)])

        ttk.Button(btn_frame, text="Скасувати",
                   style="Cancel.TButton", width=14,
                   command=self.win.destroy).pack(
                       side=tk.LEFT, padx=12, ipady=8)
        ttk.Button(btn_frame, text="Скинути",
                   style="Reset.TButton", width=14,
                   command=self._reset).pack(
                       side=tk.LEFT, padx=4, ipady=8)
        ttk.Button(btn_frame, text="Прийняти",
                   style="Apply2.TButton", width=14,
                   command=self._apply).pack(
                       side=tk.RIGHT, padx=12, ipady=8)

    def _build_body(self):
        s = self.settings

        self._section("Загальні параметри")
        self._slider("max_speed_kmh",
                     "Максимальна швидкість ТЗ (км/год)",
                     30, 250, s.max_speed_kmh,
                     resolution=5, is_int=True)
        self._slider("emergency_brake_dur",
                     "Тривалість аварійного гальмування (сек)",
                     1.0, 10.0, s.emergency_brake_dur, resolution=0.5)
        self._slider("peace_cooldown",
                     "Час затримки після відміни аварійної сигналізації (сек)",
                     0.5, 10.0, s.peace_cooldown, resolution=0.5)

        self._section("Контроль очей")
        self._toggle("enable_drowsiness",
                     "Увімкнути контроль очей", s.enable_drowsiness)
        self._slider("ear_threshold",
                     "EAR поріг закритих очей (0.10 – 0.40)",
                     0.10, 0.40, s.ear_threshold, resolution=0.01)
        self._slider("stop_time",
                     "Час закритих очей до аварійної зупинки (сек)",
                     1.0, 10.0, s.stop_time, resolution=0.5)

        self._section("Контроль нахилу голови")
        self._toggle("enable_tilt",
                     "Увімкнути контроль нахилу голови", s.enable_tilt)
        self._slider("pitch_down_threshold",
                     "Пороговий кут нахилу вгору для аварійної зупинки (градуси)",
                     0, 100, s.pitch_down_threshold)
        self._slider("pitch_up_threshold",
                     "Пороговий кут нахилу вниз для аварійної зупинки (градуси)",
                     0, 100, s.pitch_up_threshold)
        self._slider("tilt_time",
                     "Час нахилу голови до аварійної зупинки (сек)",
                     0.5, 10.0, s.tilt_time, resolution=0.5)

        self._section("Контроль повороту голови (поворотники)")
        self._toggle("enable_turn_signals",
                     "Увімкнути автоматичні поворотники при повороті голови", s.enable_turn_signals)
        self._slider("head_turn_angle_left",
                     "Пороговий кут для лівого поворотника (градуси)",
                     0, 50, s.head_turn_angle_left)
        self._slider("head_turn_angle_right",
                     "Пороговий кут для правого поворотника (градуси)",
                     0, 50, s.head_turn_angle_right)
        self._slider("head_turn_time",
                     "Час повороту для ввімкнення поворотника (сек)",
                     0.5, 5.0, s.head_turn_time, resolution=0.5)
        self._slider("head_turn_off_time",
                     "Час погляду прямо для вимкнення поворотника (сек)",
                     0.5, 5.0, s.head_turn_off_time, resolution=0.5)

        self._section("Контроль позіхань")
        self._toggle("enable_yawns",
                     "Увімкнути контроль позіхань", s.enable_yawns)
        self._slider("max_allowed_yawns",
                     "Ліміт позіхань підряд",
                     3, 15, s.max_allowed_yawns,
                     resolution=1, is_int=True)
        self._slider("mar_threshold",
             "MAR поріг позіхання (0.30 – 0.90)",
             0.30, 0.90, s.mar_threshold, resolution=0.01)
        self._section("Контроль зникнення обличчя")
        self._toggle("enable_face_missing",
                    "Увімкнути контроль зникнення обличчя", s.enable_face_missing)
        self._slider("face_missing_time",
                    "Час відсутності обличчя до аварійної зупинки (сек)",
                    1.0, 10.0, s.face_missing_time, resolution=0.5)

    def _section(self, title):
        tk.Frame(self.body, bg="#2a2a4e", height=2).pack(
            fill=tk.X, padx=20, pady=(15, 2))
        tk.Label(self.body, text=title,
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_COLOR, fg=WARNING_COLOR).pack(
                     anchor=tk.W, padx=25, pady=(4, 0))

    def _toggle(self, key, label, default):
        var = tk.BooleanVar(value=default)
        self._vars[key] = var
        row = tk.Frame(self.body, bg=BG_COLOR)
        row.pack(fill=tk.X, padx=25, pady=4)
        tk.Checkbutton(row, text=label, variable=var,
                       font=("Segoe UI", 10),
                       bg=BG_COLOR, fg=TEXT_COLOR,
                       selectcolor=ACCENT_COLOR,
                       activebackground=BG_COLOR,
                       activeforeground=TEXT_COLOR).pack(anchor=tk.W)

    def _slider(self, key, label, from_, to,
                default, resolution=1.0, is_int=False):
        var = tk.DoubleVar(value=default)
        self._vars[key] = (var, is_int)

        row = tk.Frame(self.body, bg=BG_COLOR)
        row.pack(fill=tk.X, padx=25, pady=6)
        top = tk.Frame(row, bg=BG_COLOR)
        top.pack(fill=tk.X)

        tk.Label(top, text=label, font=("Segoe UI", 10),
                 bg=BG_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)

        val_lbl = tk.Label(top, text=self._fmt(default, is_int),
                           font=("Segoe UI", 10, "bold"),
                           bg=BG_COLOR, fg=SUCCESS_COLOR, width=6)
        val_lbl.pack(side=tk.RIGHT)

        tk.Scale(row, variable=var,
                 from_=from_, to=to, resolution=resolution,
                 orient=tk.HORIZONTAL, length=420, showvalue=False,
                 bg=BG_COLOR, fg=TEXT_COLOR,
                 troughcolor=ACCENT_COLOR, highlightthickness=0,
                 command=lambda v, lbl=val_lbl, ii=is_int:
                     lbl.config(text=self._fmt(float(v), ii))
                 ).pack(fill=tk.X)

    @staticmethod
    def _fmt(v, is_int):
        return str(int(v)) if is_int else f"{v:.2f}"

    def _update_sliders_from_settings(self):
        s = self.settings
        mapping = {
            'max_speed_kmh':         s.max_speed_kmh,
            'ear_threshold':         s.ear_threshold,
            'stop_time':             s.stop_time,
            'emergency_brake_dur':   s.emergency_brake_dur,
            'peace_cooldown':        s.peace_cooldown,
            'pitch_down_threshold':  s.pitch_down_threshold,
            'pitch_up_threshold':    s.pitch_up_threshold,
            'tilt_time':             s.tilt_time,
            'head_turn_angle_left':  s.head_turn_angle_left,
            'head_turn_angle_right': s.head_turn_angle_right,
            'head_turn_time':        s.head_turn_time,
            'head_turn_off_time':    s.head_turn_off_time,
            'max_allowed_yawns':     s.max_allowed_yawns,
            'mar_threshold':         s.mar_threshold,
            'face_missing_time':     s.face_missing_time,
        }
        toggles = {
            'enable_drowsiness':   s.enable_drowsiness,
            'enable_tilt':         s.enable_tilt,
            'enable_turn_signals': s.enable_turn_signals,
            'enable_yawns':        s.enable_yawns,
            'enable_face_missing': s.enable_face_missing,
        }
        for key, val in mapping.items():
            item = self._vars.get(key)
            if item:
                item[0].set(val)
        for key, val in toggles.items():
            var = self._vars.get(key)
            if isinstance(var, tk.BooleanVar):
                var.set(val)

    def _reset(self):
        if not messagebox.askyesno(
                "Скинути налаштування",
                "Скинути всі налаштування до заводських?",
                parent=self.win):
            return
        self.settings.reset_to_defaults(self.db)
        self._update_sliders_from_settings()
        if self.vehicle:
            self.settings.apply_to_vehicle(self.vehicle)

    def _apply(self):
        s = self.settings
        for key, item in self._vars.items():
            if isinstance(item, tk.BooleanVar):
                setattr(s, key, item.get())
            else:
                var, is_int = item
                val = var.get()
                setattr(s, key, int(val) if is_int else float(val))
        s.save_to_db(self.db)
        if self.vehicle:
            s.apply_to_vehicle(self.vehicle)
        if self.on_apply:
            self.on_apply()
        self.win.destroy()
