CREATE DATABASE IF NOT EXISTS `zhihealth_storage` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE `zhihealth_storage`;

CREATE TABLE IF NOT EXISTS `health_record` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `device_id` bigint(20) NOT NULL,
  `data_type` varchar(50) NOT NULL,
  `heart_rate` decimal(5,1) DEFAULT NULL,
  `body_temp` decimal(3,1) DEFAULT NULL,
  `blood_pressure_systolic` int(11) DEFAULT NULL,
  `blood_pressure_diastolic` int(11) DEFAULT NULL,
  `steps` int(11) DEFAULT NULL,
  `sleep_hours` decimal(4,1) DEFAULT NULL,
  `timestamp` bigint(20) NOT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_device_id` (`device_id`),
  KEY `idx_data_type` (`data_type`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_user_timestamp` (`user_id`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
