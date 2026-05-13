# ui_manager.py
import tkinter as tk
from tkinter import ttk, Label, Frame
from config import *


class UIManager:
    def __init__(self, window):
        self.window = window
        self.setup_window()
        self.create_widgets()
        self.blink_state      = False
        self.settings_callback     = None
        self.stats_callback    = None

    def setup_window(self):
        self.window.title("Інтелектуальна система асистування водію в безпечному керуванні автотранспортним засобом на основі технічного зору")
        self.window.configure(bg=BG_COLOR)
        self.window.state('zoomed')

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.create_button_styles()

    def create_button_styles(self):
        self.style.configure("Start.TButton",
                             font=("Segoe UI", 13, "bold"),
                             foreground="white",
                             background=SUCCESS_COLOR,
                             borderwidth=0, focuscolor='none', relief="flat")
        self.style.map("Start.TButton",
                       background=[('active', '#05b485')])

        self.style.configure("Stop.TButton",
                             font=("Segoe UI", 13, "bold"),
                             foreground="white",
                             background=DANGER_COLOR,
                             borderwidth=0, focuscolor='none', relief="flat")
        self.style.map("Stop.TButton",
                       background=[('active', '#d4405d')])

        self.style.configure("Exit.TButton",
                             font=("Segoe UI", 13, "bold"),
                             foreground="white",
                             background="#555555",
                             borderwidth=0, focuscolor='none', relief="flat")
        self.style.map("Exit.TButton",
                       background=[('active', '#444444')])

        self.style.configure("Settings.TButton",
                             font=("Segoe UI", 13, "bold"),
                             foreground="white",
                             background=ACCENT_COLOR,
                             borderwidth=0, focuscolor='none', relief="flat")
        self.style.map("Settings.TButton",
                       background=[('active', '#0d2a50')])
        
        self.style.configure("Stats.TButton",
                            font=("Segoe UI", 13, "bold"),
                            foreground="white",
                            background="#2d6a4f",
                            borderwidth=0, focuscolor='none', relief="flat")
        self.style.map("Stats.TButton",
                    background=[('active', '#245a42')])

    def create_widgets(self):
        header_frame = Frame(self.window, bg=ACCENT_COLOR, height=70)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        header_frame.pack_propagate(False)

        Label(header_frame, text="Інтелектуальна система асистування водію в безпечному керуванні автотранспортним засобом на основі технічного зору",
              font=("Segoe UI", 18, "bold"), bg=ACCENT_COLOR,
              fg=TEXT_COLOR).pack(pady=15)

        main_container = Frame(self.window, bg=BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        left_panel = Frame(main_container, bg=PANEL_BG, relief=tk.RIDGE, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        Label(left_panel, text="Камера Водія", font=("Segoe UI", 12, "bold"),
              bg=PANEL_BG, fg=TEXT_COLOR).pack(pady=5)

        self.video_label = Label(left_panel, bg="#000000")
        self.video_label.pack(pady=10, padx=10)

        self.create_signal_indicators(left_panel)
        self.create_buttons(left_panel)
        self.create_right_panel(main_container)

    def create_signal_indicators(self, parent):
        signals_frame = Frame(parent, bg=PANEL_BG, height=70)
        signals_frame.pack(fill=tk.X, padx=15, pady=(5, 10))
        signals_frame.pack_propagate(False)

        signals_center = Frame(signals_frame, bg=PANEL_BG)
        signals_center.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.left_turn_label = Label(signals_center, text="◀",
                                     font=("Arial", 36, "bold"),
                                     bg=PANEL_BG, fg="#444444")
        self.left_turn_label.pack(side=tk.LEFT, padx=15)

        self.brake_label = Label(signals_center, text="STOP",
                                 font=("Arial", 30, "bold"),
                                 bg=PANEL_BG, fg="#444444")
        self.brake_label.pack(side=tk.LEFT, padx=15)

        self.emergency_label = Label(signals_center, text="<!>",
                                     font=("Arial", 30, "bold"),
                                     bg=PANEL_BG, fg="#444444")
        self.emergency_label.pack(side=tk.LEFT, padx=15)

        self.right_turn_label = Label(signals_center, text="▶",
                                      font=("Arial", 36, "bold"),
                                      bg=PANEL_BG, fg="#444444")
        self.right_turn_label.pack(side=tk.LEFT, padx=15)

    def create_buttons(self, parent):
        button_frame = Frame(parent, bg=PANEL_BG, height=80)
        button_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        button_frame.pack_propagate(False)

        button_container = Frame(button_frame, bg=PANEL_BG)
        button_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.start_button_text = tk.StringVar(value="Запустити")

        self.start_button = ttk.Button(button_container,
                                       textvariable=self.start_button_text,
                                       style="Start.TButton", width=15)
        self.start_button.pack(side=tk.LEFT, padx=5, ipady=10)

        self.exit_button = ttk.Button(button_container, text="Вихід",
                                      style="Exit.TButton", width=12)
        self.exit_button.pack(side=tk.LEFT, padx=5, ipady=10)

        self.settings_button = ttk.Button(button_container,
                                          text="Налаштування",
                                          style="Settings.TButton", width=20,
                                          command=self._on_settings)
        self.settings_button.pack(side=tk.LEFT, padx=5, ipady=10)

    def _on_settings(self):
        if self.settings_callback:
            self.settings_callback()
    
    def _on_stats(self):
        if self.stats_callback:
            self.stats_callback()

    def create_right_panel(self, parent):
        right_panel = Frame(parent, bg=PANEL_BG, width=350,
                            relief=tk.RIDGE, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)

        status_section = Frame(right_panel, bg=PANEL_BG)
        status_section.pack(fill=tk.X, pady=15, padx=15)

        Label(status_section, text="Статус системи",
              font=("Segoe UI", 14, "bold"), bg=PANEL_BG,
              fg=TEXT_COLOR).pack(anchor=tk.W)

        self.status_label = Label(status_section,
                                  text="Очікування запуску...",
                                  font=("Segoe UI", 11), bg=PANEL_BG,
                                  fg=WARNING_COLOR, wraplength=310,
                                  justify=tk.LEFT)
        self.status_label.pack(anchor=tk.W, pady=(8, 0))

        ttk.Separator(right_panel, orient='horizontal').pack(
            fill=tk.X, pady=10, padx=15)

        servo_section = Frame(right_panel, bg=PANEL_BG)
        servo_section.pack(fill=tk.X, pady=10, padx=15)

        Label(servo_section, text="Керування швидкістю",
              font=("Segoe UI", 14, "bold"), bg=PANEL_BG,
              fg=TEXT_COLOR).pack(anchor=tk.W)

        self.servo_label = Label(servo_section, text="Швидкість: 0 Км/Год",
                                 font=("Segoe UI", 12, "bold"),
                                 bg=PANEL_BG, fg=TEXT_COLOR)
        self.servo_label.pack(anchor=tk.W, pady=(8, 5))

        self.speed_progress = ttk.Progressbar(servo_section,
                                              orient=tk.HORIZONTAL,
                                              length=300, mode='determinate')
        self.speed_progress.pack(anchor=tk.W, pady=(0, 5))

        ttk.Separator(right_panel, orient='horizontal').pack(
            fill=tk.X, pady=10, padx=15)

        warning_section = Frame(right_panel, bg=PANEL_BG)
        warning_section.pack(fill=tk.X, pady=10, padx=15)

        Label(warning_section, text="Попередження",
              font=("Segoe UI", 14, "bold"), bg=PANEL_BG,
              fg=TEXT_COLOR).pack(anchor=tk.W)

        self.warning_label = Label(warning_section,
                                   text="Немає попереджень",
                                   font=("Segoe UI", 10), bg=PANEL_BG,
                                   fg=SUCCESS_COLOR, wraplength=310,
                                   justify=tk.LEFT)
        self.warning_label.pack(anchor=tk.W, pady=(8, 0))

        ttk.Separator(right_panel, orient='horizontal').pack(
            fill=tk.X, pady=10, padx=15)

        metrics_section = Frame(right_panel, bg=PANEL_BG)
        metrics_section.pack(fill=tk.X, pady=10, padx=15)

        Label(metrics_section, text="Статистика",
              font=("Segoe UI", 14, "bold"), bg=PANEL_BG,
              fg=TEXT_COLOR).pack(anchor=tk.W)

        self.emergency_count_label = Label(metrics_section,
                                    text="Аварійних зупинок: 0",
                                    font=("Segoe UI", 10), bg=PANEL_BG,
                                    fg=TEXT_COLOR)
        self.emergency_count_label.pack(anchor=tk.W, pady=3)

        self.face_missing_count_label = Label(metrics_section,
                                            text="Зникнень обличчя: 0",
                                            font=("Segoe UI", 10), bg=PANEL_BG,
                                            fg=TEXT_COLOR)
        self.face_missing_count_label.pack(anchor=tk.W, pady=3)

        self.yawn_label = Label(metrics_section,
                                text="Позіхання: 0 (підряд: 0)",
                                font=("Segoe UI", 10), bg=PANEL_BG,
                                fg=TEXT_COLOR)
        self.yawn_label.pack(anchor=tk.W, pady=3)

        self.yawn_limit_label = Label(metrics_section,
                                      text="Обмеження: НЕМАЄ",
                                      font=("Segoe UI", 10, "bold"),
                                      bg=PANEL_BG, fg=SUCCESS_COLOR)
        self.yawn_limit_label.pack(anchor=tk.W, pady=3)

        ttk.Separator(right_panel, orient='horizontal').pack(
            fill=tk.X, pady=10, padx=15)

        head_section = Frame(right_panel, bg=PANEL_BG)
        head_section.pack(fill=tk.X, pady=10, padx=15)

        Label(head_section, text="Положення голови",
              font=("Segoe UI", 14, "bold"), bg=PANEL_BG,
              fg=TEXT_COLOR).pack(anchor=tk.W)

        self.head_status_label = Label(head_section,
                                       text="Напрямок: Прямо",
                                       font=("Segoe UI", 10), bg=PANEL_BG,
                                       fg=TEXT_COLOR, wraplength=310,
                                       justify=tk.LEFT)
        self.head_status_label.pack(anchor=tk.W, pady=(8, 0))

        ttk.Separator(right_panel, orient='horizontal').pack(
            fill=tk.X, pady=10, padx=15)

        gesture_section = Frame(right_panel, bg=PANEL_BG)
        gesture_section.pack(fill=tk.X, pady=10, padx=15)

        Label(gesture_section, text="Жести",
              font=("Segoe UI", 14, "bold"), bg=PANEL_BG,
              fg=TEXT_COLOR).pack(anchor=tk.W)

        self.gesture_label = Label(gesture_section,
                                   text="Розведіть пальці для руху",
                                   font=("Segoe UI", 10), bg=PANEL_BG,
                                   fg=TEXT_COLOR, wraplength=310,
                                   justify=tk.LEFT)
        self.gesture_label.pack(anchor=tk.W, pady=(8, 0))

    def update_speed_display(self, speed_percent, max_speed_kmh=120):
        kmh = int((speed_percent / 100) * max_speed_kmh)
        self.servo_label.config(text=f"Швидкість: {kmh} км/год")
        self.speed_progress['value'] = speed_percent

        if speed_percent == 0:
            self.servo_label.config(fg=DANGER_COLOR)
        elif speed_percent < 50:
            self.servo_label.config(fg=WARNING_COLOR)
        else:
            self.servo_label.config(fg=SUCCESS_COLOR)

    def update_signals(self, left, right, emergency, brake):
        self.left_turn_label.config(
            fg=WARNING_COLOR if left else "#444444")
        self.right_turn_label.config(
            fg=WARNING_COLOR if right else "#444444")

        self.emergency_label.config(
            fg=WARNING_COLOR if emergency else "#444444")

        self.brake_label.config(
            fg=DANGER_COLOR if brake else "#444444")

    def update_signals_emergency(self, blink_state, brake):
        orange = WARNING_COLOR
        emrg   = DANGER_COLOR
        dim    = "#444444"

        self.left_turn_label.config(fg=orange if blink_state else dim)
        self.right_turn_label.config(fg=orange if blink_state else dim)

        self.emergency_label.config(fg=emrg if blink_state else dim)

        self.brake_label.config(fg=DANGER_COLOR if brake else dim)
