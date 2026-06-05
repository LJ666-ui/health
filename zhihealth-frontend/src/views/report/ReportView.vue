<template>
  <div class="report-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span>健康报告中心</span>
          <el-button type="primary" :icon="DocumentAdd" @click="showGenerateDialog = true">
            生成报告
          </el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-form :inline="true" :model="queryParams" class="filter-form">
          <el-form-item label="报告类型">
            <el-select v-model="queryParams.reportType" placeholder="全部类型" clearable style="width: 150px;">
              <el-option label="综合健康报告" value="comprehensive" />
              <el-option label="专项分析报告" value="specialized" />
              <el-option label="趋势预测报告" value="trend" />
              <el-option label="异常检测报告" value="anomaly" />
            </el-select>
          </el-form-item>

          <el-form-item label="时间范围">
            <el-date-picker
              v-model="queryParams.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 260px;"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
            <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table :data="reportList" v-loading="loading" border stripe style="width: 100%;">
        <el-table-column prop="id" label="报告ID" width="80" align="center" />
        
        <el-table-column prop="title" label="报告标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" @click="viewReport(row)">{{ row.title }}</el-link>
          </template>
        </el-table-column>

        <el-table-column prop="reportType" label="报告类型" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="getReportTypeTag(row.reportType)">
              {{ getReportTypeName(row.reportType) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="userId" label="用户ID" width="100" align="center" />

        <el-table-column prop="generateTime" label="生成时间" width="170" align="center" />

        <el-table-column prop="format" label="格式" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.format.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="fileSize" label="大小" width="90" align="center">
          <template #default="{ row }">
            {{ formatFileSize(row.fileSize) }}
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'generating' ? 'warning' : 'danger'">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" :icon="View" @click="viewReport(row)" :disabled="row.status !== 'completed'">
              查看
            </el-button>
            <el-button link type="primary" size="small" :icon="Download" @click="downloadReport(row)" :disabled="row.status !== 'completed'">
              下载
            </el-button>
            <el-button link type="danger" size="small" :icon="Delete" @click="deleteReport(row)">
              删除
            </el-button>
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

    <el-dialog
      v-model="showGenerateDialog"
      title="生成健康报告"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form ref="generateFormRef" :model="generateForm" :rules="generateRules" label-width="120px">
        <el-form-item label="报告类型" prop="reportType">
          <el-select v-model="generateForm.reportType" placeholder="请选择报告类型" style="width: 100%;">
            <el-option label="综合健康报告" value="comprehensive" />
            <el-option label="专项分析报告" value="specialized" />
            <el-option label="趋势预测报告" value="trend" />
            <el-option label="异常检测报告" value="anomaly" />
          </el-select>
        </el-form-item>

        <el-form-item label="用户ID" prop="userId">
          <el-input-number v-model="generateForm.userId" :min="1" :max="99999" style="width: 100%;" />
        </el-form-item>

        <el-form-item label="数据范围" prop="dateRange">
          <el-date-picker
            v-model="generateForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="输出格式" prop="format">
          <el-radio-group v-model="generateForm.format">
            <el-radio label="pdf">PDF</el-radio>
            <el-radio label="excel">Excel</el-radio>
            <el-radio label="word">Word</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="包含内容" prop="includeContent">
          <el-checkbox-group v-model="generateForm.includeContent">
            <el-checkbox label="healthData">基础健康数据</el-checkbox>
            <el-checkbox label="trendAnalysis">趋势分析图表</el-checkbox>
            <el-checkbox label="aiInsights">AI智能洞察</el-checkbox>
            <el-checkbox label="recommendations">健康建议</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          {{ generating ? '生成中...' : '确认生成' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPreviewDialog" title="报告预览" width="900px" top="5vh">
      <div class="report-preview">
        <div class="preview-header">
          <h2>{{ currentReport.title }}</h2>
          <div class="meta-info">
            <span>生成时间：{{ currentReport.generateTime }}</span>
            <span>格式：{{ currentReport.format?.toUpperCase() }}</span>
          </div>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="概览" name="overview">
            <div class="section">
              <h3>执行摘要</h3>
              <p>{{ currentReport.summary || '本报告基于用户近期的健康数据进行全面分析，包含基础指标评估、趋势分析、AI智能诊断及个性化健康建议。' }}</p>
              
              <el-row :gutter="20" class="summary-cards">
                <el-col :span="8" v-for="(item, index) in summaryCards" :key="index">
                  <el-card shadow="hover" class="summary-card">
                    <h4>{{ item.value }}</h4>
                    <p>{{ item.label }}</p>
                  </el-card>
                </el-col>
              </el-row>
            </div>
          </el-tab-pane>

          <el-tab-pane label="详细分析" name="analysis">
            <div class="section">
              <h3>健康指标分析</h3>
              <v-chart :option="healthMetricsChartOption" style="height: 350px;" autoresize />
            </div>

            <div class="section">
              <h3>趋势变化</h3>
              <v-chart :option="trendChartOption" style="height: 350px;" autoresize />
            </div>
          </el-tab-pane>

          <el-tab-pane label="AI洞察" name="insights">
            <div class="section">
              <h3>AI智能分析结果</h3>
              <el-alert
                v-for="(insight, index) in aiInsights"
                :key="index"
                :title="insight.title"
                :description="insight.description"
                :type="insight.type"
                :closable="false"
                show-icon
                style="margin-bottom: 12px;"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane label="健康建议" name="recommendations">
            <div class="section">
              <h3>个性化健康建议</h3>
              <el-timeline>
                <el-timeline-item
                  v-for="(rec, index) in recommendations"
                  :key="index"
                  :timestamp="rec.timestamp"
                  placement="top"
                  :color="rec.color"
                >
                  <el-card>
                    <h4>{{ rec.title }}</h4>
                    <p>{{ rec.content }}</p>
                  </el-card>
                </el-timeline-item>
              </el-timeline>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, DocumentAdd, View, Download, Delete } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const generating = ref(false)
const showGenerateDialog = ref(false)
const showPreviewDialog = ref(false)
const activeTab = ref('overview')
const total = ref(0)

const queryParams = reactive({
  reportType: '',
  dateRange: null,
  pageNum: 1,
  pageSize: 10
})

const generateFormRef = ref()
const generateForm = reactive({
  reportType: '',
  userId: 1,
  dateRange: [],
  format: 'pdf',
  includeContent: ['healthData', 'trendAnalysis']
})

const generateRules = {
  reportType: [{ required: true, message: '请选择报告类型', trigger: 'change' }],
  userId: [{ required: true, message: '请输入用户ID', trigger: 'blur' }],
  dateRange: [{ required: true, message: '请选择数据范围', trigger: 'change' }],
  format: [{ required: true, message: '请选择输出格式', trigger: 'change' }]
}

const currentReport = ref({})

const reportList = ref([
  {
    id: 1,
    title: '张三 - 2026年5月综合健康报告',
    reportType: 'comprehensive',
    userId: 1,
    generateTime: '2026-06-01 14:30:00',
    format: 'pdf',
    fileSize: 2458624,
    status: 'completed'
  },
  {
    id: 2,
    title: '李四 - 心血管专项分析报告',
    reportType: 'specialized',
    userId: 2,
    generateTime: '2026-06-01 16:45:00',
    format: 'excel',
    fileSize: 1536000,
    status: 'completed'
  },
  {
    id: 3,
    title: '王五 - 健康趋势预测报告',
    reportType: 'trend',
    userId: 3,
    generateTime: '2026-06-02 09:15:00',
    format: 'pdf',
    fileSize: 0,
    status: 'generating'
  },
  {
    id: 4,
    title: '赵六 - 异常检测分析报告',
    reportType: 'anomaly',
    userId: 4,
    generateTime: '2026-06-02 11:20:00',
    format: 'word',
    fileSize: 982000,
    status: 'completed'
  }
])

const summaryCards = ref([
  { value: '良好', label: '整体健康状况', color: '#67c23a' },
  { value: '3项', label: '关注指标数量', color: '#e6a23c' },
  { value: '92分', label: '健康评分', color: '#409eff' }
])

const healthMetricsChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['血压', '心率', '血糖'] },
  xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
  yAxis: { type: 'value' },
  series: [
    { name: '血压', type: 'line', data: [120, 118, 125, 122, 119, 121, 117], smooth: true },
    { name: '心率', type: 'line', data: [72, 75, 70, 73, 71, 74, 72], smooth: true },
    { name: '血糖', type: 'line', data: [5.2, 5.4, 5.1, 5.3, 5.5, 5.2, 5.1], smooth: true }
  ]
}))

