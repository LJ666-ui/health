import request from '@/utils/request'

/** 获取报告列表 */
export function getReportList(params) {
  return request({
    url: '/report/list',
    method: 'get',
    params
  })
}

/** 生成报告(异步) */
export function generateReport(data) {
  return request({
    url: '/report/generate',
    method: 'post',
    data,
    timeout: 60000 // 报告生成可能较慢
  })
}

/** 获取报告详情 */
export function getReportDetail(id) {
  return request({
    url: `/report/${id}`,
    method: 'get'
  })
}

/** 下载报告(PDF) */
export function downloadPdf(id) {
  return request({
    url: `/report/${id}/download/pdf`,
    method: 'get',
    responseType: 'blob'
  })
}

/** 下载报告(Excel) */
export function downloadExcel(id) {
  return request({
    url: `/report/${id}/download/excel`,
    method: 'get',
    responseType: 'blob'
  })
}

/** 下载报告(Word) */
export function downloadWord(id) {
  return request({
    url: `/report/${id}/download/word`,
    method: 'get',
    responseType: 'blob'
  })
}

/** 删除报告 */
export function deleteReport(id) {
  return request({
    url: `/report/${id}`,
    method: 'delete'
  })
}

/** 报告统计 */
export function getReportStatistics(params) {
  return request({
    url: '/report/statistics',
    method: 'get',
    params
  })
}

// ============== 健康档案 ==============

/** 获取档案列表 */
export function getArchives(params) {
  return request({
    url: '/report/archive/list',
    method: 'get',
    params
  })
}

/** 生成AI分析报告 */
export function generateAiReport(data) {
  return request({
    url: '/report/generate-ai',
    method: 'post',
    data,
    timeout: 120000 // AI生成可能较慢
  })
}

/** 导出档案 */
export function exportArchive(data) {
  return request({
    url: '/report/export',
    method: 'post',
    data,
    responseType: 'blob'
  })
}

export const reportApi = {
  getReportList,
  generateReport,
  getReportDetail,
  downloadPdf,
  downloadExcel,
  downloadWord,
  deleteReport,
  getReportStatistics,
  getArchives,
  generateAiReport,
  exportArchive
}
