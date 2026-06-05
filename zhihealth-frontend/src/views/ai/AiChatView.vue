<template>
  <div class="ai-chat-container">
    <!-- 聊天头部 -->
    <div class="chat-header">
      <div class="header-left">
        <el-icon :size="20" color="#409EFF"><ChatDotRound /></el-icon>
        <span class="title">AI智能健康助手</span>
        <el-tag v-if="aiStatus.online" type="success" size="small" effect="dark">在线</el-tag>
        <el-tag v-else type="danger" size="small" effect="dark">离线</el-tag>
      </div>
      <div class="header-right">
        <el-button text size="small" @click="clearHistory">
          <el-icon><Delete /></el-icon> 清空对话
        </el-button>
        <el-button text size="small" @click="$emit('close')">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesRef">
      <!-- 欢迎消息 -->
      <div v-if="messages.length === 0" class="welcome-area">
        <div class="welcome-icon"><el-icon :size="48" color="#409EFF"><MagicStick /></el-icon></div>
        <h3>智康云枢 AI 健康助手</h3>
        <p>我可以帮您：</p>
        <div class="quick-cards">
          <div class="quick-card" v-for="(q, i) in quickQuestions" :key="i" @click="sendQuickQuestion(q.text)">
            <el-icon><component :is="q.icon" /></el-icon>
            <span>{{ q.label }}</span>
          </div>
        </div>
      </div>

      <!-- 消息气泡 -->
      <div v-for="(msg, idx) in messages" :key="idx"
           :class="['message-bubble', msg.role === 'user' ? 'user-msg' : 'ai-msg']">
        <div class="avatar">
          <el-avatar v-if="msg.role === 'user'" :size="32" icon="UserFilled" />
          <el-avatar v-else :size="32" :style="{ background: '#409EFF' }" icon="MagicStick" />
        </div>
        <div class="bubble-content">
          <div class="bubble-text" v-html="formatMessage(msg.content)"></div>
          <div class="bubble-time">{{ formatTime(msg.timestamp) }}</div>
          <!-- AI消息的操作按钮 -->
          <div v-if="msg.role === 'assistant'" class="bubble-actions">
            <el-button text size="small" @click="copyText(msg.content)">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
            <el-button text size="small" @click="regenerate(idx)">
              <el-icon><RefreshRight /></el-icon> 重答
            </el-button>
          </div>
        </div>
      </div>

      <!-- 正在输入指示器 -->
      <div v-if="loading" class="message-bubble ai-msg">
        <div class="avatar">
          <el-avatar :size="32" :style="{ background: '#409EFF' }" icon="MagicStick" />
        </div>
        <div class="bubble-content">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷问题栏 -->
    <div class="quick-bar" v-if="messages.length > 0 && !loading">
      <span class="quick-label">快捷提问:</span>
      <el-tag
        v-for="(q, i) in quickQuestions.slice(0, 4)"
        :key="'q'+i"
        size="small"
        effect="plain"
        class="quick-tag"
        @click="sendQuickQuestion(q.text)"
      >{{ q.label }}</el-tag>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="2"
        :maxlength="500"
        show-word-limit
        placeholder="请描述您的健康问题，例如：我的心率最近总是偏高..."
        resize="none"
        @keydown.enter.exact.prevent="sendMessage"
        :disabled="loading || !aiStatus.online"
      />
      <div class="input-actions">
        <el-button type="primary" :loading="loading" :disabled="!canSend" @click="sendMessage">
          <el-icon><Promotion /></el-icon> 发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const emit = defineEmits(['close'])
const messagesRef = ref(null)
const inputMessage = ref('')
const loading = ref(false)
const messages = ref([])
const aiStatus = ref({ online: false })

// 快捷问题
const quickQuestions = [
  { label: '健康趋势分析', icon: 'TrendCharts', text: '帮我分析一下最近一周的健康数据趋势' },
  { label: '风险评估', icon: 'Warning', text: '根据我的数据做一次全面健康风险评估' },
  { label: '运动建议', icon: 'Soccer', text: '我想改善运动量，有什么建议吗' },
  { label: '睡眠改善', icon: 'Moon', text: '最近睡眠质量不好，怎么改善' },
  { label: '饮食建议', icon: 'Bowl', text: '我的饮食结构需要调整吗' },
  { label: '血压解读', icon: 'Monitor', text: '我的血压数据正常吗' }
]

const canSend = computed(() => inputMessage.value.trim().length > 0 && !loading.value)

// 发送消息
async function sendMessage() {
  const text = inputMessage.value.trim()
  if (!text || loading.value.value) return

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: text,
    timestamp: Date.now()
  })
  inputMessage.value = ''
  scrollToBottom()

  // 调用AI接口
  await fetchAiReply(text)
}

function sendQuickQuestion(text) {
  inputMessage.value = text
  sendMessage()
}

