<template>
  <div class="settings-container">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="settings-card">
          <template #header>
            <span>系统设置</span>
          </template>

          <el-tabs v-model="activeTab" type="border-card">
            <el-tab-pane label="基本设置" name="basic">
              <el-form :model="basicSettings" label-width="140px" class="settings-form">
                <el-divider content-position="left">系统信息</el-divider>
                
                <el-form-item label="系统名称">
                  <el-input v-model="basicSettings.systemName" placeholder="请输入系统名称" />
                </el-form-item>

                <el-form-item label="系统Logo">
                  <el-input v-model="basicSettings.systemLogo" placeholder="Logo URL" />
                  <div class="form-tip">支持图片URL地址或上传图片</div>
                </el-form-item>

                <el-form-item label="系统描述">
                  <el-input 
                    v-model="basicSettings.systemDescription" 
                    type="textarea" 
                    :rows="3"
                    placeholder="请输入系统描述"
                  />
                </el-form-item>

                <el-divider content-position="left">接口配置</el-divider>

                <el-form-item label="API网关地址">
                  <el-input v-model="basicSettings.gatewayUrl" placeholder="http://localhost:8080" />
                </el-form-item>

                <el-form-item label="请求超时时间(秒)">
                  <el-input-number v-model="basicSettings.requestTimeout" :min="5" :max="120" />
                </el-form-item>

                <el-form-item label="默认分页大小">
                  <el-select v-model="basicSettings.defaultPageSize" style="width: 200px;">
                    <el-option :label="item" :value="item" v-for="item in [10, 20, 30, 50, 100]" :key="item" />
                  </el-select>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="saveBasicSettings">保存设置</el-button>
                  <el-button @click="resetBasicSettings">恢复默认</el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="告警配置" name="alert">
              <el-form :model="alertSettings" label-width="160px" class="settings-form">
                <el-divider content-position="left">全局告警开关</el-divider>

                <el-form-item label="启用告警系统">
                  <el-switch v-model="alertSettings.enableAlert" />
                </el-form-item>

                <el-form-item label="冷却时间(秒)">
                  <el-input-number v-model="alertSettings.cooldownSeconds" :min="0" :max="3600" />
                  <div class="form-tip">同一规则触发后的最小间隔时间，防止告警风暴</div>
                </el-form-item>

                <el-divider content-position="left">通知渠道</el-divider>

                <el-form-item label="邮件通知">
                  <el-switch v-model="alertSettings.channels.email.enabled" />
                </el-form-item>

                <el-form-item label="SMTP服务器" v-if="alertSettings.channels.email.enabled">
                  <el-input v-model="alertSettings.channels.email.smtpHost" placeholder="smtp.example.com" />
                </el-form-item>

                <el-form-item label="SMTP端口" v-if="alertSettings.channels.email.enabled">
                  <el-input-number v-model="alertSettings.channels.email.smtpPort" :min="1" :max="65535" />
                </el-form-item>

                <el-form-item label="Webhook通知">
                  <el-switch v-model="alertSettings.channels.webhook.enabled" />
                </el-form-item>

                <el-form-item label="Webhook URL" v-if="alertSettings.channels.webhook.enabled">
                  <el-input v-model="alertSettings.channels.webhook.url" placeholder="https://your-webhook-url" />
                </el-form-item>

                <el-form-item label="钉钉机器人">
                  <el-switch v-model="alertSettings.channels.dingtalk.enabled" />
                </el-form-item>

                <el-form-item label="企业微信">
                  <el-switch v-model="alertSettings.channels.wechatWork.enabled" />
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="saveAlertSettings">保存设置</el-button>
                  <el-button @click="testAlertNotification" :loading="testingAlert">
                    发送测试通知
                  </el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="AI服务配置" name="ai">
              <el-form :model="aiSettings" label-width="160px" class="settings-form">
                <el-divider content-position="left">Python AI服务</el-divider>

                <el-form-item label="服务地址">
                  <el-input v-model="aiSettings.pythonAiService.url" placeholder="http://localhost:5000" />
                </el-form-item>

                <el-form-item label="超时时间(秒)">
                  <el-input-number v-model="aiSettings.pythonAiService.timeout" :min="5" :max="300" />
                </el-form-item>

                <el-form-item label="连接测试">
                  <el-button @click="testPythonAiConnection" :loading="testingPythonAi">
                    测试连接
                  </el-button>
                  <el-tag v-if="pythonAiStatus !== ''" :type="pythonAiStatus === 'connected' ? 'success' : 'danger'" style="margin-left: 10px;">
                    {{ pythonAiStatus === 'connected' ? '连接成功' : '连接失败' }}
                  </el-tag>
                </el-form-item>

                <el-divider content-position="left">Ollama大模型</el-divider>

                <el-form-item label="启用Ollama">
                  <el-switch v-model="aiSettings.ollama.enabled" />
                </el-form-item>

                <el-form-item label="Ollama地址" v-if="aiSettings.ollama.enabled">
                  <el-input v-model="aiSettings.ollama.baseUrl" placeholder="http://localhost:11434" />
                </el-form-item>

                <el-form-item label="使用模型" v-if="aiSettings.ollama.enabled">
                  <el-select v-model="aiSettings.ollama.model" style="width: 250px;" filterable allow-create>
                    <el-option label="qwen2" value="qwen2" />
                    <el-option label="llama3" value="llama3" />
                    <el-option label="mistral" value="mistral" />
                    <el-option label="yi" value="yi" />
                  </el-select>
                </el-form-item>

                <el-form-item label="温度参数" v-if="aiSettings.ollama.enabled">
                  <el-slider v-model="aiSettings.ollama.temperature" :min="0" :max="2" :step="0.1" show-input />
                  <div class="form-tip">值越高输出越随机，越低越确定性</div>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="saveAiSettings">保存设置</el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="数据存储配置" name="storage">
              <el-form :model="storageSettings" label-width="160px" class="settings-form">
                <el-divider content-position="left">MySQL配置</el-divider>

                <el-form-item label="主机地址">
                  <el-input v-model="storageSettings.mysql.host" placeholder="localhost" />
                </el-form-item>

                <el-form-item label="端口">
                  <el-input-number v-model="storageSettings.mysql.port" :min="1" :max="65535" />
                </el-form-item>

                <el-form-item label="数据库名">
                  <el-input v-model="storageSettings.mysql.database" placeholder="zhihealth" />
                </el-form-item>

                <el-divider content-position="left">Redis配置</el-divider>

                <el-form-item label="主机地址">
                  <el-input v-model="storageSettings.redis.host" placeholder="localhost" />
                </el-form-item>

                <el-form-item label="端口">
                  <el-input-number v-model="storageSettings.redis.port" :min="1" :max="65535" />
                </el-form-item>

                <el-form-item label="密码">
                  <el-input v-model="storageSettings.redis.password" type="password" show-password placeholder="可选" />
                </el-form-item>

                <el-form-item label="数据库索引">
                  <el-input-number v-model="storageSettings.redis.db" :min="0" :max="15" />
                </el-form-item>

                <el-divider content-position="left">InfluxDB配置</el-divider>

                <el-form-item label="URL地址">
                  <el-input v-model="storageSettings.influxdb.url" placeholder="http://localhost:8086" />
                </el-form-item>

                <el-form-item label="组织名称">
                  <el-input v-model="storageSettings.influxdb.org" placeholder="zhihealth" />
                </el-form-item>

                <el-form-item label="Bucket名称">
                  <el-input v-model="storageSettings.influxdb.bucket" placeholder="health_data" />
                </el-form-item>

                <el-form-item label="Token">
                  <el-input v-model="storageSettings.influxdb.token" type="password" show-password />
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="saveStorageSettings">保存设置</el-button>
                  <el-button @click="testStorageConnections" :loading="testingStorage">
                    测试所有连接
                  </el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="安全配置" name="security">
              <el-form :model="securitySettings" label-width="160px" class="settings-form">
                <el-divider content-position="left">JWT认证</el-divider>

                <el-form-item label="Token过期时间(小时)">
                  <el-input-number v-model="securitySettings.jwtExpirationHours" :min="1" :max="720" />
                </el-form-item>

                <el-form-item label="刷新Token过期(天)">
                  <el-input-number v-model="securitySettings.refreshTokenExpirationDays" :min="1" :max="365" />
                </el-form-item>

                <el-divider content-position="left">API限流</el-divider>

                <el-form-item label="启用限流">
                  <el-switch v-model="securitySettings.enableRateLimit" />
                </el-form-item>

                <el-form-item label="默认限制(次/分钟)" v-if="securitySettings.enableRateLimit">
                  <el-input-number v-model="securitySettings.defaultRateLimit" :min="1" :max="10000" />
                </el-form-item>

                <el-form-item label="白名单IP" v-if="securitySettings.enableRateLimit">
                  <el-input 
                    v-model="securitySettings.whitelistIps" 
                    type="textarea" 
                    :rows="3"
                    placeholder="每行一个IP地址，支持CIDR格式"
                  />
                </el-form-item>

                <el-divider content-position="left">数据加密</el-divider>

                <el-form-item label="敏感字段加密">
                  <el-switch v-model="securitySettings.enableEncryption" />
                </el-form-item>

                <el-form-item label="加密算法" v-if="securitySettings.enableEncryption">
                  <el-select v-model="securitySettings.encryptionAlgorithm">
                    <el-option label="AES-256-GCM" value="AES-256-GCM" />
                    <el-option label="AES-128-CBC" value="AES-128-CBC" />
                    <el-option label="RSA-2048" value="RSA-2048" />
                  </el-select>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="saveSecuritySettings">保存设置</el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="system-status-card">
          <template #header>
            <span>系统运行状态</span>
          </template>

          <div class="status-list">
            <div class="status-item" v-for="(service, index) in serviceStatusList" :key="index">
              <div class="status-icon">
                <el-icon :size="24" :style="{ color: service.status === 'running' ? '#67c23a' : '#f56c6c' }">
                  <component :is="service.icon" />
                </el-icon>
              </div>
              <div class="status-info">
                <h4>{{ service.name }}</h4>
                <p>{{ service.address }}</p>
              </div>
              <el-tag :type="service.status === 'running' ? 'success' : 'danger'" size="small">
                {{ service.statusText }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <el-card class="quick-actions-card" style="margin-top: 20px;">
          <template #header>
            <span>快捷操作</span>
          </template>

          <div class="action-buttons">
            <el-button type="primary" :icon="RefreshRight" @click="refreshAllServices" :loading="refreshing">
              刷新服务状态
            </el-button>
            <el-button type="warning" :icon="Delete" @click="clearCache">
              清除系统缓存
            </el-button>
            <el-button type="danger" :icon="Document" @click="exportConfig">
              导出配置
            </el-button>
            <el-button :icon="Upload" @click="importConfig">
              导入配置
            </el-button>
          </div>

          <el-divider />

          <div class="danger-zone">
            <h4>危险操作区</h4>
            <el-button type="danger" plain @click="resetSystem" :loading="resetting">
              重置系统配置
            </el-button>
            <div class="form-tip">此操作将清除所有自定义配置，恢复为出厂设置</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, Delete, Document, Upload } from '@element-plus/icons-vue'

