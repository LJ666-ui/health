-- 通过注册接口创建测试用户（密码会被BCrypt加密）
USE zhihealth_user;

-- 删除旧admin记录
DELETE FROM sys_user WHERE username = 'admin';

-- 插入新的admin用户（明文密码admin123将在注册时被BCrypt加密）
-- 先手动插入，然后通过API测试
INSERT INTO sys_user (username, password, nickname, status, role_id) VALUES 
('admin', '$2a$10$dXJ3SW6G7P50lGmMkkmwe.20cQQubK3.HZWzG3YB1tlRy.fqvM/BG', '系统管理员', 1, 1);

SELECT id, username, LEFT(password, 30) as pwd_prefix FROM sys_user WHERE username = 'admin';
