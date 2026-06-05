<template>
  <div class="alert-container">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="alert-stats">
      <el-col :span="6" v-for="(stat, index) in alertStats" :key="index">
        <el-card shadow="hover" class="stat-card" :style="{ borderLeftColor: stat.color }">
          <div class="stat-content">
            <h3>{{ stat.value }}</h3>
            <p>{{ stat.label }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Tab切换 -->
    <el-card shadow="hover" style="margin-top: 20px;">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 预警记录 Tab -->
        <el-tab-pane label="预警记录" name="records">
          <div class="tab-header">
            <el-button-group>
              <el-button
                :type="currentLevel === '' ? 'primary' : ''"
                size="small"
                @click="currentLevel = ''; loadRecords()"
              >全部</el-button>
              <el-button
                :type="currentLevel === 'critical' ? 'danger' : ''"
                size="small"
                @click="currentLevel = 'critical'; loadRecords()"
              >严重</el-button>
              <el-button
                :type="currentLevel === 'warning' ? 'warning' : ''"
                size="small"
                @click="currentLevel = 'warning'; loadRecords()"
              >警告</el-button>
              <el-button
                :type="currentLevel === 'info' ? 'info' : ''"
                size="small"
                @click="currentLevel = 'info'; loadRecords()"
              >提醒</el-button>
            </el-button-group>
            <el-button type="primary" size="small" :icon="Download" @click="exportRecords">导出</el-button>
          </div>

          <el-table :data="recordData" stripe border style="width: 100%" v-loading="loading">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="ruleName" label="规则名称" width="150" />
            <el-table-column prop="dataType" label="数据类型" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ getDataTypeName(row.dataType) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="level" label="级别" width="90">
              <template #default="{ row }">
                <el-tag :type="getLevelType(row.level)" size="small">{{ getLevelName(row.level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="预警信息" min-width="220" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'resolved' ? 'success' : 'warning'" size="small">
                  {{ row.status === 'resolved' ? '已处理' : '待处理' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="triggerTime" label="触发时间" width="170" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" :disabled="row.status === 'resolved'" @click="handleResolve(row)">处理</el-button>
                <el-button type="primary" link size="small" @click="handleDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="pagination.pageNum"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 16px; justify-content: flex-end;"
            @size-change="loadRecords"
            @current-change="loadRecords"
          />
        </el-tab-pane>

        <!-- 预警规则管理 Tab -->
        <el-tab-pane label="规则管理" name="rules">
          <div class="tab-header">
            <el-button type="primary" size="small" :icon="Plus" @click="openRuleDialog()">新增规则</el-button>
            <el-input v-model="ruleSearchKey" placeholder="搜索规则名称" clearable size="small" style="width: 200px;" @clear="loadRules" @keyup.enter="loadRules" />
          </div>

          <el-table :data="ruleData" stripe border style="width: 100%;" v-loading="rulesLoading">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="ruleName" label="规则名称" min-width="140" />
            <el-table-column prop="dataType" label="数据类型" width="120">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ getDataTypeName(row.dataType) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="condition" label="条件表达式" min-width="160" show-overflow-tooltip />
            <el-table-column prop="threshold" label="阈值" width="100" />
            <el-table-column prop="level" label="默认级别" width="100">
              <template #default="{ row }">
                <el-tag :type="getLevelType(row.level)" size="small">{{ getLevelName(row.level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="状态" width="80">
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  active-text="启用"
                  inactive-text="禁用"
                  @change="toggleRuleStatus(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openRuleDialog(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="deleteRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 规则编辑弹窗 -->
    <el-dialog
      v-model="ruleDialogVisible"
      :title="editingRule.id ? '编辑预警规则' : '新增预警规则'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="ruleFormRef" :model="editingRule" :rules="ruleFormRules" label-width="110px">
        <el-form-item label="规则名称" prop="ruleName">
          <el-input v-model="editingRule.ruleName" placeholder="例如：心率过高预警" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="数据类型" prop="dataType">
          <el-select v-model="editingRule.dataType" placeholder="选择数据类型" style="width: 100%;">
            <el-option label="心率 (heart_rate)" value="heart_rate" />
            <el-option label="血压 (blood_pressure)" value="blood_pressure" />
            <el-option label="血氧 (blood_oxygen)" value="blood_oxygen" />
            <el-option label="体温 (temperature)" value="temperature" />
            <el-option label="血糖 (blood_sugar)" value="blood_sugar" />
            <el-option label="步数 (steps)" value="steps" />
            <el-option label="睡眠质量 (sleep_quality)" value="sleep_quality" />
            <el-option label="体重 (weight)" value="weight" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件运算符" prop="condition">
          <el-select v-model="editingRule.condition" placeholder="选择条件" style="width: 100%;">
            <el-option label="大于 (>)" value="gt" />
            <el-option label="大于等于 (>=)" value="gte" />
            <el-option label="小于 (<)" value="lt" />
            <el-option label="小于等于 (<=)" value="lte" />
            <el-option label="等于 (=)" value="eq" />
            <el-option label="不等于 (!=)" value="neq" />
            <el-option label="超出范围" value="out_of_range" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值/范围" prop="threshold">
          <el-input v-model="editingRule.threshold" placeholder="例如：120 或 90-140（范围）" />
          <div class="form-tip">数值型填具体值，范围型填 min-max 格式</div>
        </el-form-item>
        <el-form-item label="预警级别" prop="level">
          <el-radio-group v-model="editingRule.level">
            <el-radio label="critical">严重</el-radio>
            <el-radio label="warning">警告</el-radio>
            <el-radio label="info">提醒</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="预警消息模板" prop="messageTemplate">
          <el-input
            v-model="editingRule.messageTemplate"
            type="textarea"
            :rows="3"
            placeholder="支持变量: {value} {dataType} {threshold} {time}"
          />
        </el-form-item>
        <el-form-item label="冷却时间(秒)" prop="cooldownSeconds">
          <el-input-number v-model="editingRule.cooldownSeconds" :min="0" :max="86400" :step="60" />
          <span class="form-tip">同一规则触发后冷却时间，防止重复告警</span>
        </el-form-item>
        <el-form-item label="通知方式" prop="notifyChannels">
          <el-checkbox-group v-model="editingRule.notifyChannels">
            <el-checkbox label="system">系统通知</el-checkbox>
            <el-checkbox label="email">邮件通知</el-checkbox>
            <el-checkbox label="sms">短信通知</el-checkbox>
            <el-checkbox label="wechat">微信通知</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="ruleSaving" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download } from '@element-plus/icons-vue'
import { getAlertRecordList, resolveAlert, exportAlertRecords, getAlertRuleList, createAlertRule, updateAlertRule, deleteAlertRule, toggleAlertRule, getAlertStatistics } from '@/api/alert'

// ==================== 预警记录 ====================
const recordData = ref([])
const currentLevel = ref('')
const loading = ref(false)
const activeTab = ref('records')

const alertStats = ref([
  { label: '今日预警总数', value: 15, color: '#409eff' },
  { label: '待处理', value: 8, color: '#e6a23c' },
  { label: '严重预警', value: 2, color: '#f56c6c' },
  { label: '已处理', value: 7, color: '#67c23a' }
])

const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

function getDataTypeName(type) {
  const map = {
    heart_rate: '心率', blood_pressure: '血压', blood_oxygen: '血氧',
    temperature: '体温', blood_sugar: '血糖', steps: '步数',
    sleep_quality: '睡眠', weight: '体重'
  }
  return map[type] || type
}

function getLevelType(level) {
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[level] || ''
}

function getLevelName(level) {
  const map = { critical: '严重', warning: '警告', info: '提醒' }
  return map[level] || level
}

async function loadRecords() {
  loading.value = true
  try {
    const params = { pageNum: pagination.pageNum, pageSize: pagination.pageSize, level: currentLevel.value || undefined }
    const res = await api.get('/alert/record/list', { params })
    if (res.code === 200) {
      recordData.value = res.data?.records || []
      pagination.total = res.data?.total || 0
    }
  } catch (error) {
    console.error('加载预警记录失败:', error)
  } finally {
    loading.value = false
  }
}

async function handleResolve(row) {
  try {
    await ElMessageBox.confirm('确定标记该预警为已处理吗？', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'info'
    })
    await api.put(`/alert/record/${row.id}/resolve`)
    ElMessage.success('处理成功')
    loadRecords()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('处理失败')
  }
}

function handleDetail(row) {
  ElMessageBox.alert(
    `<p><strong>规则名称：</strong>${row.ruleName}</p>` +
    `<p><strong>数据类型：</strong>${getDataTypeName(row.dataType)}</p>` +
    `<p><strong>预警级别：</strong>${getLevelName(row.level)}</p>` +
    `<p><strong>预警信息：</strong>${row.message}</p>` +
    `<p><strong>触发时间：</strong>${row.triggerTime}</p>` +
    `<p><strong>当前状态：</strong>${row.status === 'resolved' ? '已处理' : '待处理'}</p>`,
    '预警详情',
    { dangerouslyUseHTMLString: true }
  )
}

async function exportRecords() {
  try {
    const params = { level: currentLevel.value || undefined }
    const res = await api.get('/alert/record/export', { params, responseType: 'blob' })
    // 处理文件下载
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `预警记录_${new Date().toLocaleDateString()}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// ==================== 规则管理 ====================
const ruleData = ref([])
const rulesLoading = ref(false)
const ruleSearchKey = ref('')
const ruleDialogVisible = ref(false)
const ruleSaving = ref(false)
const ruleFormRef = ref(null)

const editingRule = reactive({
  id: null,
  ruleName: '',
  dataType: '',
  condition: '',
  threshold: '',
  level: 'warning',
  messageTemplate: '',
  cooldownSeconds: 300,
  enabled: true,
  notifyChannels: ['system']
})

const ruleFormRules = {
  ruleName: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  dataType: [{ required: true, message: '请选择数据类型', trigger: 'change' }],
  condition: [{ required: true, message: '请选择条件运算符', trigger: 'change' }],
  threshold: [{ required: true, message: '请输入阈值', trigger: 'blur' }],
  level: [{ required: true, message: '请选择预警级别', trigger: 'change' }]
}

function resetEditingRule() {
  Object.assign(editingRule, {
    id: null,
    ruleName: '',
    dataType: '',
    condition: '',
    threshold: '',
    level: 'warning',
    messageTemplate: '',
    cooldownSeconds: 300,
    enabled: true,
    notifyChannels: ['system']
  })
}

function openRuleDialog(rule) {
  resetEditingRule()
  if (rule) {
    Object.assign(editingRule, JSON.parse(JSON.stringify(rule)))
  }
  ruleDialogVisible.value = true
}

async function loadRules() {
  rulesLoading.value = true
  try {
    const params = {}
    if (ruleSearchKey.value) params.keyword = ruleSearchKey.value
    const res = await getAlertRuleList(params)
    if (res.code === 200) {
      ruleData.value = res.data || []
    }
  } catch (error) {
    console.error('加载预警规则失败:', error)
  } finally {
    rulesLoading.value = false
  }
}

async function saveRule() {
  try {
    await ruleFormRef.value.validate()
  } catch {
    return
  }

  ruleSaving.value = true
  try {
    const payload = { ...editingRule }
    let res
    if (payload.id) {
      res = await api.put(`/alert/rule/${payload.id}`, payload)
    } else {
      res = await api.post('/alert/rule', payload)
    }

    if (res.code === 200) {
      ElMessage.success(payload.id ? '规则更新成功' : '规则创建成功')
      ruleDialogVisible.value = false
      loadRules()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    ruleSaving.value = false
  }
}

async function deleteRule(row) {
  try {
    await ElMessageBox.confirm(`确定删除规则「${row.ruleName}」吗？此操作不可恢复。`, '警告', {
      confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteAlertRule(row.id)
    ElMessage.success('删除成功')
    loadRules()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

async function toggleRuleStatus(row) {
  try {
    await toggleAlertRule(row.id, row.enabled)
    ElMessage.success(row.enabled ? '已启用' : '已禁用')
  } catch (error) {
    row.enabled = !row.enabled
    ElMessage.error('状态更新失败')
  }
}

function handleTabChange(tab) {
  if (tab === 'rules') loadRules()
}

onMounted(() => {
  loadRecords()
})
</script>

<style lang="scss" scoped>
.alert-container {
  .alert-stats {
    .stat-card {
      border-left: 4px solid;
      .stat-content {
        h3 { font-size: 28px; font-weight: bold; margin-bottom: 8px; }
        p { font-size: 14px; color: #999; }
      }
    }
  }

  .tab-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .form-tip {
    font-size: 12px;
    color: #999;
    margin-left: 4px;
  }
}
</style>
