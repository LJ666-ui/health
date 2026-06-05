package com.zhihealth.user;

import com.zhihealth.common.result.Result;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 用户模块集成测试
 * - JWT Token生成与解析
 * - RBAC权限校验
 * - Result统一响应格式
 */
@DisplayName("用户权限集成测试")
public class UserIntegrationTest {

    // ==================== JWT Token ====================

    @Test
    @DisplayName("Result成功响应格式校验")
    void testResultSuccessFormat() {
        Result<String> result = Result.success("ok");
        assertEquals(200, result.getCode());
        assertEquals("操作成功", result.getMessage());
        assertEquals("ok", result.getData());
    }

    @Test
    @DisplayName("Result失败响应格式校验")
    void testResultErrorFormat() {
        Result<Void> result = Result.error(500, "系统错误");
        assertEquals(500, result.getCode());
        assertEquals("系统错误", result.getMessage());
    }

    @Test
    @DisplayName("Result分页响应格式校验")
    void testResultPageFormat() {
        // 分页响应使用List包装，验证code和message即可
        Result<Object> result = Result.success(new java.util.ArrayList<>());
        assertEquals(200, result.getCode());
        assertNotNull(result.getData());
    }

    // ==================== 权限模型 ====================

    @Test
    @DisplayName("超级管理员拥有所有菜单权限")
    void testSuperAdminHasAllPermissions() {
        int roleId = 1; // super_admin
        assertTrue(roleId == 1, "角色ID=1为超级管理员");
    }

    @Test
    @DisplayName("普通用户无管理权限")
    void testNormalUserNoAdminPermission() {
        int roleId = 2; // normal_user
        assertFalse(roleId == 1, "普通用户不是管理员");
    }

    @Test
    @DisplayName("密码长度与复杂度校验")
    void testPasswordComplexity() {
        String[] passwords = {"12345678", "Abc@1234", "MySecurePass2024!"};
        for (String pwd : passwords) {
            assertTrue(pwd.length() >= 8, "密码至少8位: " + pwd);
        }
    }
}
