-- ── Профілі налаштувань ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings_profiles (
    id                      SERIAL PRIMARY KEY,
    profile_name            VARCHAR(100) NOT NULL DEFAULT 'Default',
    max_speed_kmh           INTEGER      NOT NULL DEFAULT 60,

    -- Сонливість
    enable_drowsiness       BOOLEAN      NOT NULL DEFAULT TRUE,
    ear_threshold           FLOAT        NOT NULL DEFAULT 0.25,
    stop_time               FLOAT        NOT NULL DEFAULT 2.5,
    emergency_brake_dur     FLOAT        NOT NULL DEFAULT 3.0,

    -- Позіхання
    enable_yawns            BOOLEAN      NOT NULL DEFAULT TRUE,
    mar_threshold           FLOAT        NOT NULL DEFAULT 0.6,
    max_allowed_yawns       INTEGER      NOT NULL DEFAULT 3,

    -- Нахил голови
    enable_tilt             BOOLEAN      NOT NULL DEFAULT TRUE,
    pitch_down_threshold    FLOAT        NOT NULL DEFAULT 20.0,
    pitch_up_threshold      FLOAT        NOT NULL DEFAULT 20.0,
    tilt_time               FLOAT        NOT NULL DEFAULT 2.0,

    -- Поворотники
    enable_turn_signals     BOOLEAN      NOT NULL DEFAULT TRUE,
    head_turn_angle_left    FLOAT        NOT NULL DEFAULT 25.0,
    head_turn_angle_right   FLOAT        NOT NULL DEFAULT 25.0,
    head_turn_time          FLOAT        NOT NULL DEFAULT 1.5,

    created_at              TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── Водії ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drivers (
    id                      SERIAL PRIMARY KEY,
    first_name              VARCHAR(100) NOT NULL,
    last_name               VARCHAR(100) NOT NULL,
    license_number          VARCHAR(50)  NOT NULL UNIQUE,
    date_of_birth           DATE,
    phone                   VARCHAR(20),
    created_at              TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── Транспортні засоби ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicles (
    id                      SERIAL PRIMARY KEY,
    driver_id               INTEGER REFERENCES drivers(id) ON DELETE SET NULL,
    make                    VARCHAR(100) NOT NULL,
    model                   VARCHAR(100) NOT NULL,
    year                    INTEGER,
    license_plate           VARCHAR(20)  NOT NULL UNIQUE,
    vin                     VARCHAR(17),
    created_at              TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── Сесії (поїздки) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id                      SERIAL PRIMARY KEY,
    driver_id               INTEGER REFERENCES drivers(id) ON DELETE SET NULL,
    vehicle_id              INTEGER REFERENCES vehicles(id) ON DELETE SET NULL,
    settings_profile_id     INTEGER REFERENCES settings_profiles(id) ON DELETE SET NULL,
    started_at              TIMESTAMP    NOT NULL DEFAULT NOW(),
    ended_at                TIMESTAMP,
    total_yawns             INTEGER      NOT NULL DEFAULT 0,
    emergency_count         INTEGER      NOT NULL DEFAULT 0,
    face_missing_count      INTEGER      NOT NULL DEFAULT 0,
    notes                   TEXT
);

-- ── Метрики (кожні N кадрів) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS metrics (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    recorded_at             TIMESTAMP    NOT NULL DEFAULT NOW(),
    ear_value               FLOAT,
    mar_value               FLOAT,
    yaw_angle               FLOAT,
    pitch_angle             FLOAT,
    speed                   INTEGER
);

-- ── Події ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    occurred_at             TIMESTAMP    NOT NULL DEFAULT NOW(),
    event_type              VARCHAR(50)  NOT NULL,
    -- 'DROWSY', 'EMERGENCY_STOP', 'YAWN', 'FACE_MISSING',
    -- 'TILT_WARNING', 'TILT_EMERGENCY', 'TURN_LEFT', 'TURN_RIGHT'
    description             TEXT,
    value                   FLOAT
);

-- ── Індекси ──────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sessions_started_at    ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_driver_id     ON sessions(driver_id);
CREATE INDEX IF NOT EXISTS idx_metrics_session_id     ON metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at    ON metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session_id      ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_type            ON events(event_type);