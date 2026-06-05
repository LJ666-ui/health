import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '@/router'

// 创建axios实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json;charset=UTF-8'
  }
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 添加请求时间戳防止缓存（GET请求）
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now()
      }
    }

    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data

    // 业务状态码判断
    if (res.code !== undefined && res.code !== 200 && res.code !== '200') {
      // Token过期或无效
      if (res.code === 401 || res.code === '401') {
        ElMessageBox.confirm('登录已过期，请重新登录', '提示', {
          confirmButtonText: '重新登录',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          localStorage.removeItem('token')
          localStorage.removeItem('userInfo')
          router.push('/login')
        })
        return Promise.reject(new Error(res.msg || '认证失败'))
      }

      // 服务熔断/降级
      if (String(res.code).startsWith('503')) {
        ElMessage.warning(res.msg || '服务暂时不可用，请稍后重试')
        return Promise.reject(new Error(res.msg))
      }

      // 其他业务错误
      ElMessage.error(res.msg || '请求失败')
      return Promise.reject(new Error(res.msg || '请求失败'))
    }

    return res
  },
  error => {
    console.error('响应错误:', error)

    // 网络错误
    if (!error.response) {
      ElMessage.error('网络连接失败，请检查网络设置')
      return Promise.reject(error)
    }

    const status = error.response.status
    switch (status) {
      case 401:
        localStorage.removeItem('token')
        localStorage.removeItem('userInfo')
        router.push('/login')
        break
      case 403:
        ElMessage.error('没有权限访问该资源')
        break
      case 404:
        ElMessage.error('请求的资源不存在')
        break
      case 429:
        ElMessage.warning('请求过于频繁，请稍后再试')
        break
      case 500:
        ElMessage.error('服务器内部错误')
        break
      case 502:
      case 503:
      case 504:
        ElMessage.warning('服务暂时不可用，请稍后重试')
        break
      default:
        ElMessage.error(`请求失败(${status})`)
    }

    return Promise.reject(error)
  }
)

export default request
