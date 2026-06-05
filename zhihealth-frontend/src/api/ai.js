import request from '@/utils/request'

/** AI健康数据分析 */
export function analyzeHealthData(userId, data) {
  return request({
    url: '/ai/analyze',
    method: 'post',
    params: { userId },
    data
  })
}

/** 健康趋势预测 */
export function predictHealthTrend(userId, timeSeriesData, days = 7) {
  return request({
    url: '/ai/predict',
    method: 'post',
    params: { userId, days },
    data: timeSeriesData
  })
}

/** 异常检测 */
export function detectAnomalies(userId, data) {
  return request({
    url: '/ai/detect-anomalies',
    method: 'post',
    params: { userId },
    data
  })
}

/** 生成健康报告(AI) */
export function generateAiReport(userId, dataList) {
  return request({
    url: '/ai/generate-report',
    method: 'post',
    params: { userId },
    data: dataList
  })
}

/** AI智能问答(聊天) */
export function aiChat(params) {
  return request({
    url: '/ai/chat',
    method: 'post',
    data: params,
    timeout: 60000
  })
}

/** AI健康建议生成 */
export function generateAdvice(data) {
  return request({
    url: '/ai/advice',
    method: 'post',
    data,
    timeout: 60000
  })
}

/** 获取AI分析记录列表 */
export function getAiRecordList(params) {
  return request({
    url: '/ai/record/list',
    method: 'get',
    params
  })
}

/** 获取最近分析记录 */
export function getRecentAnalyses(userId, limit = 10) {
  return request({
    url: '/ai/record/recent',
    method: 'get',
    params: { userId, limit }
  })
}

/** AI服务状态检查 */
export function getAiStatus() {
  return request({ url: '/ai/status', method: 'get' })
}

/** AI统计 */
export function getAiStatistics(userId) {
  return request({
    url: '/ai/statistics',
    method: 'get',
    params: { userId }
  })
}
