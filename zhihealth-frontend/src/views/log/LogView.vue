<template>
  <div class="log-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span>系统操作日志</span>
          <div class="header-actions">
            <el-button type="danger" plain :icon="Delete" @click="clearLogs" :disabled="selectedRows.length === 0">
              批量删除 ({{ selectedRows.length }})
            </el-button>
            <el-button type="primary" :icon="Download" @click="exportLogs">
              导出日志
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-form :inline="true" :model="queryParams" class="filter-form">
          <el-form-item label="操作类型">
            <el-select v-model="queryParams.actionType" placeholder="全部类型" clearable style="width: 150px;">
              <el-option label="登录/登出" value="auth" />
              <el-option label="数据操作" value="data" />
              <el-option label="系统配置" value="config" />
              <el-option label="告警处理" value="alert" />
              <el-option label="AI分析" value="ai" />
              <el-option label="文件操作" value="file" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>

          <el-form-item label="操作人">
            <el-input v-model="queryParams.operator" placeholder="输入操作人" clearable style="width: 150px;" />
          </el-form-item>

          <el-form-item label="操作模块">
            <el-select v-model="queryParams.module" placeholder="全部模块" clearable style="width: 150px;">
              <el-option label="用户管理" value="user" />
              <el-option label="设备管理" value="device" />
              <el-option label="数据采集" value="collect" />
              <el-option label="数据存储" value="storage" />
              <el-option label="预警中心" value="alert" />
              <el-option label="AI分析" value="ai" />
              <el-option label="系统设置" value="settings" />
              <el-option label="报告中心" value="report" />
            </el-select>
          </el-form-item>

          <el-form-item label="执行结果">
            <el-select v-model="queryParams.result" placeholder="全部结果" clearable style="width: 130px;">
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
              <el-option label="异常" value="error" />
            </el-select>
          </el-form-item>

          <el-form-item label="时间范围">
            <el-date-picker
              v-model="queryParams.dateRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 340px;"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
            <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        :data="logList"
        v-loading="loading"
        border
        stripe
        style="width: 100%;"
        @selection-change="handleSelectionChange"
        :default-sort="{ prop: 'operateTime', order: 'descending' }"
      >
        <el-table-column type="selection" width="50" align="center" />

        <el-table-column prop="id" label="序号" width="70" align="center" />

        <el-table-column prop="operator" label="操作人" width="110" align="center">
          <template #default="{ row }">
            <el-avatar :size="24" style="vertical-align: middle; margin-right: 6px;">
              {{ row.operator.charAt(0) }}
            </el-avatar>
            {{ row.operator }}
          </template>
        </el-table-column>

        <el-table-column prop="module" label="操作模块" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ getModuleName(row.module) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="actionType" label="操作类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getActionTypeTag(row.actionType)" size="small">
              {{ getActionTypeName(row.actionType) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="操作描述" min-width="220" show-overflow-tooltip />

        <el-table-column prop="ipAddress" label="IP地址" width="140" align="center" />

        <el-table-column prop="result" label="执行结果" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : row.result === 'failed' ? 'danger' : 'warning'" size="small">
              {{ getResultName(row.result) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="duration" label="耗时(ms)" width="95" align="center" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.duration > 1000 ? '#f56c6c' : '#67c23a' }">
              {{ row.duration }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="operateTime" label="操作时间" width="170" align="center" sortable />

        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="showDetailDialog" title="日志详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="日志ID">{{ currentLog.id }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ currentLog.operator }}</el-descriptions-item>
        <el-descriptions-item label="操作模块">{{ getModuleName(currentLog.module) }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ getActionTypeName(currentLog.actionType) }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog.ipAddress }}</el-descriptions-item>
        <el-descriptions-item label="执行结果">
          <el-tag :type="currentLog.result === 'success' ? 'success' : 'danger'">
            {{ getResultName(currentLog.result) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentLog.duration }}ms</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ currentLog.operateTime }}</el-descriptions-item>
        <el-descriptions-item label="操作描述" :span="2">{{ currentLog.description }}</el-descriptions-item>
        <el-descriptions-item label="请求参数" :span="2">
          <pre class="json-preview">{{ currentLog.requestParams || '{}' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="响应结果" :span="2">
          <pre class="json-preview">{{ currentLog.responseData || '{}' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="异常信息" :span="2" v-if="currentLog.errorMessage">
          <el-alert :title="currentLog.errorMessage" type="error" :closable="false" />
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Delete, Download } from '@element-plus/icons-vue'

const loading = ref(false)
const showDetailDialog = ref(false)
const selectedRows = ref([])
const total = ref(0)

const queryParams = reactive({
  actionType: '',
  operator: '',
  module: '',
  result: '',
  dateRange: null,
  pageNum: 1,
  pageSize: 20
})

const currentLog = ref({})

const logList = ref([
  {
    id: 1,
    operator: '管理员',
    module: 'user',
    actionType: 'auth',
    description: '用户登录系统',
    ipAddress: '192.168.1.100',
    result: 'success',
    duration: 156,
    operateTime: '2026-06-02 14:30:25',
    requestParams: '{"username": "admin", "password": "***"}',
    responseData: '{"code": 200, "msg": "登录成功", "token": "eyJhbGciOiJIUzI1NiJ9..."}',
    errorMessage: null
  },
  {
    id: 2,
    operator: '管理员',
    module: 'device',
    actionType: 'data',
    description: '新增设备绑定：智能手环-BandPro-X1',
    ipAddress: '192.168.1.100',
    result: 'success',
    duration: 89,
    operateTime: '2026-06-02 14:28:13',
    requestParams: '{"deviceName": "BandPro-X1", "deviceType": "wearable"}',
    responseData: '{"code": 200, "msg": "添加成功", "data": {"deviceId": 10001}}',
    errorMessage: null
  },
  {
    id: 3,
    operator: '张三',
    module: 'alert',
    actionType: 'config',
    description: '修改告警规则：高血压阈值调整为140/90',
    ipAddress: '192.168.1.105',
    result: 'success',
    duration: 234,
    operateTime: '2026-06-02 14:15:42',
    requestParams: '{"ruleId": 5, "threshold": 140}',
    responseData: '{"code": 200, "msg": "更新成功"}',
    errorMessage: null
  },
  {
    id: 4,
    operator: '李四',
    module: 'ai',
    actionType: 'data',
    description: '执行AI健康数据分析（用户ID: 1002）',
    ipAddress: '192.168.1.108',
    result: 'success',
    duration: 3456,
    operateTime: '2026-06-02 13:52:18',
    requestParams: '{"userId": 1002, "analysisType": "comprehensive"}',
    responseData: '{"code": 200, "msg": "分析完成", "confidenceScore": 0.92}',
    errorMessage: null
  },
  {
    id: 5,
    operator: '王五',
    module: 'data',
    actionType: 'data',
    description: '批量导入健康数据（共1256条记录）',
    ipAddress: '192.168.1.112',
    result: 'failed',
    duration: 5678,
    operateTime: '2026-06-02 13:28:55',
    requestParams: '{"file": "health_data_202606.csv", "count": 1256}',
    responseData: '{}',
    errorMessage: '数据格式校验失败：第456行血糖值超出合理范围(0-30)'
  },
  {
    id: 6,
    operator: '赵六',
    module: 'report',
    actionType: 'file',
    description: '导出PDF健康报告（用户ID: 1005）',
    ipAddress: '192.168.1.115',
    result: 'success',
    duration: 12345,
    operateTime: '2026-06-02 12:45:33',
    requestParams: '{"userId": 1005, "format": "pdf", "includeCharts": true}',
    responseData: '{"code": 200, "msg": "导出成功", "filePath": "/reports/report_1005_20260602.pdf"}',
    errorMessage: null
  },
  {
    id: 7,
    operator: '系统定时任务',
    module: 'collect',
    actionType: 'data',
    description: '自动执行ETL数据清洗任务',
    ipAddress: '127.0.0.1',
    result: 'success',
    duration: 8923,
    operateTime: '2026-06-02 12:00:00',
    requestParams: '{"taskType": "etl_clean", "schedule": "0 0 12 * * *"}',
    responseData: '{"processed": 8923, "cleaned": 156, "errors": 3}',
    errorMessage: null
  },
  {
    id: 8,
    operator: '管理员',
    module: 'settings',
    actionType: 'config',
    description: '修改系统配置：AI服务超时时间从30s改为60s',
    ipAddress: '192.168.1.100',
    result: 'success',
    duration: 178,
    operateTime: '2026-06-02 11:30:22',
    requestParams: '{"key": "ai.timeout", "oldValue": 30, "newValue": 60}',
    responseData: '{"code": 200, "msg": "配置更新成功"}',
    errorMessage: null
  },
  {
    id: 9,
    operator: '钱七',
    module: 'user',
    actionType: 'auth',
    description: '用户登录失败：密码错误（尝试次数：3/5）',
    ipAddress: '192.168.1.120',
    result: 'failed',
    duration: 45,
    operateTime: '2026-06-02 10:15:08',
    requestParams: '{"username": "qianqi", "password": "***"}',
    responseData: '{"code": 401, "msg": "用户名或密码错误"}',
    errorMessage: '认证失败：密码不匹配'
  },
  {
    id: 10,
    operator: '孙八',
    module: 'storage',
    actionType: 'other',
    description: '手动触发数据库备份任务',
    ipAddress: '192.168.1.125',
    result: 'success',
    duration: 45678,
    operateTime: '2026-06-02 09:00:00',
    requestParams: '{"backupType": "full", "compress": true}',
    responseData: '{"code": 200, "msg": "备份完成", "fileSize": "2.3GB", "path": "/backups/full_20260602.sql.gz"}',
    errorMessage: null
  }
])

function getModuleName(module) {
  const map = {
    user: '用户管理',
    device: '设备管理',
    collect: '数据采集',
    storage: '数据存储',
    alert: '预警中心',
    ai: 'AI分析',
    settings: '系统设置',
    report: '报告中心'
  }
  return map[module] || module
}

function getActionTypeName(type) {
  const map = {
    auth: '登录/登出',
    data: '数据操作',
    config: '系统配置',
    alert: '告警处理',
    ai: 'AI分析',
    file: '文件操作',
    other: '其他'
  }
  return map[type] || type
}

function getActionTypeTag(type) {
  const map = {
    auth: '',
    data: 'success',
    config: 'warning',
    alert: 'danger',
    ai: 'info',
    file: 'info',
    other: 'info'
  }
  return map[type] || ''
}

function getResultName(result) {
  const map = {
    success: '成功',
    failed: '失败',
    error: '异常'
  }
  return map[result] || result
}

function handleQuery() {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    total.value = logList.value.length
  }, 500)
}

function resetQuery() {
  queryParams.actionType = ''
  queryParams.operator = ''
  queryParams.module = ''
  queryParams.result = ''
  queryParams.dateRange = null
  queryParams.pageNum = 1
  handleQuery()
}

function handleSizeChange(val) {
  queryParams.pageSize = val
  handleQuery()
}

function handleCurrentChange(val) {
  queryParams.pageNum = val
  handleQuery()
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function viewDetail(row) {
  currentLog.value = { ...row }
  showDetailDialog.value = true
}

function clearLogs() {
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 条日志记录吗？`,
    '批量删除确认',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    const ids = selectedRows.value.map(row => row.id)
    logList.value = logList.value.filter(item => !ids.includes(item.id))
    total.value -= ids.length
    selectedRows.value = []
    ElMessage.success(`成功删除 ${ids.length} 条日志`)
  })
}

function exportLogs() {
  ElMessage.success('日志导出任务已启动，请稍候下载')
}
</script>

<style lang="scss" scoped>
.log-container {
  .page-card {
    margin-bottom: 20px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-actions {
    display: flex;
    gap: 10px;
  }

  .filter-bar {
    margin-bottom: 20px;
    
    .filter-form {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
  }

  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }

  .json-preview {
    background: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
  }
}
</style>
