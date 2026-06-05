<template>
  <div class="archive-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>健康档案</h2>
      <el-button type="primary" @click="handleGenerateReport" :loading="generating">
        <el-icon><Document /></el-icon>
        生成AI分析报告
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :shortcuts="dateShortcuts"
          />
        </el-form-item>
        <el-form-item label="数据类型">
          <el-select v-model="queryParams.dataType" placeholder="全部类型" clearable style="width: 140px;">
            <el-option label="心率" value="heart_rate" />
            <el-option label="血压" value="blood_pressure" />
            <el-option label="体温" value="body_temp" />
            <el-option label="步数" value="steps" />
            <el-option label="睡眠" value="sleep" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchArchives"><el-icon><Search /></el-icon>查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 档案列表 -->
    <el-card shadow="never" class="archive-list-card">
      <template #header>
        <span>档案记录 (共 {{ total }} 条)</span>
      </template>

      <el-table :data="archives" v-loading="loading" stripe>
        <el-table-column prop="id" label="编号" width="70" />
        <el-table-column prop="reportDate" label="报告日期" width="120">
          <template #default="{ row }">{{ formatDate(row.reportDate) }}</template>
        </el-table-column>
        <el-table-column prop="reportType" label="报告类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getReportTypeTag(row.reportType)" size="small">{{ row.reportType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="200" show-overflow-tooltip />
        <el-table-column prop="riskLevel" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskTag(row.riskLevel)" size="small" effect="dark">
              {{ getRiskText(row.riskLevel) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '已确认' : '待查看' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
            <el-button link type="warning" size="small" @click="downloadReport(row)">下载</el-button>
            <el-popconfirm title="确定删除此档案？" @confirm="deleteArchive(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchArchives"
          @current-change="fetchArchives"
        />
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="'档案详情 - #' + currentArchive?.id"
      width="720px"
      destroy-on-close
    >
      <div v-if="currentArchive" class="archive-detail">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border class="detail-section">
          <el-descriptions-item label="报告编号">#{{ currentArchive.id }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ formatDate(currentArchive.createTime) }}</el-descriptions-item>
          <el-descriptions-item label="报告类型">
            <el-tag>{{ currentArchive.reportType }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="getRiskTag(currentArchive.riskLevel)" effect="dark">
              {{ getRiskText(currentArchive.riskLevel) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 健康指标雷达图 -->
        <div class="chart-section">
          <h4>健康指标概览</h4>
          <v-chart :option="radarOption" style="height: 280px;" autoresize />
        </div>

        <!-- 趋势图 -->
        <div class="chart-section">
          <h4>历史趋势</h4>
          <v-chart :option="trendOption" style="height: 260px;" autoresize />
        </div>

        <!-- AI分析报告 -->
        <div class="analysis-section">
          <h4>AI智能分析</h4>
          <div class="analysis-content" v-html="formattedAnalysis"></div>
        </div>

        <!-- 预警记录时间线 -->
        <div class="timeline-section">
          <h4>关联预警记录</h4>
          <el-timeline v-if="relatedAlerts.length">
            <el-timeline-item
              v-for="(alert, i) in relatedAlerts"
              :key="i"
              :timestamp="alert.alertTime"
              :type="getTimelineType(alert.level)"
              placement="top"
            >
              <el-card shadow="hover" size="small">
                <strong>{{ alert.ruleName }}</strong>
                <p>{{ alert.message }}</p>
                <el-tag size="small" :type="alert.status === 1 ? 'success' : 'danger'">
                  {{ alert.status === 1 ? '已处理' : '未处理' }}
                </el-tag>
              </el-card>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无关联预警记录" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart, LineChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import dayjs from 'dayjs'
import request from '@/utils/request'
import { reportApi } from '@/api/report'

use([CanvasRenderer, RadarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent])

// ============== 数据 ==============
const loading = ref(false)
const generating = ref(false)
const archives = ref([])
const total = ref(0)
const detailVisible = ref(false)
const currentArchive = ref(null)
const relatedAlerts = ref([])
const dateRange = ref(null)

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  dataType: '',
  startDate: '',
  endDate: ''
})

const dateShortcuts = [
  { text: '最近一周', value: () => [dayjs().subtract(7, 'd'), dayjs()] },
  { text: '最近一月', value: () => [dayjs().subtract(1, 'M'), dayjs()] },
  { text: '最近三月', value: () => [dayjs().subtract(3, 'M'), dayjs()] },
]

// ============== 图表选项 ==============
const radarOption = computed(() => ({
  radar: {
    indicator: [
      { name: '心血管', max: 100 },
      { name: '代谢', max: 100 },
      { name: '运动', max: 100 },
      { name: '睡眠', max: 100 },
      { name: '营养', max: 100 },
      { name: '心理', max: 100 },
    ],
    shape: 'polygon',
    splitNumber: 4,
    axisName: { color: '#666' }
  },
  series: [{
    type: 'radar',
    data: [{
      value: currentArchive.value?.metrics || [75, 68, 55, 72, 65, 78],
      name: '健康评分',
      areaStyle: { opacity: 0.25 },
      lineStyle: { width: 2 }
    }]
  }]
}))

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['心率', '血压', '步数'], bottom: 0 },
  xAxis: { type: 'category', data: currentArchive.value?.trendDates || [], axisLabel: { rotate: 30 } },
  yAxis: { type: 'value' },
  grid: { bottom: 60, left: 50, right: 20, top: 20 },
  series: [
    { name: '心率', type: 'line', data: currentArchive.value?.trendHr || [], smooth: true },
    { name: '血压', type: 'line', data: currentArchive.value?.trendBp || [], smooth: true },
    { name: '步数', type: 'bar', data: currentArchive.value?.trendSteps || [] }
  ]
}))

const formattedAnalysis = computed(() => {
  if (!currentArchive.value?.aiAnalysis) return '暂无AI分析内容'
  return currentArchive.value.aiAnalysis.replace(/\n/g, '<br/>').replace(/#{1,3}\s/g, (m) =>
    m.startsWith('# ') ? '<h3>' + m.slice(2) + '</h3>' :
    m.startsWith('## ') ? '<h4>' + m.slice(3) + '</h4>' :
    '<strong>' + m.slice(4) + '</strong>'
  )
})

// ============== 方法 ==============

async function fetchArchives() {
  loading.value = true
  try {
    if (dateRange.value && dateRange.value.length === 2) {
      queryParams.startDate = dateRange.value[0]
      queryParams.endDate = dateRange.value[1]
    }
    const res = await reportApi.getArchives(queryParams)
    archives.value = res.data.records || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('获取档案列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function viewDetail(row) {
  currentArchive.value = row
  detailVisible.value = true
  // 加载关联预警记录
  try {
    const res = await request.get('/api/alert/record/list', { params: { userId: row.userId, pageSize: 10 } })
    relatedAlerts.value = res.data?.records || []
  } catch (e) {
    relatedAlerts.value = []
  }
}

async function handleGenerateReport() {
  generating.value = true
  try {
    const res = await reportApi.generateAiReport({
      userId: 1,
      dateRange: dateRange.value || [dayjs().subtract(1, 'M').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')]
    })
    ElMessage.success('AI报告生成成功！')
    fetchArchives()
  } catch (e) {
    ElMessage.error('报告生成失败: ' + (e.msg || e.message))
  } finally {
    generating.value = false
  }
}

async function downloadReport(row) {
  try {
    const res = await request.post('/api/report/export', { id: row.id }, { responseType: 'blob' })
    const blob = new Blob([res], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `健康档案_${row.id}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

async function deleteArchive(row) {
  try {
    await request.delete(`/api/report/archive/${row.id}`)
    ElMessage.success('删除成功')
    fetchArchives()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

function resetQuery() {
  queryParams.pageNum = 1
  queryParams.dataType = ''
  queryParams.startDate = ''
  queryParams.endDate = ''
  dateRange.value = null
  fetchArchives()
}

// ============== 工具方法 ==============
function formatDate(val) { return val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-' }
function getReportTypeTag(type) {
  const map = { '周报': '', '月报': 'success', '综合': 'warning', '专项': 'info' }
  return map[type] || ''
}
function getRiskTag(level) {
  if (level >= 3) return 'danger'
  if (level === 2) return 'warning'
  return 'success'
}
function getRiskText(level) {
  if (level >= 3) return '高风险'
  if (level === 2) return '中风险'
  return '低风险'
}
function getTimelineType(level) {
  if (level >= 3) return 'danger'
  if (level === 2) return 'warning'
  return 'primary'
}

onMounted(() => {
  fetchArchives()
})
</script>

<style scoped lang="scss">
.archive-container {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h2 {
      margin: 0;
      font-size: 18px;
      color: #303133;
    }
  }

  .search-card {
    margin-bottom: 16px;
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }

  .archive-detail {
    .detail-section {
      margin-bottom: 20px;
    }

    .chart-section {
      background: #fafafa;
      padding: 12px;
      border-radius: 6px;
      margin-bottom: 20px;

      h4 {
        margin: 0 0 10px;
        font-size: 14px;
        color: #606266;
      }
    }

    .analysis-section {
      margin-bottom: 20px;

      h4 {
        margin: 0 0 10px;
        font-size: 14px;
      }

      .analysis-content {
        padding: 14px;
        background: #f5f7fa;
        border-radius: 6px;
        line-height: 1.8;
        font-size: 13px;
        color: #303133;

        :deep(h3) { font-size: 15px; color: #409EFF; margin: 12px 0 6px; }
        :deep(h4) { font-size: 14px; color: #606266; margin: 10px 0 4px; }
        :deep(strong) { color: #F56C6C; }
      }
    }

    .timeline-section {
      h4 {
        margin: 0 0 12px;
        font-size: 14px;
      }
    }
  }
}
</style>
