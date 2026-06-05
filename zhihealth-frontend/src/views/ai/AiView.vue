<template>
  <div class="ai-container">
    <el-row :gutter="20">
      <!-- 左侧：AI对话区 -->
      <el-col :span="16">
        <el-card shadow="hover" class="ai-chat-card">
          <template #header>
            <div class="card-header">
              <span>AI 智能健康助手</span>
              <div class="header-right">
                <el-select v-model="selectedModel" size="small" style="width: 160px; margin-right: 10px;" placeholder="选择模型" @change="onModelChange">
                  <el-option label="通用健康助手 (qwen2)" value="qwen2:7b" />
                  <el-option label="深度分析 (llama3.1)" value="llama3.1:8b" />
                  <el-option label="快速响应 (phi3)" value="phi3:3.8b" />
                </el-select>
                <el-tag :type="isOllamaOnline ? 'success' : 'danger'" size="small">
                  {{ isOllamaOnline ? '模型在线' : '模型离线' }}
                </el-tag>
              </div>
            </div>
          </template>

          <!-- 对话消息 -->
          <div class="chat-messages" ref="chatContainer">
            <div
              v-for="(msg, index) in messages"
              :key="index"
              class="message-item"
              :class="msg.role"
            >
              <div class="avatar">
                <el-icon v-if="msg.role === 'assistant'" :size="22"><MagicStick /></el-icon>
                <el-icon v-else :size="22"><UserFilled /></el-icon>
              </div>
              <div class="content-wrapper">
                <div class="content" v-html="formatMessage(msg.content)"></div>
                <!-- AI分析结果卡片 -->
                <div v-if="msg.analysisResult" class="analysis-result-card">
                  <div class="result-header">
                    <el-icon><DataAnalysis /></el-icon>
                    <span>分析结果</span>
                    <el-tag size="small" :type="msg.analysisResult.riskLevel === 'high' ? 'danger' : msg.analysisResult.riskLevel === 'medium' ? 'warning' : 'success'">
                      {{ msg.analysisResult.riskLevel === 'high' ? '高风险' : msg.analysisResult.riskLevel === 'medium' ? '中等风险' : '低风险' }}
                    </el-tag>
                  </div>
                  <div class="result-body" v-if="msg.analysisResult.metrics">
                    <div v-for="(val, key) in msg.analysisResult.metrics" :key="key" class="metric-item">
                      <span class="metric-label">{{ getMetricLabel(key) }}</span>
                      <span class="metric-value" :class="{ warning: isAbnormal(key, val) }">{{ val }}</span>
                      <span class="metric-status">{{ getMetricStatus(key, val) }}</span>
                    </div>
                  </div>
                  <div class="result-suggestions" v-if="msg.analysisResult.suggestions && msg.analysisResult.suggestions.length">
                    <h4>健康建议</h4>
                    <ul>
                      <li v-for="(s, i) in msg.analysisResult.suggestions" :key="i">{{ s }}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <!-- 加载动画 -->
            <div v-if="loading" class="message-item assistant">
              <div class="avatar"><el-icon :size="22"><MagicStick /></el-icon></div>
              <div class="content loading">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </div>
            </div>

            <!-- 空状态引导 -->
            <div v-if="messages.length <= 1 && !loading" class="quick-questions">
              <p>试试问我：</p>
              <div class="question-chips">
                <el-button size="small" round @click="askQuestion('我的心率数据正常吗？')">我的心率数据正常吗？</el-button>
                <el-button size="small" round @click="askQuestion('最近血压偏高，需要注意什么？')">血压偏高需要注意什么？</el-button>
                <el-button size="small" round @click="askQuestion('帮我分析一下睡眠质量趋势')">分析睡眠质量趋势</el-button>
                <el-button size="small" round @click="askQuestion('给我一些运动建议')">给我运动建议</el-button>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="chat-input">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              placeholder="请输入您的问题，例如：我的心率偏高需要注意什么？"
              @keyup.enter.ctrl="sendMessage"
            />
            <div class="input-actions">
              <el-checkbox v-model="attachHealthData" size="small">附带当前健康数据</el-checkbox>
              <el-button type="primary" :icon="Promotion" :loading="loading" @click="sendMessage">发送 (Ctrl+Enter)</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：工具栏 -->
      <el-col :span="8">
        <!-- 快速分析 -->
        <el-card shadow="hover" style="margin-bottom: 16px;">
          <template #header><span>快速分析</span></template>
          <div class="quick-actions">
            <el-button type="primary" plain :icon="DataAnalysis" @click="handleQuickAnalyze('health')" :loading="analyzing === 'health'">健康数据分析</el-button>
            <el-button type="success" plain :icon="TrendCharts" @click="handleQuickAnalyze('trend')" :loading="analyzing === 'trend'">趋势预测</el-button>
            <el-button type="warning" plain :icon="Warning" @click="handleQuickAnalyze('anomaly')" :loading="analyzing === 'anomaly'">异常检测</el-button>
            <el-button type="info" plain :icon="Document" @click="handleQuickAnalyze('report')" :loading="analyzing === 'report'">生成报告</el-button>
          </div>
        </el-card>

        <!-- 分析历史 -->
        <el-card shadow="hover" style="margin-bottom: 16px;">
          <template #header>
            <span>分析历史</span>
            <el-button link size="small" @click="loadHistory">刷新</el-button>
          </template>
          <el-timeline v-if="analysisHistory.length > 0">
            <el-timeline-item
              v-for="(record, index) in analysisHistory.slice(0, 8)"
              :key="index"
              :timestamp="record.analysisTime"
              placement="top"
              :type="getTimelineType(record.status)"
            >
              <el-card shadow="never" size="small" class="history-card">
                <h4>{{ getAnalysisTypeName(record.analysisType) }}</h4>
                <p class="history-meta">
                  <span>{{ record.modelUsed || selectedModel }}</span>
                  <span v-if="record.executionTimeMs">{{ record.executionTimeMs }}ms</span>
                </p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无分析记录" :image-size="60" />
        </el-card>

        <!-- 数据概览 -->
        <el-card shadow="hover">
          <template #header><span>数据概览</span></template>
          <div class="data-overview">
            <div class="overview-item" v-for="item in dataOverview" :key="item.key">
              <div class="overview-label">{{ item.label }}</div>
              <div class="overview-value" :style="{ color: item.color }">{{ item.value }}{{ item.unit }}</div>
              <div class="overview-status" :class="item.status">{{ item.statusText }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, UserFilled, DataAnalysis, TrendCharts, Warning, Document, Promotion } from '@element-plus/icons-vue'
