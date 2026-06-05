<template>
  <div class="visualization-container" v-fullscreen>
    <div class="viz-header">
      <div class="header-left">
        <h1>健康数据可视化大屏</h1>
        <div class="datetime">
          <span class="date">{{ currentDate }}</span>
          <span class="time">{{ currentTime }}</span>
        </div>
      </div>
      
      <div class="header-center">
        <div class="title-decoration"></div>
      </div>

      <div class="header-right">
        <el-select v-model="timeRange" size="small" style="width: 120px; margin-right: 12px;">
          <el-option label="今日" value="today" />
          <el-option label="本周" value="week" />
          <el-option label="本月" value="month" />
          <el-option label="本年" value="year" />
        </el-select>
        
        <el-button size="small" :icon="Refresh" circle @click="refreshData" />
        
        <el-button 
          size="small" 
          :icon="FullScreen" 
          circle 
          @click="toggleFullscreen"
        />
      </div>
    </div>

    <div class="viz-content">
      <div class="viz-left">
        <div class="panel panel-user-stats">
          <div class="panel-title">
            <span class="icon">👥</span>
            用户统计
          </div>
          <div class="panel-content">
            <div class="stat-grid">
              <div class="stat-item" v-for="(item, index) in userStats" :key="index">
                <div class="stat-value" :style="{ color: item.color }">
                  {{ animateNumber(item.value) }}
                </div>
                <div class="stat-label">{{ item.label }}</div>
                <div class="stat-trend" :class="item.trend > 0 ? 'up' : 'down'">
                  <span>{{ item.trend > 0 ? '+' : '' }}{{ item.trend }}%</span>
                  较上期
                </div>
              </div>
            </div>
            
            <v-chart :option="userTrendOption" style="height: 180px;" autoresize />
          </div>
        </div>

        <div class="panel panel-device-status">
          <div class="panel-title">
            <span class="icon">📱</span>
            设备在线状态
          </div>
          <div class="panel-content">
            <v-chart :option="deviceStatusOption" style="height: 240px;" autoresize />
          </div>
        </div>

        <div class="panel panel-data-source">
          <div class="panel-title">
            <span class="icon">📊</span>
            数据来源分布
          </div>
          <div class="panel-content">
            <v-chart :option="dataSourceOption" style="height: 220px;" autoresize />
          </div>
        </div>
      </div>

      <div class="viz-center">
        <div class="main-metrics">
          <div class="metric-card main-score">
            <div class="metric-label">综合健康指数</div>
            <div class="metric-value">
              <span class="number">{{ animatedHealthIndex }}</span>
              <span class="unit">分</span>
            </div>
            <div class="metric-level" :class="healthLevelClass">
              {{ healthLevelText }}
            </div>
          </div>

          <div class="sub-metrics">
            <div class="metric-card small" v-for="(metric, index) in subMetrics" :key="index">
              <div class="metric-label">{{ metric.label }}</div>
              <div class="metric-value">
                <span class="number">{{ metric.value }}</span>
                <span class="unit">{{ metric.unit }}</span>
              </div>
              <div class="metric-change" :class="metric.change >= 0 ? 'positive' : 'negative'">
                {{ metric.change >= 0 ? '↑' : '↓' }} {{ Math.abs(metric.change) }}
              </div>
            </div>
          </div>
        </div>

        <div class="panel panel-health-map">
          <div class="panel-title">
            <span class="icon">🗺️</span>
            区域健康热力图
          </div>
          <div class="panel-content">
            <v-chart :option="healthMapOption" style="height: 320px;" autoresize />
          </div>
        </div>

        <div class="panel panel-realtime-data">
          <div class="panel-title">
            <span class="icon">📡</span>
            实时数据流
            <span class="live-indicator">
              <span class="dot"></span>
              LIVE
            </span>
          </div>
          <div class="panel-content">
            <div class="realtime-list">
              <div 
                class="realtime-item" 
                v-for="(item, index) in realtimeDataList" 
                :key="index"
                :class="{ highlight: index === 0 }"
              >
                <span class="time">{{ item.time }}</span>
                <span class="type">{{ item.type }}</span>
                <span class="value" :class="item.level">{{ item.value }}</span>
                <span class="user">{{ item.user }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="viz-right">
        <div class="panel panel-health-trend">
          <div class="panel-title">
            <span class="icon">📈</span>
            健康趋势分析
          </div>
          <div class="panel-content">
            <v-chart :option="healthTrendOption" style="height: 260px;" autoresize />
          </div>
        </div>

        <div class="panel panel-risk-analysis">
          <div class="panel-title">
            <span class="icon">⚠️</span>
            风险预警统计
          </div>
          <div class="panel-content">
            <v-chart :option="riskAnalysisOption" style="height: 240px;" autoresize />
          </div>
        </div>

        <div class="panel panel-ai-insights">
          <div class="panel-title">
            <span class="icon">🤖</span>
            AI智能洞察
          </div>
          <div class="panel-content insights-list">
            <div 
              class="insight-item" 
              v-for="(insight, index) in aiInsights" 
              :key="index"
              :class="insight.level"
            >
              <div class="insight-icon">{{ insight.icon }}</div>
              <div class="insight-content">
                <h4>{{ insight.title }}</h4>
                <p>{{ insight.content }}</p>
              </div>
              <div class="insight-time">{{ insight.time }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { Refresh, FullScreen } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getDataStatistics } from '@/api/data'
import { getDeviceList } from '@/api/device'

const timeRange = ref('week')
const currentDate = ref('')
const currentTime = ref('')
let timeTimer = null

const animatedHealthIndex = ref(87)
const healthLevelClass = computed(() => {
  const score = animatedHealthIndex.value
  if (score >= 90) return 'excellent'
  if (score >= 80) return 'good'
  if (score >= 70) return 'normal'
  if (score >= 60) return 'warning'
  return 'danger'
})

const healthLevelText = computed(() => {
  const score = animatedHealthIndex.value
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 70) return '一般'
  if (score >= 60) return '需关注'
  return '高风险'
})

