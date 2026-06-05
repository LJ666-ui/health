CREATE DATABASE IF NOT EXISTS `zhihealth_device` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE `zhihealth_device`;

CREATE TABLE IF NOT EXISTS `device_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `device_name` varchar(100) NOT NULL,
  `device_type` varchar(50) NOT NULL,
  `device_model` varchar(100) DEFAULT NULL,
  `serial_number` varchar(100) NOT NULL,
  `firmware_version` varchar(50) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT '1',
  `location` varchar(200) DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_serial_number` (`serial_number`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_device_type` (`device_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