import { aiChat, analyzeHealthData, predictHealthTrend, detectAnomalies, generateAiReport, getRecentAnalyses, getAiStatus } from '@/api/ai'

// ==================== 对话相关 ====================
const messages = ref([
  {
    role: 'assistant',
    content: '您好！我是智康云枢AI健康助手。我可以帮您：\n\n- 分析健康数据指标\n- 预测健康趋势\n- 检测异常数据\n- 提供个性化建议\n\n请问有什么可以帮您的？'
  }
])
const inputMessage = ref('')
const loading = ref(false)
const analyzing = ref(null)
const isOllamaOnline = ref(false)
const chatContainer = ref(null)
const selectedModel = ref('qwen2:7b')
const attachHealthData = ref(true)

// 分析历史
const analysisHistory = ref([])

// 数据概览（模拟）
const dataOverview = ref([
  { key: 'heartRate', label: '心率', value: 72, unit: ' bpm', color: '#409eff', status: 'normal', statusText: '正常' },
  { key: 'bloodPressure', label: '血压', value: '118/76', unit: '', color: '#67c23a', status: 'normal', statusText: '正常' },
  { key: 'bloodOxygen', label: '血氧', value: 98, unit: '%', color: '#67c23a', status: 'normal', statusText: '正常' },
  { key: 'temperature', label: '体温', value: 36.5, unit: '°C', color: '#67c23a', status: 'normal', statusText: '正常' },
  { key: 'steps', label: '今日步数', value: 6820, unit: '', color: '#e6a23c', status: 'warn', statusText: '偏低' },
  { key: 'sleep', label: '昨晚睡眠', value: 6.5, unit: 'h', color: '#e6a23c', status: 'warn', statusText: '偏少' },
])

function formatMessage(content) {
  if (!content) return ''
  // 简单的Markdown转换：换行、加粗
  return content
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.*?)/gm, '<li>$1</li>')
}

function askQuestion(question) {
  inputMessage.value = question
  sendMessage()
}