// 调用后端AI接口
async function fetchAiReply(userMessage) {
  loading.value = true

  try {
    const res = await request.post('/api/ai/chat', {
      message: userMessage,
      user_id: 'current_user',
      context: getContextData()
    }, { timeout: 120000 })  // AI可能较慢

    if (res.data?.data?.reply) {
      messages.value.push({
        role: 'assistant',
        content: res.data.data.reply,
        timestamp: Date.now(),
        intent: res.data.data.intent
      })
    } else {
      throw new Error(res.data?.message || '无有效回复')
    }
  } catch (e) {
    const errMsg = e.msg || e.message || 'AI服务暂时不可用'
    messages.value.push({
      role: 'assistant',
      content: `抱歉，${errMsg}。您可以稍后再试或联系管理员。`,
      timestamp: Date.now(),
      isError: true
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// 重新生成（删除最后一条AI回复重新请求）
async function regenerate(idx) {
  if (loading.value) return
  // 找到对应的用户消息
  let userMsgIdx = idx - 1
  while (userMsgIdx >= 0 && messages.value[userMsgIdx].role !== 'user') userMsgIdx--
  if (userMsgIdx >= 0) {
    // 删除从用户消息开始的所有后续消息
    messages.value.splice(userMsgIdx + 1)
    const userText = messages.value[userMsgIdx].content
    await fetchAiReply(userText)
  }
}

// 复制文本
function copyText(text) {
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}

// 清空历史
function clearHistory() {
  messages.value = []
}

// 构造上下文数据（可选）
function getContextData() {
  return null  // 可扩展：传入当前用户的最新健康指标摘要
}

// 格式化消息（Markdown简单渲染）
function formatMessage(content) {
  return content
    .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
    .replace(/^#{1,3}\s(.+)$/gm, '<strong style="color:#409EFF">$1</strong>')
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

// 检查AI服务状态
async function checkAiStatus() {
  try {
    const res = await request.get('/api/ai/status', { timeout: 5000 })
    aiStatus.value = res.data?.data || {}
  } catch {
    aiStatus.value.online = false
  }
}

onMounted(() => {
  checkAiStatus()
})
</script>

<style scoped lang="scss">
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;

  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #ebeef5;
    background: #fafafa;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .title {
        font-size: 15px;
        font-weight: 600;
        color: #303133;
      }
    }

    .header-right {
      display: flex;
      gap: 4px;
    }
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    scroll-behavior: smooth;

    &::-webkit-scrollbar { width: 4px; }
    &::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }

    .welcome-area {
      text-align: center;
      padding: 40px 20px;

      h3 { margin: 12px 0 6px; font-size: 18px; color: #303133; }
      p { color: #909399; margin-bottom: 24px; }

      .quick-cards {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        max-width: 480px;
        margin: 0 auto;
      }

      .quick-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        padding: 14px 10px;
        border: 1px solid #e4e7ed;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 13px;
        color: #606266;

        &:hover {
          border-color: #409EFF;
          color: #409EFF;
          box-shadow: 0 2px 8px rgba(64,158,255,0.15);
        }

        .el-icon { font-size: 22px; }
      }
    }

    .message-bubble {
      display: flex;
      gap: 10px;
      margin-bottom: 16px;

      &.user-msg {
        flex-direction: row-reverse;

        .bubble-content {
          background: #409EFF;
          color: #fff;
          border-radius: 14px 14px 2px 14px;
        }
      }

      &.ai-msg {
        .bubble-content {
          background: #f5f7fa;
          color: #303133;
          border-radius: 14px 14px 14px 2px;
        }
      }

      .bubble-content {
        max-width: 75%;
        padding: 10px 14px;
        line-height: 1.7;
        font-size: 14px;

        .bubble-time {
          font-size: 11px;
          color: #909399;
          margin-top: 4px;
        }

        .bubble-actions {
          margin-top: 6px;
          display: none;
          gap: 4px;
        }

        &:hover .bubble-actions { display: block; }
      }
    }

    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 8px 4px;

      span {
        width: 8px;
        height: 8px;
        background: #c0c4cc;
        border-radius: 50%;
        animation: bounce 1.4s infinite ease-in-out both;

        &:nth-child(1) { animation-delay: -0.32s; }
        &:nth-child(2) { animation-delay: -0.16s; }
      }
    }
  }

  @keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
  }

  .quick-bar {
    padding: 8px 16px;
    border-top: 1px solid #f0f0f0;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;

    .quick-label {
      font-size: 12px;
      color: #909399;
      white-space: nowrap;
    }

    .quick-tag {
      cursor: pointer;
      transition: all 0.2s;
      &:hover { color: #409EFF; border-color: #409EFF; }
    }
  }

  .chat-input {
    padding: 12px 16px;
    border-top: 1px solid #ebeef5;

    .input-actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 8px;
    }
  }
}
</style>
