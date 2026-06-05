import request from '@/utils/request'

// ==================== 用户相关API ====================

/** 用户登录 */
export function login(data) {
  return request({
    url: '/user/login',
    method: 'post',
    data
  })
}

/** 用户注册 */
export function register(data) {
  return request({
    url: '/user/register',
    method: 'post',
    data
  })
}

/** 获取用户信息 */
export function getUserInfo() {
  return request({
    url: '/user/info',
    method: 'get'
  })
}

/** 获取用户列表 */
export function getUserList(params) {
  return request({
    url: '/user/list',
    method: 'get',
    params
  })
}

/** 新增用户 */
export function createUser(data) {
  return request({
    url: '/user',
    method: 'post',
    data
  })
}

/** 更新用户 */
export function updateUser(id, data) {
  return request({
    url: `/user/${id}`,
    method: 'put',
    data
  })
}

/** 删除用户 */
export function deleteUser(id) {
  return request({
    url: `/user/${id}`,
    method: 'delete'
  })
}

/** 修改密码 */
export function changePassword(data) {
  return request({
    url: '/user/password',
    method: 'put',
    data
  })
}

// ==================== RBAC权限API ====================

/** 获取角色列表 */
export function getRoleList() {
  return request({ url: '/user/roles', method: 'get' })
}

/** 获取权限列表 */
export function getPermissionList() {
  return request({ url: '/user/permissions', method: 'get' })
}

/** 分配角色 */
export function assignRole(userId, roleIds) {
  return request({
    url: `/user/${userId}/roles`,
    method: 'put',
    data: { roleIds }
  })
}
