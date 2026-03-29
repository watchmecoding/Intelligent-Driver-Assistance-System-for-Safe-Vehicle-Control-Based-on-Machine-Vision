-- Профіль за замовчуванням
INSERT INTO settings_profiles (
    profile_name, max_speed_kmh,
    enable_drowsiness, ear_threshold, stop_time, emergency_brake_dur,
    enable_yawns, mar_threshold, max_allowed_yawns,
    enable_tilt, pitch_down_threshold, pitch_up_threshold, tilt_time,
    enable_turn_signals, head_turn_angle_left, head_turn_angle_right, head_turn_time
) VALUES (
    'Default', 60,
    TRUE, 0.25, 2.5, 3.0,
    TRUE, 0.6,  3,
    TRUE, 20.0, 20.0, 2.0,
    TRUE, 25.0, 25.0, 1.5
) ON CONFLICT DO NOTHING;

-- Користувацький профіль (підвищена чутливість)
INSERT INTO settings_profiles (
    profile_name, max_speed_kmh,
    enable_drowsiness, ear_threshold, stop_time, emergency_brake_dur,
    enable_yawns, mar_threshold, max_allowed_yawns,
    enable_tilt, pitch_down_threshold, pitch_up_threshold, tilt_time,
    enable_turn_signals, head_turn_angle_left, head_turn_angle_right, head_turn_time
) VALUES (
    'High Sensitivity', 40,
    TRUE, 0.28, 2.0, 2.5,
    TRUE, 0.55, 2,
    TRUE, 15.0, 15.0, 1.5,
    TRUE, 20.0, 20.0, 1.0
) ON CONFLICT DO NOTHING;

-- Тестовий водій
INSERT INTO drivers (first_name, last_name, license_number, date_of_birth, phone)
VALUES ('Іван', 'Тестовий', 'АА123456', '1990-01-01', '+380991234567')
ON CONFLICT (license_number) DO NOTHING;

-- Тестовий автомобіль
INSERT INTO vehicles (driver_id, make, model, year, license_plate)
VALUES (
    (SELECT id FROM drivers WHERE license_number = 'АА123456'),
    'Toyota', 'Camry', 2020, 'AA1234BB'
) ON CONFLICT (license_plate) DO NOTHING;