async function sendMessage() {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = inputMessage.value.trim()
  messages.value.push({ role: 'user', content: userMessage })
  inputMessage.value = ''
  loading.value = true

  scrollToBottom()

  try {
    const payload = { question: userMessage, model: selectedModel.value }
    if (attachHealthData.value) {
      payload.healthContext = {
        heartRate: 72,
        bloodPressure: '118/76',
        bloodOxygen: 98,
        temperature: 36.5,
        steps: 6820,
        sleepHours: 6.5
      }
    }

    const res = await aiChat(payload)

    if (res.code === 200 && res.data.success) {
      const assistantMsg = {
        role: 'assistant',
        content: res.data.response || '抱歉，我暂时无法回答这个问题。',
        analysisResult: res.data.analysisResult || null
      }
      messages.value.push(assistantMsg)
    } else {
      messages.value.push({
        role: 'assistant',
        content: res.data?.error || '抱歉，服务暂时不可用，请稍后重试。'
      })
    }
  } catch (error) {
    messages.value.push({ role: 'assistant', content: '网络错误，请检查网络连接后重试。' })
  }

  loading.value = false
  scrollToBottom()
}

function onModelChange(model) {
  ElMessage.info(`已切换至模型: ${model}`)
}

// ==================== 快速分析 ====================
async function handleQuickAnalyze(type) {
  analyzing.value = type

  // 先在聊天中显示用户操作
  const typeNames = { health: '健康数据分析', trend: '趋势预测', anomaly: '异常检测', report: '生成报告' }
  messages.value.push({ role: 'user', content: `执行${typeNames[type]}...` })
  scrollToBottom()

  try {
    let res
    switch (type) {
      case 'health':
        res = await analyzeHealthData(1, { heartRate: 72, bloodPressure: '118/76', bloodOxygen: 98, temperature: 36.5 })
        break
      case 'trend':
        res = await predictHealthTrend(1, { dataType: 'heart_rate' }, 7)
        break
      case 'anomaly':
        res = await detectAnomalies(1, {})
        break
      case 'report':
        res = await generateAiReport(1, [])
        break
    }

    if (res.code === 200 && res.data.success) {
      messages.value.push({
        role: 'assistant',
        content: res.data.result || `${typeNames[type]}已完成`,
        analysisResult: res.data.analysisResult || null
      })
      ElMessage.success(`${typeNames[type]}完成`)
      loadHistory()
    } else {
      messages.value.push({ role: 'assistant', content: res.data?.error || `${typeNames[type]}失败` })
      ElMessage.error(res.data?.error || '分析失败')
    }
  } catch (error) {
    messages.value.push({ role: 'assistant', content: '分析请求失败，请检查网络或服务状态。' })
    ElMessage.error('分析请求失败')
  }

  analyzing.value = null
  scrollToBottom()
}

// ==================== 历史记录 ====================
async function loadHistory() {
  try {
    const res = await getRecentAnalyses(1, 10)
    if (res.code === 200) {
      analysisHistory.value = res.data || []
    }
  } catch (error) {
    console.error('加载分析历史失败:', error)
  }
}

function getAnalysisTypeName(type) {
  const map = {
    health_data_analysis: '健康数据分析',
    trend_prediction: '趋势预测',
    anomaly_detection: '异常检测',
    health_report_generation: '报告生成',
    health: '健康数据分析',
    trend: '趋势预测',
    anomaly: '异常检测',
    report: '报告生成'
  }
  return map[type] || type
}

function getTimelineType(status) {
  return status === 1 || status === 'completed' ? 'success' : 'danger'
}

// ==================== 健康指标工具函数 ====================
function getMetricLabel(key) {
  const map = {
    heartRate: '心率', bloodPressure: '血压', bloodOxygen: '血氧',
    temperature: '体温', bloodSugar: '血糖', steps: '步数',
    sleepQuality: '睡眠评分', weight: '体重', bmi: 'BMI'
  }
  return map[key] || key
}

function isAbnormal(key, value) {
  // 简单判断逻辑
  if (key === 'heartRate') return Number(value) > 100 || Number(value) < 55
  if (key === 'bloodOxygen') return Number(value) < 95
  if (key === 'temperature') return Number(value) > 37.3 || Number(value) < 36.0
  return false
}

