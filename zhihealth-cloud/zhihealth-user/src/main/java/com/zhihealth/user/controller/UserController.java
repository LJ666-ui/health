package com.zhihealth.user.controller;

import com.zhihealth.common.result.Result;
import com.zhihealth.user.entity.Permission;
import com.zhihealth.user.entity.Role;
import com.zhihealth.user.entity.User;
import com.zhihealth.user.service.RbacService;
import com.zhihealth.user.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;
    private final RbacService rbacService;

    // ==================== 用户管理 ====================

    @PostMapping("/register")
    public Result<Map<String, Object>> register(@RequestBody User user) {
        Map<String, Object> data = userService.register(user);
        return Result.success("注册成功", data);
    }

    @PostMapping("/login")
    public Result<Map<String, Object>> login(@RequestParam String username,
                                              @RequestParam String password) {
        Map<String, Object> data = userService.login(username, password);
        return Result.success(data);
    }

    @PutMapping("/password")
    public Result<Void> updatePassword(@RequestHeader("X-User-Id") Long userId,
                                        @RequestParam String oldPassword,
                                        @RequestParam String newPassword) {
        userService.updatePassword(userId, oldPassword, newPassword);
        return Result.success();
    }

    @GetMapping("/profile")
    public Result<User> getUserProfile(@RequestHeader("X-User-Id") Long userId) {
        User user = userService.getUserProfile(userId);
        return Result.success(user);
    }

    @PutMapping("/profile")
    public Result<Void> updateUserProfile(@RequestHeader("X-User-Id") Long userId,
                                           @RequestBody User updateUser) {
        userService.updateUserProfile(userId, updateUser);
        return Result.success();
    }

    // ==================== 角色管理 ====================

    @GetMapping("/role/list")
    public Result<List<Role>> getAllRoles() {
        List<Role> roles = rbacService.getAllRoles();
        return Result.success(roles);
    }

    @GetMapping("/role/{roleId}")
    public Result<Role> getRoleById(@PathVariable Long roleId) {
        Role role = rbacService.getRoleById(roleId);
        return Result.success(role);
    }

    @PostMapping("/role")
    public Result<Void> createRole(@RequestBody Role role) {
        rbacService.createRole(role);
        return Result.success();
    }

    @PutMapping("/role/{roleId}")
    public Result<Void> updateRole(@PathVariable Long roleId, @RequestBody Role role) {
        role.setId(roleId);
        rbacService.updateRole(role);
        return Result.success();
    }

    @DeleteMapping("/role/{roleId}")
    public Result<Void> deleteRole(@PathVariable Long roleId) {
        rbacService.deleteRole(roleId);
        return Result.success();
    }

    // ==================== 权限管理 ====================

    @GetMapping("/permission/list")
    public Result<List<Permission>> getAllPermissions() {
        List<Permission> permissions = rbacService.getAllPermissions();
        return Result.success(permissions);
    }

    @GetMapping("/permission/{permissionId}")
    public Result<Permission> getPermissionById(@PathVariable Long permissionId) {
        Permission permission = rbacService.getPermissionById(permissionId);
        return Result.success(permission);
    }

    @GetMapping("/role/{roleId}/permissions")
    public Result<List<Permission>> getPermissionsByRoleId(@PathVariable Long roleId) {
        List<Permission> permissions = rbacService.getPermissionsByRoleId(roleId);
        return Result.success(permissions);
    }

    @PostMapping("/permission")
    public Result<Void> createPermission(@RequestBody Permission permission) {
        rbacService.createPermission(permission);
        return Result.success();
    }

    @PutMapping("/permission/{permissionId}")
    public Result<Void> updatePermission(@PathVariable Long permissionId, @RequestBody Permission permission) {
        permission.setId(permissionId);
        rbacService.updatePermission(permission);
        return Result.success();
    }

    @DeleteMapping("/permission/{permissionId}")
    public Result<Void> deletePermission(@PathVariable Long permissionId) {
        rbacService.deletePermission(permissionId);
        return Result.success();
    }

    // ==================== 用户-角色分配 ====================

    @GetMapping("/{userId}/roles")
    public Result<List<Role>> getUserRoles(@PathVariable Long userId) {
        List<Role> roles = rbacService.getUserRoles(userId);
        return Result.success(roles);
    }

    @PostMapping("/{userId}/roles")
    public Result<Void> assignRolesToUser(@PathVariable Long userId,
                                          @RequestBody Map<String, List<Long>> body) {
        List<Long> roleIds = body.get("roleIds");
        rbacService.assignRolesToUser(userId, roleIds);
        return Result.success();
    }

    // ==================== 角色-权限分配 ====================

    @PostMapping("/role/{roleId}/permissions")
    public Result<Void> assignPermissionsToRole(@PathVariable Long roleId,
                                                @RequestBody Map<String, List<Long>> body) {
        List<Long> permissionIds = body.get("permissionIds");
        rbacService.assignPermissionsToRole(roleId, permissionIds);
        return Result.success();
    }

    // ==================== 权限校验 ====================

    @GetMapping("/{userId}/permissions/check")
    public Result<Map<String, Object>> checkUserPermission(
            @PathVariable Long userId,
            @RequestParam String resourceCode,
            @RequestParam String action) {
        boolean hasPerm = rbacService.hasPermission(userId, resourceCode, action);
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("hasPermission", hasPerm);
        result.put("resource", resourceCode);
        result.put("action", action);
        return Result.success(result);
    }

    @GetMapping("/{userId}/permissions/all")
    public Result<java.util.Set<String>> getUserAllPermissions(@PathVariable Long userId) {
        java.util.Set<String> permissions = rbacService.getUserPermissions(userId);
        return Result.success(permissions);
    }

    // ==================== 初始化 ====================

    @PostMapping("/rbac/init")
    public Result<Void> initRbacData() {
        rbacService.initDefaultData();
        return Result.success();
    }
}
