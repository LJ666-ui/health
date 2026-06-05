import request from '@/utils/request'

/** 获取健康数据列表 */
export function getDataList(params) {
  return request({
    url: '/storage/list',
    method: 'get',
    params
  })
}

/** 获取数据详情 */
export function getDataDetail(id) {
  return request({
    url: `/storage/${id}`,
    method: 'get'
  })
}

/** 上报健康数据 */
export function uploadHealthData(data) {
  return request({
    url: '/collect/upload',
    method: 'post',
    data
  })
}

/** 批量上传健康数据 */
export function batchUploadData(dataList) {
  return request({
    url: '/collect/batch-upload',
    method: 'post',
    data: dataList
  })
}

/** 数据统计 */
export function getDataStatistics(params) {
  return request({
    url: '/storage/statistics',
    method: 'get',
    params
  })
}

/** 导出健康数据 */
export function exportData(params) {
  return request({
    url: '/storage/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/** 导入健康数据(Excel/CSV) */
function importData(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/storage/import',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
  })
}