const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['第1周', '第2周', '第3周', '第4周'] },
  yAxis: { type: 'value', name: '健康指数' },
  series: [
    { name: '健康指数', type: 'bar', data: [78, 82, 85, 88], itemStyle: { color: '#409eff' } }
  ]
}))

const aiInsights = ref([
  { title: '心血管状态稳定', description: '近期血压和心率数据均在正常范围内波动，整体心血管功能表现良好。', type: 'success' },
  { title: '血糖需持续关注', description: '空腹血糖值偶有偏高现象，建议控制碳水化合物摄入并定期监测。', type: 'warning' },
  { title: '睡眠质量待改善', description: '根据设备监测数据显示，深睡比例偏低，建议调整作息规律。', type: 'info' }
])

const recommendations = ref([
  { timestamp: '立即执行', title: '饮食调整', content: '减少高盐高脂食物摄入，增加蔬菜水果比例，每日饮水量保持在2000ml以上。', color: '#f56c6c' },
  { timestamp: '本周内', title: '运动计划', content: '每周至少进行3次有氧运动，每次30分钟以上，推荐快走或游泳。', color: '#e6a23c' },
  { timestamp: '本月内', title: '定期检查', content: '建议完成年度体检，重点关注血脂、肝肾功能等指标。', color: '#409eff' }
])

