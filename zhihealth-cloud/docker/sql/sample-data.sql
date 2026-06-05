-- Sample Data for ZhiHealth Demo

INSERT IGNORE INTO health_data (user_id, device_code, data_type, data_value, unit, measure_time, source) VALUES
(1, 'DEV001', 'HEART_RATE', '{"value": 72}', 'bpm', '2026-06-04 08:00:00', 'DEVICE'),
(1, 'DEV001', 'HEART_RATE', '{"value": 78}', 'bpm', '2026-06-04 12:00:00', 'DEVICE'),
(1, 'DEV001', 'HEART_RATE', '{"value": 68}', 'bpm', '2026-06-04 18:00:00', 'DEVICE'),
(1, 'DEV002', 'BLOOD_PRESSURE', '{"systolic": 120, "diastolic": 80}', 'mmHg', '2026-06-04 08:30:00', 'DEVICE'),
(1, 'DEV002', 'BLOOD_PRESSURE', '{"systolic": 128, "diastolic": 85}', 'mmHg', '2026-06-04 18:30:00', 'DEVICE'),
(2, 'DEV003', 'WEIGHT', '{"value": 70.5}', 'kg', '2026-06-04 07:00:00', 'DEVICE'),
(1, 'DEV004', 'OXYGEN', '{"value": 98}', '%', '2026-06-04 09:00:00', 'DEVICE');

SELECT COUNT(*) AS health_data_count FROM health_data;
