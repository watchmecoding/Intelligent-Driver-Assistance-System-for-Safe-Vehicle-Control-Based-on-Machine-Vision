-- ── 1. Всі поїздки з тривалістю ─────────────────────────────
SELECT
    s.id,
    d.first_name || ' ' || d.last_name          AS driver,
    v.make || ' ' || v.model                    AS vehicle,
    TO_CHAR(s.started_at, 'DD.MM.YYYY HH24:MI') AS started,
    TO_CHAR(s.ended_at,   'HH24:MI')            AS ended,
    EXTRACT(EPOCH FROM (
        COALESCE(s.ended_at, NOW()) - s.started_at
    ))::INTEGER / 60                            AS duration_min,
    s.total_yawns,
    s.emergency_count,
    s.face_missing_count
FROM sessions s
LEFT JOIN drivers  d ON d.id = s.driver_id
LEFT JOIN vehicles v ON v.id = s.vehicle_id
ORDER BY s.started_at DESC;


-- ── 2. Статистика по водію ───────────────────────────────────
SELECT
    d.first_name || ' ' || d.last_name          AS driver,
    COUNT(s.id)                                  AS total_sessions,
    SUM(s.total_yawns)                           AS total_yawns,
    SUM(s.emergency_count)                       AS total_emergencies,
    SUM(s.face_missing_count)                    AS total_face_missing,
    ROUND(AVG(
        EXTRACT(EPOCH FROM (
            COALESCE(s.ended_at, NOW()) - s.started_at
        )) / 60
    )::NUMERIC, 1)                               AS avg_duration_min
FROM sessions s
JOIN drivers d ON d.id = s.driver_id
GROUP BY d.id, d.first_name, d.last_name
ORDER BY total_sessions DESC;


-- ── 3. Найнебезпечніші поїздки ───────────────────────────────
SELECT
    s.id,
    TO_CHAR(s.started_at, 'DD.MM.YYYY HH24:MI') AS started,
    s.emergency_count,
    s.total_yawns,
    s.face_missing_count,
    (s.emergency_count * 3 +
     s.total_yawns     * 1 +
     s.face_missing_count * 2)                   AS risk_score
FROM sessions s
WHERE s.ended_at IS NOT NULL
ORDER BY risk_score DESC
LIMIT 10;


-- ── 4. Розподіл подій по типу ────────────────────────────────
SELECT
    event_type,
    COUNT(*)                                     AS occurrences,
    COUNT(DISTINCT session_id)                   AS sessions_affected,
    ROUND(AVG(value)::NUMERIC, 2)                AS avg_value
FROM events
GROUP BY event_type
ORDER BY occurrences DESC;


-- ── 5. Середні метрики за сесією ────────────────────────────
SELECT
    m.session_id,
    TO_CHAR(s.started_at, 'DD.MM.YYYY HH24:MI') AS started,
    ROUND(AVG(m.ear_value)::NUMERIC,  3)         AS avg_ear,
    ROUND(AVG(m.mar_value)::NUMERIC,  3)         AS avg_mar,
    ROUND(AVG(ABS(m.yaw_angle))::NUMERIC, 1)     AS avg_yaw_abs,
    ROUND(AVG(m.speed)::NUMERIC, 0)              AS avg_speed_pct,
    COUNT(*)                                     AS metric_records
FROM metrics m
JOIN sessions s ON s.id = m.session_id
GROUP BY m.session_id, s.started_at
ORDER BY s.started_at DESC;


-- ── 6. Поїздки за останні 7 днів ────────────────────────────
SELECT
    DATE(started_at)                             AS trip_date,
    COUNT(*)                                     AS sessions,
    SUM(total_yawns)                             AS yawns,
    SUM(emergency_count)                         AS emergencies
FROM sessions
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(started_at)
ORDER BY trip_date DESC;


-- ── 7. Поточна активна сесія ────────────────────────────────
SELECT
    s.id,
    d.first_name || ' ' || d.last_name          AS driver,
    TO_CHAR(s.started_at, 'HH24:MI')            AS started,
    EXTRACT(EPOCH FROM (NOW() - s.started_at))::INTEGER / 60
                                                 AS running_min
FROM sessions s
LEFT JOIN drivers d ON d.id = s.driver_id
WHERE s.ended_at IS NULL
ORDER BY s.started_at DESC
LIMIT 1;