import request from '@/utils/request'

// ==================== 预警记录API ====================

/** 获取预警记录列表 */
export function getAlertRecordList(params) {
  return request({
    url: '/alert/record/list',
    method: 'get',
    params
  })
}

/** 获取活跃预警 */
export function getActiveAlerts(userId) {
  return request({
    url: '/alert/record/active',
    method: 'get',
    params: { userId }
  })
}

/** 处理预警 */
export function resolveAlert(recordId, resolvedBy, remark) {
  return request({
    url: `/alert/record/${recordId}/resolve`,
    method: 'put',
    params: { resolvedBy, remark }
  })
}

/** 导出预警记录 */
export function exportAlertRecords(params) {
  return request({
    url: '/alert/record/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/** 批量处理预警 */
export function batchResolveAlerts(data) {
  return request({
    url: '/alert/record/batch-resolve',
    method: 'put',
    data
  })
}

// ==================== 预警规则API ====================

/** 获取规则列表 */
export function getAlertRuleList(params) {
  return request({
    url: '/alert/rule/list',
    method: 'get',
    params
  })
}

/** 新增规则 */
export function createAlertRule(data) {
  return request({
    url: '/alert/rule',
    method: 'post',
    data
  })
}

/** 更新规则 */
export function updateAlertRule(ruleId, data) {
  return request({
    url: `/alert/rule/${ruleId}`,
    method: 'put',
    data
  })
}

/** 删除规则 */
export function deleteAlertRule(ruleId) {
  return request({
    url: `/alert/rule/${ruleId}`,
    method: 'delete'
  })
}

/** 启用/禁用规则 */
export function toggleAlertRule(ruleId, enabled) {
  return request({
    url: `/alert/rule/${ruleId}/toggle`,
    method: 'put',
    params: { enabled }
  })
}

/** 获取启用的规则列表 */
export function getEnabledRules() {
  return request({
    url: '/alert/rules/enabled',
    method: 'get'
  })
}

/** 手动评估数据 */
export function evaluateData(data) {
  return request({
    url: '/alert/evaluate',
    method: 'post',
    data
  })
}

/** 预警统计 */
export function getAlertStatistics(params) {
  return request({
    url: '/alert/statistics',
    method: 'get',
    params
  })
}
