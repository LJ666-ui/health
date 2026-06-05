UPDATE sys_user SET password = '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi' WHERE username = 'admin';
SELECT id, username, LEFT(password, 20) as pwd_prefix FROM sys_user WHERE username='admin';
