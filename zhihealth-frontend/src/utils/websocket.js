/**
 * WebSocket全局预警推送服务
 * - 连接后端WebSocket/SSE服务
 * - 接收实时预警消息
 * - 右上角弹出通知（Element Plus Notification）
 * - 支持声音提醒
 * - 自动重连机制
 */

import { ElNotification } from 'element-plus'
import { ref, onMounted, onUnmounted } from 'vue'

// ============== 配置 ==============
const WS_CONFIG = {
  // WebSocket地址（开发环境通过Vite代理 /ws -> ws://后端）
  url: (import.meta.env.VITE_WS_URL || '')
    ? import.meta.env.VITE_WS_URL
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/alert`,
  // 重连配置
  reconnect: {
    enabled: true,
    maxAttempts: 10,
    interval: 3000,       // 首次重连间隔(ms)
    maxInterval: 30000,   // 最大重连间隔(ms)
    backoffMultiplier: 1.5
  },
  // 心跳
  heartbeat: {
    enabled: true,
    interval: 30000,      // 心跳间隔(ms)
    timeout: 10000        // 心跳超时(ms)
  }
}

// ============== 状态 ==============
let ws = null
let reconnectAttempts = 0
let heartbeatTimer = null
let heartbeatTimeoutTimer = null
let isManualClose = false
const listeners = []  // 外部监听器

// ============== 预警等级映射 ==============
const LEVEL_MAP = {
  1: { type: 'info', title: '提示', color: '#67C23A', icon: 'InfoFilled' },
  2: { type: 'warning', title: '警告', color: '#E6A23C', icon: 'Warning' },
  3: { type: 'error', title: '紧急', color: '#F56C6C', icon: 'CircleCloseFilled' }
}

// ============== 核心方法 ==============

/**
 * 建立WebSocket连接
 */
export function connectAlertWS() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    console.warn('[AlertWS] 已有连接或正在连接')
    return
  }

  isManualClose = false

  try {
    const token = localStorage.getItem('token')
    const url = `${WS_CONFIG.url}?token=${token || ''}`

    ws = new WebSocket(url)

    ws.onopen = () => {
      console.log('[AlertWS] 连接成功')
      reconnectAttempts = 0
      startHeartbeat()
      _emit('connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleAlertMessage(data)
      } catch (e) {
        console.error('[AlertWS] 消息解析失败:', e, event.data)
      }
    }

    ws.onclose = (event) => {
      console.log(`[AlertWS] 连接关闭: code=${event.code}, reason=${event.reason}`)
      stopHeartbeat()
      _emit('disconnected')

      if (!isManualClose && WS_CONFIG.reconnect.enabled) {
        scheduleReconnect()
      }
    }

    ws.onerror = (error) => {
      console.error('[AlertWS] 连接错误:', error)
      _emit('error', error)
    }

  } catch (e) {
    console.error('[AlertWS] 创建连接失败:', e)
    scheduleReconnect()
  }
}

/**
 * 处理收到的预警消息
 */
function handleAlertMessage(data) {
  const msgType = data.type || data.messageType || 'alert'

  switch (msgType) {
    case 'alert':
    case 'notification':
      showNotification(data)
      _emit('alert', data)
      playAlertSound(data.level || data.alertLevel)
      break

    case 'heartbeat':
      handleHeartbeatResponse(data)
      break

    case 'system':
      _emit('system', data)
      break

    default:
      _emit('message', data)
  }
}

/**
 * 显示预警通知弹窗
 */
function showNotification(alertData) {
  const level = alertData.level || alertData.alertLevel || 2
  const levelConfig = LEVEL_MAP[level] || LEVEL_MAP[2]

  ElNotification({
    title: `[${levelConfig.title}] ${alertData.ruleName || alertData.title || '健康预警'}`,
    message: buildNotificationContent(alertData),
    type: levelConfig.type,
    position: 'top-right',
    duration: 0,           // 手动关闭
    showClose: true,
    onClick: () => {
      _emit('click', alertData)
    },
    customClass: 'health-alert-notification'
  })

  // 添加自定义样式到DOM
  injectAlertStyles()
}

/**
 * 构建通知内容HTML
 */
function buildNotificationContent(data) {
  let html = '<div class="alert-notification-content">'

  // 预警信息
  if (data.metric && data.currentValue !== undefined) {
    html += `<div class="alert-metric">
      <span class="metric-name">${data.metric}</span>
      <span class="metric-value" style="color:${_getValueColor(data)}">${data.currentValue}${data.unit || ''}</span>`
    if (data.threshold !== undefined) {
      html += `<span class="metric-threshold">阈值: ${data.threshold}</span>`
    }
    html += '</div>'
  }

  // 预警描述
  if (data.message || data.description) {
    html += `<p class="alert-desc">${data.message || data.description}</p>`
  }

  // 用户/设备信息
  if (data.userId || data.deviceId) {
    html += `<div class="alert-meta">
      <span>用户ID: ${data.userId || '-'}</span>
      <span>设备: ${data.deviceId || '-'}</span>
      <span>${data.alertTime || new Date().toLocaleString()}</span>
    </div>`
  }

  html += '</div>'
  return html
}

function _getValueColor(data) {
  const level = data.level || data.alertLevel || 1
  return LEVEL_MAP[level]?.color || '#E6A23C'
}

/**
 * 注入预警通知样式
 */
function injectAlertStyles() {
  if (document.getElementById('alert-notify-styles')) return

  const style = document.createElement('style')
  style.id = 'alert-notify-styles'
  style.textContent = `
    .health-alert-notification .el-notification__content {
      width: 320px;
    }
    .alert-notification-content {
      font-size: 13px;
      line-height: 1.6;
    }
    .alert-metric {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      padding: 4px 8px;
      background: #f5f7fa;
      border-radius: 4px;
    }
    .metric-name {
      color: #606266;
      font-weight: 500;
    }
    .metric-value {
      font-size: 16px;
      font-weight: bold;
    }
    .metric-threshold {
      color: #909399;
      font-size: 12px;
      margin-left: auto;
    }
    .alert-desc {
      color: #303133;
      margin: 4px 0;
    }
    .alert-meta {
      display: flex;
      justify-content: space-between;
      color: #909399;
      font-size: 11px;
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid #ebeef5;
    }
  `
  document.head.appendChild(style)
}

/**
 * 播放预警提示音
 */
function playAlertSound(level) {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = audioCtx.createOscillator()
    const gainNode = audioCtx.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioCtx.destination)

    // 不同级别不同音调
    const freqMap = { 1: 520, 2: 680, 3: 880 }
    oscillator.frequency.value = freqMap[level] || 600
    oscillator.type = 'sine'

    gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3)

    oscillator.start(audioCtx.currentTime)
    oscillator.stop(audioCtx.currentTime + 0.3)
  } catch (e) {
    // 音频播放失败静默处理
  }
}

// ============== 心跳机制 ==============

function startHeartbeat() {
  if (!WS_CONFIG.heartbeat.enabled) return

  stopHeartbeat()
  heartbeatTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }))
      // 设置超时检测
      heartbeatTimeoutTimer = setTimeout(() => {
        console.warn('[AlertWS] 心跳超时，关闭连接')
        ws.close(4001, '心跳超时')
      }, WS_CONFIG.heartbeat.timeout)
    }
  }, WS_CONFIG.heartbeat.interval)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
  if (heartbeatTimeoutTimer) {
    clearTimeout(heartbeatTimeoutTimer)
    heartbeatTimeoutTimer = null
  }
}

function handleHeartbeatResponse(data) {
  if (heartbeatTimeoutTimer) {
    clearTimeout(heartbeatTimeoutTimer)
    heartbeatTimeoutTimer = null
  }
}

// ============== 重连机制 ==============

function scheduleReconnect() {
  if (reconnectAttempts >= WS_CONFIG.reconnect.maxAttempts) {
    console.error(`[AlertWS] 已达最大重试次数(${WS_CONFIG.reconnect.maxAttempts})，停止重连`)
    _emit('reconnect_failed')
    return
  }

  const delay = Math.min(
    WS_CONFIG.reconnect.interval * Math.pow(WS_CONFIG.reconnect.backoffMultiplier, reconnectAttempts),
    WS_CONFIG.reconnect.maxInterval
  )

  reconnectAttempts++
  console.log(`[AlertWS] 将在${delay}ms后第${reconnectAttempts}次重连`)

  _emit('reconnecting', { attempt: reconnectAttempts, delay })

  setTimeout(() => {
    connectAlertWS()
  }, delay)
}

// ============== 事件系统 ==============

function _emit(event, data) {
  listeners.forEach(listener => {
    try {
      listener(event, data)
    } catch (e) {
      console.error('[AlertWS] 监听器错误:', e)
    }
  })
}

/**
 * 监听事件
 * @param {(event: string, data: any) => void} callback
 * @returns 取消订阅函数
 */
export function onAlertEvent(callback) {
  listeners.push(callback)
  return () => {
    const idx = listeners.indexOf(callback)
    if (idx > -1) listeners.splice(idx, 1)
  }
}

// ============== 公开API ==============

/**
 * 关闭连接（手动，不自动重连）
 */
export function disconnectAlertWS() {
  isManualClose = true
  stopHeartbeat()
  if (ws) {
    ws.close(1000, '用户主动断开')
    ws = null
  }
}

/**
 * 获取当前连接状态
 */
export function getAlertWSStatus() {
  if (!ws) return 'closed'
  switch (ws.readyState) {
    case WebSocket.CONNECTING: return 'connecting'
    case WebSocket.OPEN: return 'connected'
    case WebSocket.CLOSING: return 'closing'
    case WebSocket.CLOSED: return 'closed'
    default: return 'unknown'
  }
}

/**
 * 手动发送消息
 */
export function sendAlertMessage(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data))
    return true
  }
  return false
}

// ============== Vue Composable ==============

/**
 * Vue3组合式函数：使用WebSocket预警
 * 在组件setup中使用：const { status, alerts } = useAlertWebSocket()
 */
export function useAlertWebSocket(autoConnect = true) {
  const status = ref(getAlertWSStatus())
  const recentAlerts = ref([])

  const handler = (event, data) => {
    status.value = getAlertWSStatus()
    if (event === 'alert') {
      recentAlerts.value.unshift(data)
      if (recentAlerts.value.length > 50) recentAlerts.value.pop()
    }
  }

  onMounted(() => {
    onAlertEvent(handler)
    if (autoConnect) connectAlertWS()
  })

  onUnmounted(() => {
    disconnectAlertWS()
    const idx = listeners.indexOf(handler)
    if (idx > -1) listeners.splice(idx, 1)
  })

  return {
    status,
    recentAlerts,
    connect: connectAlertWS,
    disconnect: disconnectAlertWS,
    send: sendAlertMessage
  }
}