function getReportTypeName(type) {
  const map = {
    comprehensive: '综合健康报告',
    specialized: '专项分析报告',
    trend: '趋势预测报告',
    anomaly: '异常检测报告'
  }
  return map[type] || type
}

function getReportTypeTag(type) {
  const map = {
    comprehensive: '',
    specialized: 'success',
    trend: 'warning',
    anomaly: 'danger'
  }
  return map[type] || ''
}

function getStatusName(status) {
  const map = {
    completed: '已完成',
    generating: '生成中',
    failed: '失败'
  }
  return map[status] || status
}

function formatFileSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function handleQuery() {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    total.value = reportList.value.length
  }, 500)
}

function resetQuery() {
  queryParams.reportType = ''
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

async function handleGenerate() {
  await generateFormRef.value.validate((valid) => {
    if (valid) {
      generating.value = true
      
      setTimeout(() => {
        const newReport = {
          id: reportList.value.length + 1,
          title: `用户${generateForm.userId} - ${getReportTypeName(generateForm.reportType)}`,
          reportType: generateForm.reportType,
          userId: generateForm.userId,
          generateTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
          format: generateForm.format,
          fileSize: 0,
          status: 'generating'
        }

        reportList.value.unshift(newReport)
        generating.value = false
        showGenerateDialog.value = false
        
        ElMessage.success('报告已提交生成，请稍后查看')

        setTimeout(() => {
          newReport.status = 'completed'
          newReport.fileSize = Math.floor(Math.random() * 3000000) + 500000
        }, 3000)
      }, 2000)
    }
  })
}

function viewReport(row) {
  if (row.status !== 'completed') {
    ElMessage.warning('报告正在生成中，请稍后再试')
    return
  }
  
  currentReport.value = { ...row }
  showPreviewDialog.value = true
}

function downloadReport(row) {
  ElMessage.success(`正在下载：${row.title}`)
}

function deleteReport(row) {
  ElMessageBox.confirm('确定要删除该报告吗？删除后无法恢复！', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = reportList.value.findIndex(item => item.id === row.id)
    if (index > -1) {
      reportList.value.splice(index, 1)
      total.value--
      ElMessage.success('删除成功')
    }
  }).catch(() => {})
}
</script>

<style lang="scss" scoped>
.report-container {
  .page-card {
    margin-bottom: 20px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

  .report-preview {
    .preview-header {
      text-align: center;
      padding: 20px 0;
      border-bottom: 1px solid #eee;
      margin-bottom: 20px;

      h2 {
        font-size: 22px;
        color: #303133;
        margin-bottom: 10px;
      }

      .meta-info {
        color: #909399;
        font-size: 14px;

        span {
          margin: 0 15px;
        }
      }
    }

    .section {
      margin-bottom: 30px;

      h3 {
        font-size: 18px;
        color: #303133;
        margin-bottom: 20px;
        padding-left: 10px;
        border-left: 4px solid #409eff;
      }
    }

    .summary-cards {
      .summary-card {
        text-align: center;
        padding: 20px;

        h4 {
          font-size: 32px;
          color: #409eff;
          margin-bottom: 8px;
        }

        p {
          color: #606266;
          font-size: 14px;
          margin: 0;
        }
      }
    }
  }
}
</style>