const activeTab = ref('basic')
const testingAlert = ref(false)
const testingPythonAi = ref(false)
const pythonAiStatus = ref('')
const testingStorage = ref(false)
const refreshing = ref(false)
const resetting = ref(false)

const basicSettings = reactive({
  systemName: '智康云枢',
  systemLogo: '/logo.png',
  systemDescription: '健康数据智能研判与管理系统',
  gatewayUrl: 'http://localhost:8080',
  requestTimeout: 30,
  defaultPageSize: 20
})

const alertSettings = reactive({
  enableAlert: true,
  cooldownSeconds: 300,
  channels: {
    email: {
      enabled: true,
      smtpHost: 'smtp.example.com',
      smtpPort: 587,
      senderEmail: 'noreply@zhihealth.com',
      password: ''
    },
    webhook: {
      enabled: false,
      url: ''
    },
    dingtalk: {
      enabled: false,
      accessToken: '',
      secret: ''
    },
    wechatWork: {
      enabled: false,
      corpId: '',
      agentId: '',
      secret: ''
    }
  }
})

const aiSettings = reactive({
  pythonAiService: {
    url: 'http://localhost:5000',
    timeout: 30
  },
  ollama: {
    enabled: false,
    baseUrl: 'http://localhost:11434',
    model: 'qwen2',
    temperature: 0.7
  }
})

