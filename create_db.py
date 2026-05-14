# create_db.py
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import DBHOST, DBPORT, DBNAME, DBUSER, DBPASSWORD

conn = psycopg2.connect(host=DBHOST, port=DBPORT, database="postgres", user=DBUSER, password=DBPASSWORD)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
try:
    cur.execute("CREATE DATABASE driver_assistance_system_db")
    print("БД створена!")
except Exception as e:
    print(f"БД вже існує: {e}")
cur.close()
conn.close()

conn = psycopg2.connect(host=DBHOST, port=DBPORT, database=DBNAME, user=DBUSER, password=DBPASSWORD)
cur = conn.cursor()

# Водії
cur.execute("""
CREATE TABLE IF NOT EXISTS drivers (
    id             SERIAL PRIMARY KEY,
    first_name     VARCHAR(80)  NOT NULL,
    last_name      VARCHAR(80)  NOT NULL,
    license_number VARCHAR(50)  UNIQUE,
    birth_date     DATE,
    phone          VARCHAR(30),
    face_embedding FLOAT[]
)
""")

# Транспортні засоби
cur.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    id            SERIAL PRIMARY KEY,
    license_plate VARCHAR(20) UNIQUE NOT NULL,
    make          VARCHAR(50),
    model         VARCHAR(50),
    year          INTEGER,
    owner_id      INTEGER REFERENCES drivers(id)
)
""")

# Профілі налаштувань
cur.execute("""
CREATE TABLE IF NOT EXISTS settings_profiles (
    id          INTEGER PRIMARY KEY,
    driver_id   INTEGER REFERENCES drivers(id),
    name        VARCHAR(50) NOT NULL,
    description TEXT
)
""")

# Сесії
cur.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id                 SERIAL PRIMARY KEY,
    driver_id          INTEGER REFERENCES drivers(id),
    vehicle_id         INTEGER REFERENCES vehicles(id),
    settings_profile_id INTEGER REFERENCES settings_profiles(id),
    started_at         TIMESTAMP DEFAULT NOW(),
    ended_at           TIMESTAMP,
    total_yawns        INTEGER DEFAULT 0,
    emergency_count    INTEGER DEFAULT 0,
    face_missing_count INTEGER DEFAULT 0,
    notes              TEXT
)
""")


# Загальні налаштування
cur.execute("""
CREATE TABLE IF NOT EXISTS settings_general (
    profile_id    INTEGER PRIMARY KEY REFERENCES settings_profiles(id),
    max_speed_kmh INTEGER NOT NULL DEFAULT 120,
    description   TEXT    DEFAULT 'Максимальна швидкість ТЗ у км/год.',
    updated_at    TIMESTAMP DEFAULT NOW()
)
""")

# Налаштування: Сонливість
cur.execute("""
CREATE TABLE IF NOT EXISTS settings_drowsiness (
    profile_id          INTEGER PRIMARY KEY REFERENCES settings_profiles(id),
    ear_threshold       FLOAT   NOT NULL DEFAULT 0.25,
    mar_threshold       FLOAT   NOT NULL DEFAULT 0.6,
    stop_time           FLOAT   NOT NULL DEFAULT 4.0,
    emergency_brake_dur FLOAT   NOT NULL DEFAULT 5.0,
    peace_cooldown      FLOAT   NOT NULL DEFAULT 2.0,
    enable_drowsiness   BOOLEAN NOT NULL DEFAULT TRUE,
    description         TEXT    DEFAULT 'EAR/MAR поріг, затримка до аварійки, гальмування, cooldown.',
    updated_at          TIMESTAMP DEFAULT NOW()
)
""")

# Налаштування: Нахил голови
cur.execute("""
CREATE TABLE IF NOT EXISTS settings_head_tilt (
    profile_id           INTEGER PRIMARY KEY REFERENCES settings_profiles(id),
    pitch_down_threshold FLOAT   NOT NULL DEFAULT 50.0,
    pitch_up_threshold   FLOAT   NOT NULL DEFAULT 40.0,
    tilt_time            FLOAT   NOT NULL DEFAULT 2.0,
    enable_tilt          BOOLEAN NOT NULL DEFAULT TRUE,
    description          TEXT    DEFAULT 'Нахил вниз/вгору: кути та затримка до аварійки.',
    updated_at           TIMESTAMP DEFAULT NOW()
)
""")