const userStats = ref([
  { label: '总用户数', value: 12856, trend: 12.5, color: '#409eff' },
  { label: '今日活跃', value: 3256, trend: 8.3, color: '#67c23a' },
  { label: '新增用户', value: 186, trend: -2.1, color: '#e6a23c' },
  { label: '在线设备', value: 8923, trend: 15.7, color: '#f56c6c' }
])

const subMetrics = ref([
  { label: '平均心率', value: 72, unit: 'bpm', change: -2 },
  { label: '平均血压', value: 120/80, unit: 'mmHg', change: 1 },
  { label: '平均血糖', value: 5.4, unit: 'mmol/L', change: 0 },
  { label: '睡眠质量', value: 85, unit: '%', change: 5 }
])

const realtimeDataList = ref([
  { time: '14:32:15', type: '心率', value: '78 bpm', level: 'normal', user: '张***' },
  { time: '14:32:12', type: '血压', value: '122/82', level: 'normal', user: '李***' },
  { time: '14:32:08', type: '血糖', value: '6.8 mmol/L', level: 'warning', user: '王***' },
  { time: '14:32:05', type: '体温', value: '36.5°C', level: 'normal', user: '赵***' },
  { time: '14:31:58', type: '血氧', value: '98%', level: 'normal', user: '钱***' },
  { time: '14:31:52', type: '心率', value: '95 bpm', level: 'warning', user: '孙***' },
  { time: '14:31:45', type: '步数', value: '8562 步', level: 'good', user: '周***' },
  { time: '14:31:38', type: '血压', value: '145/95', level: 'danger', user: '吴***' }
])

const aiInsights = ref([
  {
    icon: '💚',
    title: '心血管健康改善',
    content: '本周高血压患者血压控制率提升至89%，较上周提高5个百分点',
    time: '10分钟前',
    level: 'success'
  },
  {
    icon: '💛',
    title: '血糖异常预警',
    content: '检测到15名糖尿病患者空腹血糖持续偏高，建议加强随访',
    time: '25分钟前',
    level: 'warning'
  },
  {
    icon: '❤️',
    title: '睡眠质量分析',
    content: '老年人群体深睡比例下降12%，可能与季节变化有关',
    time: '1小时前',
    level: 'info'
  },
  {
    icon: '🔴',
    title: '紧急健康事件',
    content: '系统检测到3例心率异常（>120bpm），已自动触发告警通知',
    time: '2小时前',
    level: 'danger'
  }
])

const userTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { top: 20, right: 20, bottom: 30, left: 50 },
  xAxis: { 
    type: 'category', 
    data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    axisLine: { lineStyle: { color: '#4a5568' } },
    axisLabel: { color: '#a0aec0' }
  },
  yAxis: { 
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#2d3748' } },
    axisLabel: { color: '#a0aec0' }
  },
  series: [{
    data: [2800, 3200, 2900, 3500, 3100, 3800, 3256],
    type: 'line',
    smooth: true,
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
        ]
      }
    },
    lineStyle: { color: '#409eff', width: 2 },
    itemStyle: { color: '#409eff' }
  }]
}))

const deviceStatusOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '50%'],
    avoidLabelOverlap: true,
    itemStyle: { borderRadius: 6, borderColor: '#1a202c', borderWidth: 2 },
    label: { show: true, color: '#fff', fontSize: 11 },
    labelLine: { lineStyle: { color: '#4a5568' } },
    data: [
      { value: 6823, name: '智能手环', itemStyle: { color: '#409eff' } },
      { value: 1256, name: '智能血压计', itemStyle: { color: '#67c23a' } },
      { value: 892, name: '智能体重秤', itemStyle: { color: '#e6a23c' } },
      { value: 567, name: '智能血糖仪', itemStyle: { color: '#f56c6c' } },
      { value: 385, name: '其他设备', itemStyle: { color: '#909399' } }
    ]
  }]
}))

const dataSourceOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { top: 20, right: 20, bottom: 30, left: 100 },
  xAxis: { 
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#2d3748' } },
    axisLabel: { color: '#a0aec0' }
  },
  yAxis: { 
    type: 'category',
    data: ['IoT设备采集', '手动录入', 'HIS系统对接', '第三方平台', 'API接口'],
    axisLine: { lineStyle: { color: '#4a5568' } },
    axisLabel: { color: '#fff' }
  },
  series: [{
    type: 'bar',
    barWidth: 16,
    data: [
      { value: 45680, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#409eff' },
        { offset: 1, color: '#66b1ff' }
      ])}},
      { value: 12560, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#67c23a' },
        { offset: 1, color: '#85ce61' }
      ])}},
      { value: 8920, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#e6a23c' },
        { offset: 1, color: '#ebb563' }
      ])}},
      { value: 5670, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#f56c6c' },
        { offset: 1, color: '#f78989' }
      ])}},
      { value: 3420, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#909399' },
        { offset: 1, color: '#a6a9ad' }
      ])}}
    ],
    itemStyle: { borderRadius: [0, 4, 4, 0] }
  }]
}))

const healthMapOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: function(params) {
      return `${params.name}<br/>健康指数: ${params.value[2]}<br/>用户数: ${params.value[3]}人`
    }
  },
  visualMap: {
    min: 60,
    max: 100,
    left: 'left',
    top: 'bottom',
    text: ['高', '低'],
    calculable: true,
    inRange: {
      color: ['#f56c6c', '#e6a23c', '#67c23a', '#409eff']
    },
    textStyle: { color: '#a0aec0' }
  },
  geo: {
    map: 'china',
    roam: true,
    zoom: 1.2,
    label: { emphasis: { show: true, color: '#fff' } },
    itemStyle: {
      normal: { areaColor: '#1a365d', borderColor: '#2d3748' },
      emphasis: { areaColor: '#2d5a88' }
    }
  },
  series: [{
    name: '区域健康指数',
    type: 'effectScatter',
    coordinateSystem: 'geo',
    data: [
      { name: '北京', value: [116.46, 39.92, 88, 2560] },
      { name: '上海', value: [121.48, 31.22, 91, 3280] },
      { name: '广州', value: [113.23, 23.16, 85, 2150] },
      { name: '深圳', value: [114.07, 22.62, 89, 1890] },
      { name: '成都', value: [104.06, 30.67, 82, 1680] },
      { name: '杭州', value: [120.19, 30.26, 90, 1450] },
      { name: '武汉', value: [114.31, 30.52, 80, 1320] },
      { name: '西安', value: [108.95, 34.27, 78, 1100] }
    ],
    symbolSize: function(val) { return val[3] / 100 + 8 },
    showEffectOn: 'render',
    rippleEffect: { brushType: 'stroke', scale: 4 },
    itemStyle: { color: '#409eff' },
    zlevel: 1
  }]
}))

const healthTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: {
    data: ['心血管', '代谢指标', '运动健康', '睡眠质量'],
    textStyle: { color: '#a0aec0' },
    top: 0
  },
  grid: { top: 40, right: 20, bottom: 30, left: 50 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
    axisLine: { lineStyle: { color: '#4a5568' } },
    axisLabel: { color: '#a0aec0' }
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#2d3748' } },
    axisLabel: { color: '#a0aec0' }
  },
  series: [
    {
      name: '心血管',
      type: 'line',
      smooth: true,
      data: [75, 72, 78, 82, 79, 76, 74],
      lineStyle: { color: '#f56c6c', width: 2 },
      itemStyle: { color: '#f56c6c' },
      areaStyle: { opacity: 0.1 }
    },
    {
      name: '代谢指标',
      type: 'line',
      smooth: true,
      data: [80, 78, 82, 85, 83, 81, 79],
      lineStyle: { color: '#e6a23c', width: 2 },
      itemStyle: { color: '#e6a23c' },
      areaStyle: { opacity: 0.1 }
    },
    {
      name: '运动健康',
      type: 'line',
      smooth: true,
      data: [65, 62, 75, 88, 82, 70, 60],
      lineStyle: { color: '#67c23a', width: 2 },
      itemStyle: { color: '#67c23a' },
      areaStyle: { opacity: 0.1 }
    },
    {
      name: '睡眠质量',
      type: 'line',
      smooth: true,
      data: [90, 95, 70, 60, 65, 85, 92],
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' },
      areaStyle: { opacity: 0.1 }
    }
  ]
}))

const riskAnalysisOption = computed(() =>({
  tooltip: { trigger: 'axis' },
  grid: { top: 20, right: 20, bottom: 30, left: 60 },
  xAxis: {
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#2d3748' } },
    axisLabel: { color: '#a0aec0' }
  },
  yAxis: {
    type: 'category',
    data: ['高血压风险', '糖尿病风险', '心脏病风险', '中风风险', '肥胖风险'],
    axisLine: { lineStyle: { color: '#4a5568' } },
    axisLabel: { color: '#fff' }
  },
  series: [{
    type: 'bar',
    barWidth: 18,
    data: [
      { value: 156, itemStyle: { color: '#f56c6c' }, label: { show: true, position: 'right', color: '#f56c6c' } },
      { value: 98, itemStyle: { color: '#e6a23c' }, label: { show: true, position: 'right', color: '#e6a23c' } },
      { value: 67, itemStyle: { color: '#409eff' }, label: { show: true, position: 'right', color: '#409eff' } },
      { value: 45, itemStyle: { color: '#67c23a' }, label: { show: true, position: 'right', color: '#67c23a' } },
      { value: 123, itemStyle: { color: '#909399' }, label: { show: true, position: 'right', color: '#909399' } }
    ],
    itemStyle: { borderRadius: [0, 4, 4, 0] }
  }]
}))

function updateDateTime() {
  currentDate.value = dayjs().format('YYYY年MM月DD日 dddd')
  currentTime.value = dayjs().format('HH:mm:ss')
}

function animateNumber(value) {
  return value.toLocaleString()
}

function refreshData() {
  loadDashboardData()
  ElMessage.success('数据已刷新')
}