function getMetricStatus(key, value) {
  if (isAbnormal(key, value)) return '偏高/偏低'
  return '正常'
}

// ==================== 工具方法 ====================
function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

onMounted(async () => {
  try {
    const statusRes = await api.get('/ai/status')
    isOllamaOnline.value = statusRes.data?.ollamaAvailable || false
  } catch (error) {
    console.warn('获取AI服务状态失败:', error)
  }
  loadHistory()
})
</script>

<style lang="scss" scoped>
.ai-container {
  .ai-chat-card {
    height: calc(100vh - 180px);
    display: flex;
    flex-direction: column;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .header-right {
        display: flex;
        align-items: center;
      }
    }

    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      background: #f5f7fa;
      border-radius: 8px;
      margin-bottom: 12px;

      .message-item {
        display: flex;
        gap: 10px;
        margin-bottom: 18px;

        &.user {
          flex-direction: row-reverse;

          .content {
            background: linear-gradient(135deg, #409eff, #337ecc);
            color: #fff;
            border-radius: 14px 14px 2px 14px;
          }
        }

        &.assistant {
          .content {
            background: #fff;
            border-radius: 14px 14px 14px 2px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
          }
        }

        .avatar {
          width: 34px;
          height: 34px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          background: #e8f4fd;
          color: #409eff;

          user & {
            background: #f0f2f5;
            color: #666;
          }
        }

        .content-wrapper {
          max-width: 75%;

          .content {
            padding: 12px 16px;
            line-height: 1.65;
            font-size: 14px;
            word-break: break-word;

            li {
              list-style-position: inside;
              margin: 4px 0;
            }

            &.loading {
              display: flex;
              gap: 6px;
              padding: 18px 24px;

              .dot {
                width: 8px; height: 8px;
                border-radius: 50%;
                background: #409eff;
                animation: bounce 1.4s infinite ease-in-out both;

                &:nth-child(1) { animation-delay: -0.32s; }
                &:nth-child(2) { animation-delay: -0.16s; }
              }
            }
          }
        }
      }

      .analysis-result-card {
        margin-top: 10px;
        background: #fffbe6;
        border: 1px solid #ffe58f;
        border-radius: 8px;
        overflow: hidden;

        .result-header {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 10px 14px;
          background: #fff7e6;
          font-weight: 600;
          font-size: 13px;
          color: #d48806;
        }

        .result-body {
          padding: 12px 14px;

          .metric-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 0;
            font-size: 13px;

            .metric-label {
              width: 70px;
              color: #666;
            }
            .metric-value {
              font-weight: 600;
              font-family: 'Monaco', monospace;
              min-width: 60px;

              &.warning { color: #e6a23c; }
              &.danger { color: #f56c6c; }
            }
            .metric-status {
              font-size: 12px;
              color: #999;
            }
          }
        }

        .result-suggestions {
          padding: 10px 14px;
          border-top: 1px dashed #ffe58f;
          background: #fffbf0;

          h4 {
            margin: 0 0 6px;
            font-size: 13px;
            color: #ad6800;
          }
          ul {
            margin: 0;
            padding-left: 16px;
            li {
              font-size: 12px;
              color: #8c6a00;
              line-height: 1.8;
            }
          }
        }
      }

      .quick-questions {
        text-align: center;
        padding: 30px 20px;

        p {
          color: #999;
          margin-bottom: 14px;
          font-size: 13px;
        }

        .question-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: center;
        }
      }
    }

    .chat-input {
      textarea { resize: none; }

      .input-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 8px;
      }
    }
  }

  .quick-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .history-card {
    h4 {
      margin: 0 0 4px;
      font-size: 13px;
    }
    .history-meta {
      margin: 0;
      font-size: 11px;
      color: #999;
      display: flex;
      gap: 10px;
    }
  }

  .data-overview {
    .overview-item {
      display: flex;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child { border-bottom: none; }

      .overview-label {
        width: 80px;
        font-size: 13px;
        color: #666;
      }
      .overview-value {
        font-size: 16px;
        font-weight: bold;
        font-family: 'Monaco', monospace;
        flex: 1;
      }
      .overview-status {
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 10px;

        &.normal { background: #f0f9eb; color: #67c23a; }
        &.warn { background: #fdf6ec; color: #e6a23c; }
        &.danger { background: #fef0f0; color: #f56c6c; }
      }
    }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
