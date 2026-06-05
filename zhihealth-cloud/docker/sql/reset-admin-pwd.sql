USE zhihealth_user;

-- 重置admin密码为admin123的BCrypt哈希
-- BCrypt hash for 'admin123': $2a$10$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW
UPDATE sys_user SET password = '$2a$10$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW' WHERE username = 'admin';

-- 验证
SELECT id, username, LEFT(password, 30) as pwd_prefix FROM sys_user WHERE username = 'admin';
