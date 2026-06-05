import request from '@/utils/request'

/** 获取设备列表 */
export function getDeviceList(params) {
  return request({
    url: '/device/list',
    method: 'get',
    params
  })
}

/** 获取设备详情 */
export function getDeviceDetail(id) {
  return request({
    url: `/device/${id}`,
    method: 'get'
  })
}

/** 新增设备 */
export function createDevice(data) {
  return request({
    url: '/device',
    method: 'post',
    data
  })
}

/** 更新设备 */
export function updateDevice(id, data) {
  return request({
    url: `/device/${id}`,
    method: 'put',
    data
  })
}

/** 删除设备 */
export function deleteDevice(id) {
  return request({
    url: `/device/${id}`,
    method: 'delete'
  })
}

/** 绑定/解绑用户 */
export function bindUser(deviceId, userId) {
  return request({
    url: `/device/${deviceId}/bind`,
    method: 'put',
    data: { userId }
  })
}

/** 获取设备在线状态统计 */
export function getDeviceStats() {
  return request({
    url: '/device/statistics',
    method: 'get'
  })
}
