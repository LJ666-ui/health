package com.zhihealth.user.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.zhihealth.user.entity.Permission;
import com.zhihealth.user.entity.Role;
import com.zhihealth.user.entity.RolePermission;
import com.zhihealth.user.entity.UserRole;
import com.zhihealth.user.mapper.PermissionMapper;
import com.zhihealth.user.mapper.RoleMapper;
import com.zhihealth.user.mapper.RolePermissionMapper;
import com.zhihealth.user.mapper.UserRoleMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class RbacService {

    private final RoleMapper roleMapper;
    private final PermissionMapper permissionMapper;
    private final UserRoleMapper userRoleMapper;
    private final RolePermissionMapper rolePermissionMapper;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String USER_PERMISSIONS_CACHE = "rbac:user:permissions:";
    private static final String USER_ROLES_CACHE = "rbac:user:roles:";
    private static final String ALL_PERMISSIONS_CACHE = "rbac:all:permissions";
    private static final int CACHE_HOURS = 2;

    // ==================== 角色管理 ====================

    public List<Role> getAllRoles() {
        LambdaQueryWrapper<Role> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Role::getStatus, 1)
               .orderByAsc(Role::getSortOrder);
        return roleMapper.selectList(wrapper);
    }

    public Role getRoleById(Long roleId) {
        return roleMapper.selectById(roleId);
    }

    public Role getRoleByCode(String roleCode) {
        LambdaQueryWrapper<Role> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Role::getRoleCode, roleCode);
        return roleMapper.selectOne(wrapper);
    }

    public void createRole(Role role) {
        LambdaQueryWrapper<Role> checkWrapper = new LambdaQueryWrapper<>();
        checkWrapper.eq(Role::getRoleCode, role.getRoleCode());
        if (roleMapper.selectCount(checkWrapper) > 0) {
            throw new RuntimeException("角色编码已存在: " + role.getRoleCode());
        }
        role.setStatus(1);
        roleMapper.insert(role);
        clearAllPermissionsCache();
    }

    public void updateRole(Role role) {
        roleMapper.updateById(role);
        clearAllPermissionsCache();
    }

    public void deleteRole(Long roleId) {
        // 删除角色-权限关联
        LambdaQueryWrapper<RolePermission> rpWrapper = new LambdaQueryWrapper<>();
        rpWrapper.eq(RolePermission::getRoleId, roleId);
        rolePermissionMapper.delete(rpWrapper);

        // 删除用户-角色关联
        LambdaQueryWrapper<UserRole> urWrapper = new LambdaQueryWrapper<>();
        urWrapper.eq(UserRole::getRoleId, roleId);
        userRoleMapper.delete(urWrapper);

        roleMapper.deleteById(roleId);
        clearAllPermissionsCache();
    }

    // ==================== 权限管理 ====================

    public List<Permission> getAllPermissions() {
        LambdaQueryWrapper<Permission> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Permission::getStatus, 1)
               .orderByAsc(Permission::getParentId)
               .orderByAsc(Permission::getSortOrder);
        return permissionMapper.selectList(wrapper);
    }

    public List<Permission> getPermissionsByRoleId(Long roleId) {
        List<Long> permissionIds = getPermissionIdsByRoleId(roleId);
        if (permissionIds.isEmpty()) {
            return new ArrayList<>();
        }
        LambdaQueryWrapper<Permission> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(Permission::getId, permissionIds)
               .orderByAsc(Permission::getSortOrder);
        return permissionMapper.selectList(wrapper);
    }

    public Permission getPermissionById(Long permissionId) {
        return permissionMapper.selectById(permissionId);
    }

    public void createPermission(Permission permission) {
        permission.setStatus(1);
        permissionMapper.insert(permission);
        clearAllPermissionsCache();
    }

    public void updatePermission(Permission permission) {
        permissionMapper.updateById(permission);
        clearAllPermissionsCache();
    }

    public void deletePermission(Long permissionId) {
        // 删除角色-权限关联
        LambdaQueryWrapper<RolePermission> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RolePermission::getPermissionId, permissionId);
        rolePermissionMapper.delete(wrapper);

        permissionMapper.deleteById(permissionId);
        clearAllPermissionsCache();
    }

    // ==================== 用户-角色分配 ====================

    @Transactional
    public void assignRolesToUser(Long userId, List<Long> roleIds) {
        // 先删除旧关联
        LambdaQueryWrapper<UserRole> deleteWrapper = new LambdaQueryWrapper<>();
        deleteWrapper.eq(UserRole::getUserId, userId);
        userRoleMapper.delete(deleteWrapper);

        // 添加新关联
        if (roleIds != null && !roleIds.isEmpty()) {
            for (Long roleId : roleIds) {
                UserRole userRole = new UserRole();
                userRole.setUserId(userId);
                userRole.setRoleId(roleId);
                userRoleMapper.insert(userRole);
            }
        }

        // 清除用户缓存
        clearUserCache(userId);
    }

    public List<Role> getUserRoles(Long userId) {
        // 先查缓存
        String cacheKey = USER_ROLES_CACHE + userId;
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof List) {
            return (List<Role>) cached;
        }

        LambdaQueryWrapper<UserRole> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserRole::getUserId, userId);

        List<UserRole> userRoles = userRoleMapper.selectList(wrapper);
        if (userRoles.isEmpty()) {
            return new ArrayList<>();
        }

        List<Long> roleIds = userRoles.stream()
                .map(UserRole::getRoleId)
                .collect(Collectors.toList());

        LambdaQueryWrapper<Role> roleWrapper = new LambdaQueryWrapper<>();
        roleWrapper.in(Role::getId, roleIds);
        List<Role> roles = roleMapper.selectList(roleWrapper);

        // 缓存
        redisTemplate.opsForValue().set(cacheKey, roles, CACHE_HOURS, TimeUnit.HOURS);
        return roles;
    }

    // ==================== 角色-权限分配 ====================

    @Transactional
    public void assignPermissionsToRole(Long roleId, List<Long> permissionIds) {
        // 先删除旧关联
        LambdaQueryWrapper<RolePermission> deleteWrapper = new LambdaQueryWrapper<>();
        deleteWrapper.eq(RolePermission::getRoleId, roleId);
        rolePermissionMapper.delete(deleteWrapper);

        // 添加新关联
        if (permissionIds != null && !permissionIds.isEmpty()) {
            for (Long permissionId : permissionIds) {
                RolePermission rp = new RolePermission();
                rp.setRoleId(roleId);
                rp.setPermissionId(permissionId);
                rolePermissionMapper.insert(rp);
            }
        }

        clearAllPermissionsCache();
    }

    // ==================== 权限校验（核心） ====================

    /**
     * 校验用户是否拥有指定权限
     */
    public boolean hasPermission(Long userId, String resourceCode, String action) {
        Set<String> permissions = getUserPermissions(userId);
        String requiredPerm = resourceCode + ":" + action;
        return permissions.contains(requiredPerm) || permissions.contains("*:*");
    }

    /**
     * 校验用户是否拥有指定角色
     */
    public boolean hasRole(Long userId, String roleCode) {
        List<Role> roles = getUserRoles(userId);
        return roles.stream().anyMatch(r -> r.getRoleCode().equals(roleCode));
    }

    /**
     * 获取用户所有权限码集合（带Redis缓存）
     */
    @SuppressWarnings("unchecked")
    public Set<String> getUserPermissions(Long userId) {
        String cacheKey = USER_PERMISSIONS_CACHE + userId;
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof Set) {
            return (Set<String>) cached;
        }

        Set<String> permissions = new HashSet<>();

        // 超级管理员拥有所有权限
        if (hasRole(userId, "super_admin")) {
            permissions.add("*:*");
            redisTemplate.opsForValue().set(cacheKey, permissions, CACHE_HOURS, TimeUnit.HOURS);
            return permissions;
        }

        // 获取用户角色
        List<Role> roles = getUserRoles(userId);
        if (roles.isEmpty()) {
            redisTemplate.opsForValue().set(cacheKey, permissions, CACHE_HOURS, TimeUnit.HOURS);
            return permissions;
        }

        // 收集所有角色的权限ID
        List<Long> roleIds = roles.stream().map(Role::getId).collect(Collectors.toList());
        Set<Long> allPermissionIds = new HashSet<>();

        for (Long roleId : roleIds) {
            allPermissionIds.addAll(getPermissionIdsByRoleId(roleId));
        }

        if (!allPermissionIds.isEmpty()) {
            LambdaQueryWrapper<Permission> permWrapper = new LambdaQueryWrapper<>();
            permWrapper.in(Permission::getId, allPermissionIds);
            List<Permission> perms = permissionMapper.selectList(permWrapper);

            for (Permission p : perms) {
                permissions.add(p.getResourceCode() + ":" + p.getAction());
            }
        }

        redisTemplate.opsForValue().set(cacheKey, permissions, CACHE_HOURS, TimeUnit.HOURS);
        return permissions;
    }

    private List<Long> getPermissionIdsByRoleId(Long roleId) {
        LambdaQueryWrapper<RolePermission> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(RolePermission::getRoleId, roleId);
        List<RolePermission> rps = rolePermissionMapper.selectList(wrapper);
        return rps.stream()
                .map(RolePermission::getPermissionId)
                .collect(Collectors.toList());
    }

    // ==================== 初始化默认数据 ====================

    /**
     * 初始化系统默认角色和权限（首次部署时调用）
     */
    @Transactional
    public void initDefaultData() {
        log.info("开始初始化RBAC默认数据...");

        // 创建默认权限
        createDefaultPermissions();

        // 创建默认角色
        createDefaultRoles();

        log.info("RBAC默认数据初始化完成");
    }

    private void createDefaultPermissions() {
        // 用户管理权限
        createPermIfNotExists("用户查看", "user:view", "menu", "user", "view");
        createPermIfNotExists("用户新增", "user:create", "button", "user", "create");
        createPermIfNotExists("用户编辑", "user:update", "button", "user", "update");
        createPermIfNotExists("用户删除", "user:delete", "button", "user", "delete");

        // 设备管理权限
        createPermIfNotExists("设备查看", "device:view", "menu", "device", "view");
        createPermIfNotExists("设备新增", "device:create", "button", "device", "create");
        createPermIfNotExists("设备编辑", "device:update", "button", "device", "update");
        createPermIfNotExists("设备删除", "device:delete", "button", "device", "delete");

        // 数据管理权限
        createPermIfNotExists("数据查询", "data:view", "menu", "data", "view");
        createPermIfNotExists("数据导入", "data:import", "button", "data", "import");
        createPermIfNotExists("数据导出", "data:export", "button", "data", "export");

        // 告警中心权限
        createPermIfNotExists("告警查看", "alert:view", "menu", "alert", "view");
        createPermIfNotExists("告警处理", "alert:handle", "button", "alert", "handle");
        createPermIfNotExists("告警规则配置", "alert:config", "button", "alert", "config");

        // AI分析权限
        createPermIfNotExists("AI分析", "ai:analyze", "menu", "ai", "analyze");
        createPermIfNotExists("AI模型管理", "ai:model_manage", "button", "ai", "model_manage");

        // 报告中心权限
        createPermIfNotExists("报告查看", "report:view", "menu", "report", "view");
        createPermIfNotExists("报告生成", "report:generate", "button", "report", "generate");
        createPermIfNotExists("报告下载", "report:download", "button", "report", "download");

        // 系统管理权限
        createPermIfNotExists("系统设置", "settings:view", "menu", "settings", "view");
        createPermIfNotExists("日志查看", "log:view", "menu", "log", "view");
        createPermIfNotExists("日志清理", "log:clean", "button", "log", "clean");
        createPermIfNotExists("日志导出", "log:export", "button", "log", "export");
    }

    private void createPermIfNotExists(String name, String code, String type, String resource, String action) {
        LambdaQueryWrapper<Permission> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Permission::getPermissionCode, code);
        if (permissionMapper.selectCount(wrapper) == 0) {
            Permission p = new Permission();
            p.setPermissionName(name);
            p.setPermissionCode(code);
            p.setResourceType(type);
            p.setResourceCode(resource);
            p.setAction(action);
            p.setStatus(1);
            p.setParentId(0L);
            p.setSortOrder(0);
            permissionMapper.insert(p);
        }
    }

    private void createDefaultRoles() {
        // 超级管理员
        Role superAdmin = createRoleIfNotExists("超级管理员", "super_admin",
                "拥有系统全部权限，可执行任何操作", 0);

        // 系统管理员
        Role admin = createRoleIfNotExists("系统管理员", "admin",
                "负责系统日常运维和管理工作", 1);

        // 医生/健康顾问
        Role doctor = createRoleIfNotExists("医生/健康顾问", "doctor",
                "负责查看和分析用户健康数据，提供专业建议", 2);

        // 普通用户
        Role user = createRoleIfNotExists("普通用户", "user",
                "普通注册用户，可查看自己的健康数据", 3);

        // 为超级管理员分配全部权限
        if (superAdmin != null) {
            LambdaQueryWrapper<Permission> allPerms = new LambdaQueryWrapper<>();
            allPerms.eq(Permission::getStatus, 1);
            List<Permission> perms = permissionMapper.selectList(allPerms);
            List<Long> permIds = perms.stream().map(Permission::getId).collect(Collectors.toList());

            assignPermissionsToRole(superAdmin.getId(), permIds);
        }

        // 为系统管理员分配大部分权限（不含AI模型管理和用户删除）
        if (admin != null) {
            LambdaQueryWrapper<Permission> adminPerms = new LambdaQueryWrapper<>();
            adminPerms.eq(Permission::getStatus, 1)
                     .notIn(Permission::getPermissionCode,
                             Arrays.asList("user:delete", "ai:model_manage"));
            List<Permission> perms = permissionMapper.selectList(adminPerms);
            List<Long> permIds = perms.stream().map(Permission::getId).collect(Collectors.toList());
            assignPermissionsToRole(admin.getId(), permIds);
        }

        // 医生角色权限
        if (doctor != null) {
            List<String> doctorPermCodes = Arrays.asList(
                    "user:view", "device:view", "data:view", "data:export",
                    "alert:view", "alert:handle", "ai:analyze",
                    "report:view", "report:generate", "report:download"
            );
            assignPermissionsByCodes(doctor.getId(), doctorPermCodes);
        }

        // 普通用户权限
        if (user != null) {
            List<String> userPermCodes = Arrays.asList(
                    "data:view", "report:view", "report:download", "alert:view"
            );
            assignPermissionsByCodes(user.getId(), userPermCodes);
        }
    }

    private Role createRoleIfNotExists(String roleName, String roleCode, String desc, int order) {
        LambdaQueryWrapper<Role> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Role::getRoleCode, roleCode);
        Role existing = roleMapper.selectOne(wrapper);
        if (existing != null) {
            return existing;
        }
        Role role = new Role();
        role.setRoleName(roleName);
        role.setRoleCode(roleCode);
        role.setDescription(desc);
        role.setStatus(1);
        role.setSortOrder(order);
        roleMapper.insert(role);
        return role;
    }

    private void assignPermissionsByCodes(Long roleId, List<String> codes) {
        if (codes == null || codes.isEmpty()) return;

        LambdaQueryWrapper<Permission> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(Permission::getPermissionCode, codes);
        List<Permission> perms = permissionMapper.selectList(wrapper);
        List<Long> permIds = perms.stream().map(Permission::getId).collect(Collectors.toList());

        if (!permIds.isEmpty()) {
            assignPermissionsToRole(roleId, permIds);
        }
    }

    // ==================== 缓存管理 ====================

    private void clearUserCache(Long userId) {
        redisTemplate.delete(USER_PERMISSIONS_CACHE + userId);
        redisTemplate.delete(USER_ROLES_CACHE + userId);
    }

    private void clearAllPermissionsCache() {
        // 清除全量权限缓存
        redisTemplate.delete(ALL_PERMISSIONS_CACHE);
        // 清除所有用户的权限缓存（通过模式匹配）
        Set<String> keys = redisTemplate.keys(USER_PERMISSIONS_CACHE + "*");
        if (keys != null && !keys.isEmpty()) {
            redisTemplate.delete(keys);
        }
        Set<String> roleKeys = redisTemplate.keys(USER_ROLES_CACHE + "*");
        if (roleKeys != null && !roleKeys.isEmpty()) {
            redisTemplate.delete(roleKeys);
        }
    }

    /**
     * 清除指定用户的所有RBAC缓存（用于角色变更后）
     */
    public void clearUserPermissionCache(Long userId) {
        clearUserCache(userId);
    }
}
