<template>
  <div class="dashboard-container">
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6" v-for="(stat, index) in statCards" :key="index">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <h3>{{ stat.value }}</h3>
              <p>{{ stat.label }}</p>
            </div>
            <el-icon class="stat-icon" :style="{ color: stat.color, background: stat.bgColor }">
              <component :is="stat.icon" />
            </el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>健康数据趋势</span>
          </template>
          <v-chart :option="trendChartOption" style="height: 400px;" autoresize />
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>数据类型分布</span>
          </template>
          <v-chart :option="pieChartOption" style="height: 400px;" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>设备在线状态</span>
          </template>
          <v-chart :option="deviceChartOption" style="height: 300px;" autoresize />
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>近期预警统计</span>
          </template>
          <v-chart :option="alertChartOption" style="height: 300px;" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" class="recent-data-card">
      <template #header>
        <span>最新健康数据</span>
      </template>
      <el-table :data="recentData" stripe style="width: 100%">
        <el-table-column prop="userId" label="用户ID" width="100" />
        <el-table-column prop="dataType" label="数据类型" width="120" />
        <el-table-column prop="metric" label="指标" width="120" />
        <el-table-column prop="value" label="数值" width="100" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="timestamp" label="时间" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import { getDataStatistics } from '@/api/data'
import request from '@/utils/request'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

const statCards = ref([
  { label: '总用户数', value: '-', icon: 'User', color: '#409eff', bgColor: '#ecf5ff' },
  { label: '在线设备', value: '-', icon: 'Monitor', color: '#67c23a', bgColor: '#f0f9eb' },
  { label: '今日数据量', value: '-', icon: 'DataLine', color: '#e6a23c', bgColor: '#fdf6ec' },
  { label: '活跃预警', value: '-', icon: 'Warning', color: '#f56c6c', bgcolor: '#fef0f0' }
])

const recentData = ref([])

const trendChartOption = ref({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' }
  },
  legend: {
    data: ['心率', '体温', '收缩压']
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'],
    axisLabel: { rotate: 30 }
  },
  yAxis: [
    { type: 'value', name: '心率/血压', position: 'left' },
    { type: 'value', name: '体温', position: 'right', min: 36, max: 38 }
  ],
  series: [
    {
      name: '心率',
      type: 'line',
      data: [],
      smooth: true,
      itemStyle: { color: '#409eff' }
    },
    {
      name: '体温',
      type: 'line',
      yAxisIndex: 1,
      data: [],
      smooth: true,
      itemStyle: { color: '#f56c6c' }
    },
    {
      name: '收缩压',
      type: 'line',
      data: [],
      smooth: true,
      itemStyle: { color: '#67c23a' }
    }
  ]
})

const pieChartOption = ref({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { orient: 'vertical', left: 'left' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
    label: { show: false, position: 'center' },
    emphasis: {
      label: { show: true, fontSize: 16, fontWeight: 'bold' }
    },
    data: []
  }]
})

const deviceChartOption = ref({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [{
    type: 'bar',
    barWidth: '60%',
    data: []
  }]
})

const alertChartOption = ref({
  tooltip: { trigger: 'axis' },
  legend: { data: ['严重', '警告', '提醒'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
  yAxis: { type: 'value' },
  series: [
    { name: '严重', type: 'bar', stack: 'total', data: [], itemStyle: { color: '#f56c6c' } },
    { name: '警告', type: 'bar', stack: 'total', data: [], itemStyle: { color: '#e6a23c' } },
    { name: '提醒', type: 'bar', stack: 'total', data: [], itemStyle: { color: '#409eff' } }
  ]
})

onMounted(() => {
  loadDashboardData()
})

async function loadDashboardData() {
  try {
    const [statsRes, recentRes] = await Promise.allSettled([
      getDataStatistics({ days: 7 }),
      request.get('/storage/list', { params: { pageSize: 5, pageNum: 1 } })
    ])

    if (statsRes.status === 'fulfilled' && statsRes.value?.code === 200) {
      const data = statsRes.value.data || {}
      statCards.value[0].value = data.totalUsers ?? '-'
      statCards.value[1].value = data.onlineDevices ?? '-'
      statCards.value[2].value = data.todayRecords ? String(data.todayRecords) : '-'
      statCards.value[3].value = data.activeAlerts ?? '-'

      if (data.typeDistribution) {
        pieChartOption.value.series[0].data = Object.entries(data.typeDistribution).map(([name, val]) => ({
          value: val, name
        }))
      }

      if (data.trendData) {
        trendChartOption.value.xAxis.data = data.trendData.times || trendChartOption.value.xAxis.data
        trendChartOption.value.series[0].data = data.trendData.heartRate || []
        trendChartOption.value.series[1].data = data.trendData.bodyTemp || []
        trendChartOption.value.series[2].data = data.trendData.bloodPressure || []
      }

      if (data.deviceStatus) {
        deviceChartOption.value.xAxis.data = data.deviceStatus.map(d => d.name)
        deviceChartOption.value.series[0].data = data.deviceStatus.map(d => ({
          value: d.count,
          itemStyle: { color: d.online ? '#67c23a' : '#f56c6c' }
        }))
      }

      if (data.alertStats) {
        alertChartOption.value.series[0].data = data.alertStats.critical || []
        alertChartOption.value.series[1].data = data.alertStats.warning || []
        alertChartOption.value.series[2].data = data.alertStats.info || []
      }
    }

    if (recentRes.status === 'fulfilled' && recentRes.value?.code === 200) {
      const records = recentRes.value.data?.records || recentRes.value.data || []
      recentData.value = records.slice(0, 5).map(r => ({
        userId: r.userId || '-',
        dataType: r.dataType || r.metric || '-',
        metric: r.metric || '-',
        value: r.value ?? '-',
        unit: r.unit || '',
        timestamp: r.timestamp || r.createdAt || '-'
      }))
    }
  } catch (error) {
    console.error('加载仪表板数据失败:', error)
  }
}
</script>

<style lang="scss" scoped>
.dashboard-container {
  .stat-cards {
    margin-bottom: 20px;

    .stat-card {
      .stat-content {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .stat-info {
          h3 {
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
          }

          p {
            font-size: 14px;
            color: #999;
          }
        }

        .stat-icon {
          width: 60px;
          height: 60px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 28px;
        }
      }
    }
  }

  .chart-row {
    margin-bottom: 20px;

    .chart-card {
      height: 480px;
    }
  }

  .recent-data-card {
    margin-top: 20px;
  }
}
</style>