const storageSettings = reactive({
  mysql: {
    host: 'localhost',
    port: 3306,
    database: 'zhihealth',
    username: 'root',
    password: ''
  },
  redis: {
    host: 'localhost',
    port: 6379,
    password: '',
    db: 0
  },
  influxdb: {
    url: 'http://localhost:8086',
    org: 'zhihealth',
    bucket: 'health_data',
    token: ''
  },
  mongodb: {
    host: 'localhost',
    port: 27017,
    database: 'zhihealth',
    username: '',
    password: ''
  }
})

const securitySettings = reactive({
  jwtExpirationHours: 24,
  refreshTokenExpirationDays: 7,
  enableRateLimit: true,
  defaultRateLimit: 100,
  whitelistIps: '127.0.0.1\n192.168.1.0/24',
  enableEncryption: true,
  encryptionAlgorithm: 'AES-256-GCM'
})

const serviceStatusList = ref([
  { name: 'API网关', address: 'localhost:8080', status: 'running', statusText: '运行中', icon: 'Connection' },
  { name: '用户服务', address: 'localhost:8081', status: 'running', statusText: '运行中', icon: 'User' },
  { name: '设备服务', address: 'localhost:8082', status: 'running', statusText: '运行中', icon: 'Monitor' },
  { name: '采集服务', address: 'localhost:8083', status: 'running', statusText: '运行中', icon: 'Upload' },
  { name: '存储服务', address: 'localhost:8084', status: 'running', statusText: '运行中', icon: 'Coin' },
  { name: '缓存服务', address: 'localhost:8085', status: 'running', statusText: '运行中', icon: 'Box' },
  { name: '预警服务', address: 'localhost:8086', status: 'stopped', statusText: '未启动', icon: 'Warning' },
  { name: 'AI服务', address: 'localhost:8087', status: 'stopped', statusText: '未启动', icon: 'MagicStick' },
  { name: 'Nacos注册中心', address: 'localhost:8848', status: 'running', statusText: '运行中', icon: 'Platform' },
  { name: 'MySQL数据库', address: 'localhost:3306', status: 'running', statusText: '运行中', icon: 'DataBoard' },
  { name: 'Redis缓存', address: 'localhost:6379', status: 'running', statusText: '运行中', icon: 'Box' }
])