# Налаштування: Поворотники
cur.execute("""
CREATE TABLE IF NOT EXISTS settings_turn_signals (
    profile_id            INTEGER PRIMARY KEY REFERENCES settings_profiles(id),
    head_turn_angle_left  FLOAT   NOT NULL DEFAULT 15.0,
    head_turn_angle_right FLOAT   NOT NULL DEFAULT 15.0,
    head_turn_time        FLOAT   NOT NULL DEFAULT 2.0,
    head_turn_off_time    FLOAT   NOT NULL DEFAULT 2.0,
    enable_turn_signals   BOOLEAN NOT NULL DEFAULT TRUE,
    description           TEXT    DEFAULT 'Автоповоротники: кути та затримки.',
    updated_at            TIMESTAMP DEFAULT NOW()
)
""")

# Налаштування: Позіхання
cur.execute("""
CREATE TABLE IF NOT EXISTS settings_yawns (
    profile_id        INTEGER PRIMARY KEY REFERENCES settings_profiles(id),
    max_allowed_yawns INTEGER NOT NULL DEFAULT 5,
    enable_yawns      BOOLEAN NOT NULL DEFAULT TRUE,
    description       TEXT    DEFAULT 'Ліміт позіхань підряд до обмеження швидкості.',
    updated_at        TIMESTAMP DEFAULT NOW()
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings_face_missing (
    profile_id          INTEGER PRIMARY KEY REFERENCES settings_profiles(id),
    face_missing_time   FLOAT   NOT NULL DEFAULT 3.0,
    enable_face_missing BOOLEAN NOT NULL DEFAULT TRUE,
    description         TEXT    DEFAULT 'Час відсутності обличчя до аварійки.',
    updated_at          TIMESTAMP DEFAULT NOW()
)
""")

# Тестові дані: Водій
cur.execute("""
INSERT INTO drivers (first_name, last_name, license_number, birth_date, phone)
VALUES ('Віталій', 'Волнушкін', 'АВ123456', '1998-03-20', '+38(099)123-45-67')
ON CONFLICT (license_number) DO NOTHING
RETURNING id
""")
row = cur.fetchone()
driver_id = row[0] if row else None

# Якщо вже існує - отримуємо id
if driver_id is None:
    cur.execute("SELECT id FROM drivers WHERE license_number = 'АВ123456'")
    driver_id = cur.fetchone()[0]

# Тестові дані: Транспортний засіб
cur.execute("""
INSERT INTO vehicles (license_plate, make, model, year, owner_id)
VALUES ('АА1234ВВ', 'Mitsubishi', 'Colt', 2014, %s)
ON CONFLICT (license_plate) DO NOTHING
""", (driver_id,))

# Профілі налаштувань
cur.execute("""
INSERT INTO settings_profiles (id, driver_id, name, description) VALUES
    (1, %s, 'default', 'Заводські налаштування — не змінювати'),
    (2, %s, 'user',    'Поточні налаштування користувача')
ON CONFLICT (id) DO NOTHING
""", (driver_id, driver_id))

# Початкові рядки для обох профілів
for profile_id in (1, 2):
    for table in ("settings_general", "settings_drowsiness",
                  "settings_head_tilt", "settings_turn_signals", "settings_yawns", "settings_face_missing"):
        cur.execute(f"""
            INSERT INTO {table} (profile_id) VALUES (%s)
            ON CONFLICT (profile_id) DO NOTHING
        """, (profile_id,))

# VIEWs
for view_name, profile_id in [("v_settings", 2), ("v_default_settings", 1)]:
    cur.execute(f"""
    CREATE OR REPLACE VIEW {view_name} AS
    SELECT g.max_speed_kmh,
           d.ear_threshold, d.mar_threshold, d.stop_time, d.emergency_brake_dur,
           d.peace_cooldown, d.enable_drowsiness,
           t.pitch_down_threshold, t.pitch_up_threshold,
           t.tilt_time, t.enable_tilt,
           s.head_turn_angle_left, s.head_turn_angle_right,
           s.head_turn_time, s.head_turn_off_time, s.enable_turn_signals,
           y.max_allowed_yawns, y.enable_yawns,
           f.face_missing_time, f.enable_face_missing
    FROM   settings_general      g
    JOIN   settings_drowsiness   d ON d.profile_id = g.profile_id
    JOIN   settings_head_tilt    t ON t.profile_id = g.profile_id
    JOIN   settings_turn_signals s ON s.profile_id = g.profile_id
    JOIN   settings_yawns        y ON y.profile_id = g.profile_id
    JOIN   settings_face_missing f ON f.profile_id = g.profile_id
    WHERE  g.profile_id = {profile_id}
    """)

conn.commit()
print("Таблиці, дані та VIEW створені!")
cur.close()
conn.close()
