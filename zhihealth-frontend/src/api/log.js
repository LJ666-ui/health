import request from '@/utils/request'

/** 获取操作日志列表 */
export function getLogList(params) {
  return request({
    url: '/log/list',
    method: 'get',
    params
  })
}

/** 导出操作日志 */
export function exportLogs(params) {
  return request({
    url: '/log/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/** 清理日志 */
export function cleanLogs(data) {
  return request({
    url: '/log/clean',
    method: 'post',
    data
  })
}

/** 日志统计 */
export function getLogStatistics(params) {
  return request({
    url: '/log/statistics',
    method: 'get',
    params
  })
}
