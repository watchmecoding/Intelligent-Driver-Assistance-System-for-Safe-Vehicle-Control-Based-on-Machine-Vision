# config.py
from collections import deque

# Максимальна швидкість
MAX_SPEED_KMH = 120

# Порогові значення для детекції
EAR_THRESHOLD = 0.2
EAR_WIDE_OPEN = 0.50
MAR_THRESHOLD = 0.4
STOP_TIME = 4.0
HEAD_TURN_TIME = 2.0
HEAD_TURN_ANGLE = 15

PITCH_DOWN_THRESHOLD = 50.0
PITCH_UP_THRESHOLD   = 40.0
EMERGENCY_BRAKE_DURATION = 5.0

# Жести руками
PINCH_MIN  = 0.02
PINCH_STOP = 0.05
PINCH_MAX  = 0.20

# Регульована затримка після peace sign
PEACE_COOLDOWN = 2.0
# Буфер
SPEED_BUFFER_SIZE = 5
# Ліміт позіхань
MAX_ALLOWED_YAWNS = 5

# UI кольори
BG_COLOR = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT_COLOR = "#0f3460"
TEXT_COLOR = "#e8e8e8"
SUCCESS_COLOR = "#06d6a0"
WARNING_COLOR = "#f0ce23"
DANGER_COLOR = "#ef476f"

# Arduino
ARDUINO_PORT = "COM9"
BAUD_RATE = 9600

# PostgreSQL
DB_HOST     = "localhost"
DB_PORT     = 5432
DB_NAME     = "driver_assistance_system_db"
DB_USER     = "postgres"
DB_PASSWORD = "123"

