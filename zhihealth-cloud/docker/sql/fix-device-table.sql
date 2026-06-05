-- 修复device_info表结构以匹配DeviceInfo实体
USE zhihealth_device;

-- 添加缺失的列
ALTER TABLE device_info ADD COLUMN device_model varchar(50) DEFAULT NULL COMMENT '设备型号' AFTER device_type;
ALTER TABLE device_info ADD COLUMN serial_number varchar(100) DEFAULT NULL COMMENT '序列号' AFTER device_model;
ALTER TABLE device_info ADD COLUMN firmware_version varchar(30) DEFAULT NULL COMMENT '固件版本' AFTER serial_number;
ALTER TABLE device_info ADD COLUMN location varchar(255) DEFAULT NULL COMMENT '位置' AFTER battery_level;

-- 验证
DESCRIBE device_info;
SELECT 'device_info structure fixed!' as result;
