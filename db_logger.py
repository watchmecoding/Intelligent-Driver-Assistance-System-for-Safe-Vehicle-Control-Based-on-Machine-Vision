# db_logger.py
import psycopg2
from psycopg2 import pool
from config import *


class DatabaseLogger:
    def __init__(self):
        self.connection_pool = None
        self.session_id      = None
        self.connected       = False
        self._connect()

    def _connect(self):
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1, maxconn=5,
                host=DB_HOST, port=DB_PORT,
                database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
            self.connected = True
            print("PostgreSQL підключено")
        except Exception as e:
            self.connected = False
            print(f"PostgreSQL не підключено: {e}")

    def _get_conn(self):
        return self.connection_pool.getconn() if self.connection_pool else None

    def _release_conn(self, conn):
        if self.connection_pool and conn:
            self.connection_pool.putconn(conn)

    # Сесії
    def start_session(self, driver_id=None, vehicle_id=None,
                      settings_profile_id=2):
        if not self.connected:
            return None
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sessions
                        (started_at, driver_id, vehicle_id,
                         settings_profile_id)
                    VALUES (NOW(), %s, %s, %s) RETURNING id
                """, (driver_id, vehicle_id, settings_profile_id))
                self.session_id = cur.fetchone()[0]
            conn.commit()
            print(f"Сесія #{self.session_id} розпочата")
            return self.session_id
        except Exception as e:
            print(f"Помилка старту сесії: {e}")
            conn.rollback()
        finally:
            self._release_conn(conn)
        return None

    def end_session(self, total_yawns=0, emergency_count=0,
                    face_missing_count=0):
        if not self.connected or not self.session_id:
            return
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sessions
                    SET ended_at           = NOW(),
                        total_yawns        = %s,
                        emergency_count    = %s,
                        face_missing_count = %s
                    WHERE id = %s
                """, (total_yawns, emergency_count,
                      face_missing_count, self.session_id))
            conn.commit()
            print(f"Сесія #{self.session_id} завершена")
        except Exception as e:
            print(f"Помилка завершення сесії: {e}")
            conn.rollback()
        finally:
            self._release_conn(conn)

    # Налаштування: читання
    def _load_view(self, view_name):
        if not self.connected:
            return None
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {view_name}")
                row  = cur.fetchone()
                cols = [d[0] for d in cur.description]
            return dict(zip(cols, row)) if row else None
        except Exception as e:
            print(f"Помилка читання {view_name}: {e}")
        finally:
            self._release_conn(conn)
        return None

    def load_settings(self):
        return self._load_view("v_settings")

    def load_default_settings(self):
        return self._load_view("v_default_settings")

    # Налаштування: збереження
    def save_settings(self, s):
        if not self.connected:
            return
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO settings_general
                        (profile_id, max_speed_kmh, updated_at)
                    VALUES (2, %s, NOW())
                    ON CONFLICT (profile_id) DO UPDATE SET
                        max_speed_kmh = EXCLUDED.max_speed_kmh,
                        updated_at    = NOW()
                """, (s.max_speed_kmh,))

                cur.execute("""
                    INSERT INTO settings_drowsiness
                        (profile_id, ear_threshold, mar_threshold, stop_time,
                         emergency_brake_dur, peace_cooldown,
                         enable_drowsiness, updated_at)
                    VALUES (2, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (profile_id) DO UPDATE SET
                        ear_threshold       = EXCLUDED.ear_threshold,
                        mar_threshold       = EXCLUDED.mar_threshold,
                        stop_time           = EXCLUDED.stop_time,
                        emergency_brake_dur = EXCLUDED.emergency_brake_dur,
                        peace_cooldown      = EXCLUDED.peace_cooldown,
                        enable_drowsiness   = EXCLUDED.enable_drowsiness,
                        updated_at          = NOW()
                """, (s.ear_threshold, s.mar_threshold, s.stop_time,
                      s.emergency_brake_dur, s.peace_cooldown,
                      s.enable_drowsiness))

                cur.execute("""
                    INSERT INTO settings_head_tilt
                        (profile_id, pitch_down_threshold, pitch_up_threshold,
                         tilt_time, enable_tilt, updated_at)
                    VALUES (2, %s, %s, %s, %s, NOW())
                    ON CONFLICT (profile_id) DO UPDATE SET
                        pitch_down_threshold = EXCLUDED.pitch_down_threshold,
                        pitch_up_threshold   = EXCLUDED.pitch_up_threshold,
                        tilt_time            = EXCLUDED.tilt_time,
                        enable_tilt          = EXCLUDED.enable_tilt,
                        updated_at           = NOW()
                """, (s.pitch_down_threshold, s.pitch_up_threshold,
                      s.tilt_time, s.enable_tilt))

                cur.execute("""
                    INSERT INTO settings_turn_signals
                        (profile_id, head_turn_angle_left, head_turn_angle_right,
                         head_turn_time, head_turn_off_time,
                         enable_turn_signals, updated_at)
                    VALUES (2, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (profile_id) DO UPDATE SET
                        head_turn_angle_left  = EXCLUDED.head_turn_angle_left,
                        head_turn_angle_right = EXCLUDED.head_turn_angle_right,
                        head_turn_time        = EXCLUDED.head_turn_time,
                        head_turn_off_time    = EXCLUDED.head_turn_off_time,
                        enable_turn_signals   = EXCLUDED.enable_turn_signals,
                        updated_at            = NOW()
                """, (s.head_turn_angle_left, s.head_turn_angle_right,
                      s.head_turn_time, s.head_turn_off_time,
                      s.enable_turn_signals))

                cur.execute("""
                    INSERT INTO settings_yawns
                        (profile_id, max_allowed_yawns, enable_yawns,
                         updated_at)
                    VALUES (2, %s, %s, NOW())
                    ON CONFLICT (profile_id) DO UPDATE SET
                        max_allowed_yawns = EXCLUDED.max_allowed_yawns,
                        enable_yawns      = EXCLUDED.enable_yawns,
                        updated_at        = NOW()
                """, (s.max_allowed_yawns, s.enable_yawns))

                cur.execute("""
                    INSERT INTO settings_face_missing
                        (profile_id, face_missing_time, enable_face_missing, updated_at)
                    VALUES (2, %s, %s, NOW())
                    ON CONFLICT (profile_id) DO UPDATE SET
                        face_missing_time   = EXCLUDED.face_missing_time,
                        enable_face_missing = EXCLUDED.enable_face_missing,
                        updated_at          = NOW()
                """, (s.face_missing_time, s.enable_face_missing))

            conn.commit()
            print("Налаштування збережено")
        except Exception as e:
            print(f"Помилка збереження: {e}")
            conn.rollback()
        finally:
            self._release_conn(conn)

    def reset_settings_to_default(self):
        if not self.connected:
            return False
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                for table, fields in [
                    ("settings_general",
                     "max_speed_kmh=d.max_speed_kmh"),
                    ("settings_drowsiness",
                     "ear_threshold=d.ear_threshold, "
                     "mar_threshold=d.mar_threshold, "
                     "stop_time=d.stop_time, "
                     "emergency_brake_dur=d.emergency_brake_dur, "
                     "peace_cooldown=d.peace_cooldown, "
                     "enable_drowsiness=d.enable_drowsiness"),
                    ("settings_head_tilt",
                     "pitch_down_threshold=d.pitch_down_threshold, "
                     "pitch_up_threshold=d.pitch_up_threshold, "
                     "tilt_time=d.tilt_time, enable_tilt=d.enable_tilt"),
                    ("settings_turn_signals",
                     "head_turn_angle_left=d.head_turn_angle_left, "
                     "head_turn_angle_right=d.head_turn_angle_right, "
                     "head_turn_time=d.head_turn_time, "
                     "head_turn_off_time=d.head_turn_off_time, "
                     "enable_turn_signals=d.enable_turn_signals"),
                    ("settings_yawns",
                     "max_allowed_yawns=d.max_allowed_yawns, "
                     "enable_yawns=d.enable_yawns"),
                    ("settings_face_missing",
                     "face_missing_time=d.face_missing_time, "
                     "enable_face_missing=d.enable_face_missing"),
                ]:
                    cur.execute(f"""
                        UPDATE {table} u
                        SET {fields}, updated_at=NOW()
                        FROM {table} d
                        WHERE d.profile_id=1 AND u.profile_id=2
                    """)
            conn.commit()
            return True
        except Exception as e:
            print(f"Помилка скидання: {e}")
            conn.rollback()
            return False
        finally:
            self._release_conn(conn)
    
    def get_driver_info(self, driver_id=1):
        if not self.connected:
            return {}
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT first_name, last_name,
                        license_number, birth_date, phone
                    FROM drivers WHERE id = %s
                """, (driver_id,))
                row = cur.fetchone()
                if row:
                    return {
                        'first_name':     row[0],
                        'last_name':      row[1],
                        'license_number': row[2],
                        'birth_date':     str(row[3]) if row[3] else None,
                        'phone':          row[4],
                    }
        except Exception as e:
            print(f"Помилка отримання водія: {e}")
        finally:
            self._release_conn(conn)
        return {}

    def get_vehicle_info(self, owner_id=1):
        if not self.connected:
            return {}
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT license_plate, make, model, year
                    FROM vehicles WHERE owner_id = %s
                    LIMIT 1
                """, (owner_id,))
                row = cur.fetchone()
                if row:
                    return {
                        'license_plate': row[0],
                        'make':          row[1],
                        'model':         row[2],
                        'year':          row[3],
                    }
        except Exception as e:
            print(f"Помилка отримання ТЗ: {e}")
        finally:
            self._release_conn(conn)
        return {}

    def get_sessions_summary(self, limit=30):
        if not self.connected:
            return []
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        id,
                        TO_CHAR(started_at, 'DD.MM.YYYY HH24:MI') AS started_fmt,
                        TO_CHAR(ended_at,   'HH24:MI')            AS ended_fmt,
                        EXTRACT(EPOCH FROM (
                            COALESCE(ended_at, NOW()) - started_at
                        ))::INTEGER                               AS duration_sec,
                        COALESCE(total_yawns,        0)           AS total_yawns,
                        COALESCE(emergency_count,    0)           AS emergency_count,
                        COALESCE(face_missing_count, 0)           AS face_missing_count
                    FROM sessions
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                cols = ['id', 'started_at', 'ended_at', 'duration_sec',
                        'total_yawns', 'emergency_count', 'face_missing_count']
                return [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            print(f"Помилка get_sessions_summary: {e}")
            return []
        finally:
            self._release_conn(conn)
 
    def close(self):
        if self.connection_pool:
            self.connection_pool.closeall()