async function loadDashboardData() {
  try {
    // Load health statistics
    const statsRes = await getDataStatistics({ timeRange: timeRange.value })
    if (statsRes.code === 200 && statsRes.data) {
      const d = statsRes.data
      if (d.totalUsers) userStats.value[0].value = d.totalUsers
      if (d.activeUsers) userStats.value[1].value = d.activeUsers
      if (d.healthIndex !== undefined) animatedHealthIndex.value = d.healthIndex
      if (d.avgHeartRate) subMetrics.value[0].value = d.avgHeartRate
    }

    // Load device statistics
    const deviceRes = await getDeviceList({ pageSize: 100 })
    if (deviceRes.code === 200 && deviceRes.data?.records) {
      const devices = deviceRes.data.records
      const onlineCount = devices.filter(d => d.status === 'online').length
      userStats.value[3].value = onlineCount
    }
  } catch (error) {
    console.warn('Dashboard API unavailable, using fallback data:', error)
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

onMounted(() => {
  updateDateTime()
  timeTimer = setInterval(updateDateTime, 1000)
  loadDashboardData()
  
  setInterval(() => {
    const newItem = {
      time: dayjs().format('HH:mm:ss'),
      type: ['心率', '血压', '血糖', '体温', '血氧', '步数'][Math.floor(Math.random() * 6)],
      value: [`${Math.floor(Math.random() * 40 + 60)} bpm`, 
              `${Math.floor(Math.random() * 40 + 100)}/${Math.floor(Math.random() * 20 + 70)}`,
              `${(Math.random() * 4 + 4).toFixed(1)} mmol/L`,
              `${(36 + Math.random()).toFixed(1)}°C`,
              `${Math.floor(Math.random() * 5 + 95)}%`,
              `${Math.floor(Math.random() * 10000)} 步`][Math.floor(Math.random() * 6)],
      level: ['normal', 'normal', 'warning', 'normal', 'normal', 'good'][Math.floor(Math.random() * 6)],
      user: ['张***', '李***', '王***', '赵***', '钱***', '孙***'][Math.floor(Math.random() * 6)]
    }
    
    realtimeDataList.value.unshift(newItem)
    if (realtimeDataList.value.length > 10) {
      realtimeDataList.value.pop()
    }
  }, 3000)
})

onUnmounted(() => {
  if (timeTimer) {
    clearInterval(timeTimer)
  }
})
</script>

<style lang="scss" scoped>
.visualization-container {
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #0c1426 0%, #1a2942 50%, #0d1b2a 100%);
  color: #fff;
  overflow: hidden;

  .viz-header {
    height: 70px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    background: linear-gradient(180deg, rgba(26, 41, 66, 0.95), rgba(26, 41, 66, 0.7));
    border-bottom: 1px solid rgba(64, 158, 255, 0.3);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);

    .header-left {
      h1 {
        font-size: 24px;
        font-weight: bold;
        margin: 0;
        background: linear-gradient(90deg, #409eff, #67c23a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px;
      }

      .datetime {
        margin-top: 4px;
        font-size: 13px;
        color: #a0aec0;

        .date {
          margin-right: 16px;
        }

        .time {
          color: #409eff;
          font-weight: bold;
          font-size: 16px;
          font-family: 'Courier New', monospace;
        }
      }
    }

    .header-center {
      flex: 1;
      padding: 0 40px;

      .title-decoration {
        height: 2px;
        background: linear-gradient(90deg, transparent, #409eff, transparent);
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 8px;

      :deep(.el-select .el-input__wrapper),
      :deep(.el-button) {
        background: rgba(64, 158, 255, 0.1);
        border-color: rgba(64, 158, 255, 0.3);
        color: #fff;

        &:hover {
          border-color: #409eff;
        }
      }
    }
  }

  .viz-content {
    display: flex;
    gap: 16px;
    padding: 16px;
    height: calc(100vh - 86px);

    .viz-left,
    .viz-right {
      width: 28%;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .viz-center {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .panel {
      background: linear-gradient(145deg, rgba(26, 41, 66, 0.9), rgba(13, 27, 42, 0.9));
      border: 1px solid rgba(64, 158, 255, 0.2);
      border-radius: 8px;
      backdrop-filter: blur(10px);

      .panel-title {
        padding: 12px 16px;
        font-size: 14px;
        font-weight: bold;
        color: #e2e8f0;
        border-bottom: 1px solid rgba(64, 158, 255, 0.15);
        display: flex;
        align-items: center;
        gap: 8px;

        .icon {
          font-size: 18px;
        }

        .live-indicator {
          margin-left: auto;
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          color: #f56c6c;
          animation: pulse 2s infinite;

          .dot {
            width: 6px;
            height: 6px;
            background: #f56c6c;
            border-radius: 50%;
          }
        }
      }

      .panel-content {
        padding: 16px;
      }
    }

    .main-metrics {
      display: flex;
      gap: 16px;

      .metric-card {
        background: linear-gradient(145deg, rgba(26, 41, 66, 0.95), rgba(13, 27, 42, 0.95));
        border: 1px solid rgba(64, 158, 255, 0.3);
        border-radius: 12px;
        padding: 24px;
        text-align: center;

        &.main-score {
          flex: 1;
          max-width: 300px;

          .metric-value {
            .number {
              font-size: 72px;
              font-weight: bold;
              background: linear-gradient(135deg, #409eff, #67c23a);
              -webkit-background-clip: text;
              -webkit-text-fill-color: transparent;
            }

            .unit {
              font-size: 24px;
              color: #a0aec0;
              margin-left: 4px;
            }
          }

          .metric-level {
            margin-top: 12px;
            font-size: 18px;
            font-weight: bold;
            padding: 6px 20px;
            border-radius: 20px;
            display: inline-block;

            &.excellent { background: rgba(103, 194, 58, 0.2); color: #67c23a; }
            &.good { background: rgba(64, 158, 255, 0.2); color: #409eff; }
            &.normal { background: rgba(230, 162, 60, 0.2); color: #e6a23c; }
            &.warning { background: rgba(245, 108, 108, 0.2); color: #f56c6c; }
            &.danger { background: rgba(245, 108, 108, 0.3); color: #f56c6c; animation: blink 1s infinite; }
          }
        }

        &.small {
          flex: 1;
          padding: 16px 12px;

          .metric-label {
            font-size: 12px;
            color: #a0aec0;
            margin-bottom: 8px;
          }

          .metric-value {
            .number {
              font-size: 28px;
              font-weight: bold;
              color: #e2e8f0;
            }

            .unit {
              font-size: 12px;
              color: #718096;
              margin-left: 4px;
            }
          }

          .metric-change {
            margin-top: 8px;
            font-size: 13px;
            font-weight: bold;

            &.positive { color: #67c23a; }
            &.negative { color: #f56c6c; }
          }
        }
      }

      .sub-metrics {
        flex: 1;
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
      }
    }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 16px;

      .stat-item {
        text-align: center;
        padding: 12px 8px;
        background: rgba(64, 158, 255, 0.05);
        border-radius: 8px;

        .stat-value {
          font-size: 24px;
          font-weight: bold;
        }

        .stat-label {
          font-size: 12px;
          color: #a0aec0;
          margin-top: 4px;
        }

        .stat-trend {
          font-size: 11px;
          margin-top: 4px;

          &.up { color: #67c23a; }
          &.down { color: #f56c6c; }
        }
      }
    }

    .realtime-list {
      .realtime-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid rgba(64, 158, 255, 0.08);
        font-size: 13px;

        &:last-child {
          border-bottom: none;
        }

        &.highlight {
          background: rgba(64, 158, 255, 0.08);
          margin: 0 -16px;
          padding: 8px 16px;
          border-radius: 4px;
        }

        .time {
          width: 80px;
          color: #718096;
          font-family: 'Courier New', monospace;
        }

        .type {
          width: 60px;
          color: #a0aec0;
        }

        .value {
          flex: 1;
          font-weight: bold;

          &.normal { color: #67c23a; }
          &.warning { color: #e6a23c; }
          &.danger { color: #f56c6c; }
          &.good { color: #409eff; }
        }

        .user {
          width: 60px;
          text-align: right;
          color: #718096;
        }
      }
    }

    .insights-list {
      .insight-item {
        display: flex;
        align-items: flex-start;
        padding: 12px;
        margin-bottom: 10px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        border-left: 3px solid;

        &:last-child {
          margin-bottom: 0;
        }

        &.success { border-left-color: #67c23a; }
        &.warning { border-left-color: #e6a23c; }
        &.info { border-left-color: #409eff; }
        &.danger { border-left-color: #f56c6c; }

        .insight-icon {
          font-size: 24px;
          margin-right: 12px;
        }

        .insight-content {
          flex: 1;

          h4 {
            font-size: 13px;
            color: #e2e8f0;
            margin: 0 0 4px 0;
          }

          p {
            font-size: 12px;
            color: #a0aec0;
            margin: 0;
            line-height: 1.4;
          }
        }

        .insight-time {
          font-size: 11px;
          color: #718096;
          white-space: nowrap;
        }
      }
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