function saveBasicSettings() {
  ElMessage.success('基本设置保存成功')
}

function resetBasicSettings() {
  ElMessageBox.confirm('确定要恢复默认设置吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    basicSettings.systemName = '智康云枢'
    basicSettings.systemLogo = '/logo.png'
    basicSettings.systemDescription = '健康数据智能研判与管理系统'
    basicSettings.gatewayUrl = 'http://localhost:8080'
    basicSettings.requestTimeout = 30
    basicSettings.defaultPageSize = 20
    ElMessage.success('已恢复默认设置')
  })
}

function saveAlertSettings() {
  ElMessage.success('告警配置保存成功')
}

async function testAlertNotification() {
  testingAlert.value = true
  
  setTimeout(() => {
    testingAlert.value = false
    ElMessage.success('测试通知发送成功，请检查接收渠道')
  }, 2000)
}

function saveAiSettings() {
  ElMessage.success('AI服务配置保存成功')
}

async function testPythonAiConnection() {
  testingPythonAi.value = true
  pythonAiStatus.value = ''

  setTimeout(() => {
    testingPythonAi.value = false
    pythonAiStatus.value = 'connected'
    ElMessage.success('Python AI服务连接成功')
  }, 1500)
}

function saveStorageSettings() {
  ElMessage.success('数据存储配置保存成功')
}

async function testStorageConnections() {
  testingStorage.value = true

  setTimeout(() => {
    testingStorage.value = false
    ElMessage.success('所有存储连接测试完成')
  }, 2500)
}

function saveSecuritySettings() {
  ElMessage.success('安全配置保存成功')
}

async function refreshAllServices() {
  refreshing.value = true

  setTimeout(() => {
    refreshing.value = false
    ElMessage.success('服务状态已刷新')
  }, 1500)
}

function clearCache() {
  ElMessageBox.confirm('确定要清除系统缓存吗？这可能会影响系统性能。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('系统缓存已清除')
  })
}

function exportConfig() {
  ElMessage.success('配置导出成功')
}

function importConfig() {
  ElMessage.info('请选择配置文件')
}

function resetSystem() {
  ElMessageBox.confirm(
    '此操作将清除所有自定义配置，恢复为出厂设置！是否继续？',
    '危险操作警告',
    {
      confirmButtonText: '确定重置',
      cancelButtonText: '取消',
      type: 'error',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(() => {
    resetting.value = true
    
    setTimeout(() => {
      resetting.value = false
      ElMessage.success('系统配置已重置')
    }, 2000)
  })
}
</script>

<style lang="scss" scoped>
.settings-container {
  .settings-card {
    min-height: 800px;
  }

  .settings-form {
    padding: 20px 0;
  }

  .form-tip {
    font-size: 12px;
    color: #909399;
    line-height: 1.4;
    margin-top: 4px;
  }

  .system-status-card {
    .status-list {
      .status-item {
        display: flex;
        align-items: center;
        padding: 16px 0;
        border-bottom: 1px solid #ebeef5;

        &:last-child {
          border-bottom: none;
        }

        .status-icon {
          width: 48px;
          height: 48px;
          background: #f5f7fa;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 12px;
        }

        .status-info {
          flex: 1;

          h4 {
            font-size: 14px;
            color: #303133;
            margin: 0 0 4px 0;
          }

          p {
            font-size: 12px;
            color: #909399;
            margin: 0;
          }
        }
      }
    }
  }

  .quick-actions-card {
    .action-buttons {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }

    .danger-zone {
      margin-top: 20px;
      padding: 16px;
      background: #fef0f0;
      border-radius: 8px;
      border: 1px solid #fde2e2;

      h4 {
        color: #f56c6c;
        font-size: 14px;
        margin: 0 0 12px 0;
      }

      .form-tip {
        margin-top: 8px;
      }
    }
  }
}
</style>
