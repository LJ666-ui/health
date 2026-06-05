/**
 * ZhiHealth 智慧健康大数据平台 - 实时监控大屏
 * ECharts 图表配置与数据可视化逻辑
 */

// 全局变量
let charts = {};
let updateInterval = null;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initDateTime();
    initAllCharts();
    startRealtimeUpdate();
    
    window.addEventListener('resize', handleResize);
});

// 时间显示更新
function initDateTime() {
    function updateDateTime() {
        const now = new Date();
        const dateStr = now.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        document.getElementById('datetime').textContent = dateStr;
        
        document.getElementById('lastUpdate').textContent = 
            now.toLocaleString('zh-CN').replace(/\//g, '-');
    }
    
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

// 初始化所有图表
function initAllCharts() {
    initHeartRateChart();
    initBloodPressureChart();
    initHealthDistributionChart();
    initDeviceStatusChart();
    initActivityRankingChart();
    initSleepQualityChart();
    initRegionMapChart();
    initPipelineStatusChart();
}

// 1. 实时心率监测图表
function initHeartRateChart() {
    const chartDom = document.getElementById('heartRateChart');
    charts.heartRate = echarts.init(chartDom);
    
    // 生成初始数据（最近60个数据点，每分钟一个）
    const data = generateTimeSeriesData(60, 70, 10);
    const timeData = generateTimeLabels(60);
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(10, 25, 50, 0.9)',
            borderColor: '#0096ff',
            textStyle: { color: '#fff' },
            formatter: function(params) {
                return `<div style="font-weight:bold;margin-bottom:5px;">心率监测</div>
                        时间: ${params[0].axisValue}<br/>
                        心率: <span style="color:#00d4ff;font-size:16px;font-weight:bold;">${params[0].value}</span> bpm`;
            }
        },
        grid: {
            left: '3%', right: '4%', bottom: '3%', top: '8%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: timeData,
            axisLine: { lineStyle: { color: '#1a3a5c' } },
            axisLabel: { 
                color: '#6b8299',
                fontSize: 11,
                interval: 9
            }
        },
        yAxis: {
            type: 'value',
            name: 'BPM',
            nameTextStyle: { color: '#6b8299' },
            min: 40,
            max: 160,
            splitLine: { 
                lineStyle: { 
                    color: 'rgba(0, 150, 255, 0.1)',
                    type: 'dashed'
                } 
            },
            axisLine: { show: false },
            axisLabel: { color: '#6b8299' }
        },
        series: [{
            name: '平均心率',
            type: 'line',
            smooth: true,
            symbol: 'none',
            sampling: 'lttb',
            lineStyle: {
                width: 3,
                color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                    { offset: 0, color: '#00d4ff' },
                    { offset: 1, color: '#00ff88' }
                ])
            },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
                    { offset: 1, color: 'rgba(0, 212, 255, 0)' }
                ])
            },
            data: data,
            markLine: {
                silent: true,
                symbol: 'none',
                data: [
                    { yAxis: 120, lineStyle: { color: '#ff4757', type: 'dashed' }, label: { formatter: '异常上限' }},
                    { yAxis: 50, lineStyle: { color: '#ffa502', type: 'dashed' }, label: { formatter: '异常下限' }}
                ]
            },
            markArea: {
                silent: true,
                data: [[{yAxis: 120}, {yAxis: 200}]]
            }
        }],
        animationDuration: 1000,
        animationEasing: 'cubicOut'
    };
    
    charts.heartRate.setOption(option);
}

// 2. 血压趋势分析图表
function initBloodPressureChart() {
    const chartDom = document.getElementById('bloodPressureChart');
    charts.bloodPressure = echarts.init(chartDom);
    
    const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const systolicData = [125, 128, 122, 130, 126, 119, 124];
    const diastolicData = [82, 85, 80, 87, 83, 78, 81];
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(10, 25, 50, 0.9)',
            borderColor: '#0096ff',
            textStyle: { color: '#fff' }
        },
        legend: {
            data: ['收缩压', '舒张压'],
            top: 5,
            textStyle: { color: '#8ba3c7', fontSize: 12 }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
        xAxis: {
            type: 'category',
            data: days,
            axisLine: { lineStyle: { color: '#1a3a5c' } },
            axisLabel: { color: '#6b8299' }
        },
        yAxis: {
            type: 'value',
            name: 'mmHg',
            nameTextStyle: { color: '#6b8299' },
            min: 50,
            max: 180,
            splitLine: { lineStyle: { color: 'rgba(0, 150, 255, 0.1)', type: 'dashed' }},
            axisLabel: { color: '#6b8299' }
        },
        series: [
            {
                name: '收缩压',
                type: 'bar',
                barWidth: '35%',
                itemStyle: {
                    borderRadius: [4, 4, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#00d4ff' },
                        { offset: 1, color: '#0066cc' }
                    ])
                },
                data: systolicData
            },
            {
                name: '舒张压',
                type: 'bar',
                barWidth: '35%',
                itemStyle: {
                    borderRadius: [4, 4, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#00ff88' },
                        { offset: 1, color: '#00aa55' }
                    ])
                },
                data: diastolicData
            }
        ],
        animationDelay: function(idx) { return idx * 100; }
    };
    
    charts.bloodPressure.setOption(option);
}

// 3. 用户健康等级分布 (饼图)
function initHealthDistributionChart() {
    const chartDom = document.getElementById('healthDistributionChart');
    charts.healthDist = echarts.init(chartDom);
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)',
            backgroundColor: 'rgba(10, 25, 50, 0.9)',
            borderColor: '#0096ff'
        },
        legend: {
            orient: 'vertical',
            right: '5%',
            top: 'center',
            textStyle: { color: '#8ba3c7', fontSize: 12 }
        },
        series: [{
            name: '健康等级',
            type: 'pie',
            radius: ['45%', '70%'],
            center: ['40%', '50%'],
            avoidLabelOverlap: false,
            padAngle: 3,
            itemStyle: {
                borderRadius: 8,
                borderColor: '#0c1426',
                borderWidth: 3
            },
            label: { show: false },
            emphasis: {
                label: { show: true, fontSize: 16, fontWeight: bold, color: '#fff' }
            },
            labelLine: { show: false },
            data: [
                { value: 4820, name: 'A级-优秀', itemStyle: { color: '#00ff88' }},
                { value: 3850, name: 'B级-良好', itemStyle: { color: '#00d4ff' }},
                { value: 2680, name: 'C级-一般', itemStyle: { color: '#ffa502' }},
                { value: 1120, name: 'D级-较差', itemStyle: { color: '#ff6348' }},
                { value: 377, name: 'E级-危险', itemStyle: { color: '#ff4757' }}
            ],
            animationType: 'scale',
            animationEasing: 'elasticOut'
        }]
    };
    
    charts.healthDist.setOption(option);
}

// 4. 设备状态仪表盘
function initDeviceStatusChart() {
    const chartDom = document.getElementById('deviceStatusChart');
    charts.deviceStatus = echarts.init(chartDom);
    
    const option = {
        backgroundColor: 'transparent',
        series: [{
            type: 'gauge',
            startAngle: 200,
            endAngle: -20,
            min: 0,
            max: 100,
            radius: '90%',
            splitNumber: 10,
            axisLine: {
                lineStyle: {
                    width: 15,
                    color: [
                        [0.85, '#00ff88'],
                        [0.95, '#ffa502'],
                        [1, '#ff4757']
                    ]
                }
            },
            pointer: {
                icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                length: '65%',
                width: 8,
                offsetCenter: [0, '-10%'],
                itemStyle: { color: 'auto' }
            },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            title: {
                offsetCenter: [0, '20%'],
                fontSize: 14,
                color: '#8ba3c7'
            },
            detail: {
                valueAnimation: true,
                offsetCenter: [0, '0%'],
                fontSize: 28,
                fontWeight: 'bold',
                formatter: '{value}%',
                color: '#00d4ff'
            },
            data: [{ value: 94.2, name: '设备在线率' }]
        }]
    };
    
    charts.deviceStatus.setOption(option);
}

// 5. 活动量排行 TOP10 (横向柱状图)
function initActivityRankingChart() {
    const chartDom = document.getElementById('activityRankingChart');
    charts.activityRank = echarts.init(chartDom);
    
    const users = ['用户#1089', '用户#1056', '用户#1102', '用户#1024', '用户#1098',
                   '用户#1076', '用户#1034', '用户#1115', '用户#1067', '用户#1045'];
    const steps = [23456, 19876, 18234, 16543, 15234, 14123, 13245, 12345, 11567, 10890];
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(10, 25, 50, 0.9)',
            borderColor: '#0096ff',
            formatter: '{b}<br/>步数: <strong>{c}</strong>'
        },
        grid: { left: '3%', right: '15%', bottom: '3%', top: '3%', containLabel: true },
        xAxis: {
            type: 'value',
            splitLine: { lineStyle: { color: 'rgba(0, 150, 255, 0.1)' }},
            axisLabel: { color: '#6b8299', formatter: '{value}' }
        },
        yAxis: {
            type: 'category',
            data: users.reverse(),
            axisLine: { lineStyle: { color: '#1a3a5c' } },
            axisLabel: { color: '#8ba3c7', fontSize: 11 }
        },
        series: [{
            type: 'bar',
            barWidth: '60%',
            data: steps.reverse(),
            itemStyle: {
                borderRadius: [0, 4, 4, 0],
                color: function(params) {
                    const colors = ['#00ff88', '#00e673', '#00cc5c', '#00b347', '#009933',
                                   '#008026', '#00661f', '#004d17', '#00330f', '#001a07'];
                    return new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: colors[params.dataIndex] },
                        { offset: 1, color: '#0066cc' }
                    ]);
                }
            },
            label: {
                show: true,
                position: 'right',
                color: '#00d4ff',
                fontSize: 11,
                formatter: '{c}'
            }
        }],
        animationDelay: function(idx) { return idx * 80; }
    };
    
    charts.activityRank.setOption(option);
}

// 6. 睡眠质量分布 (雷达图)
function initSleepQualityChart() {
    const chartDom = document.getElementById('sleepQualityChart');
    charts.sleepQuality = echarts.init(chartDom);
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {},
        radar: {
            indicator: [
                { name: '深睡时长', max: 3 },
                { name: '浅睡时长', max: 5 },
                { name: 'REM睡眠', max: 2 },
                { name: '入睡速度', max: 5 },
                { name: '睡眠连续性', max: 5 },
                { name: '睡眠效率', max: 100 }
            ],
            shape: 'circle',
            splitNumber: 4,
            axisName: { color: '#8ba3c7', fontSize: 11 },
            splitLine: { lineStyle: { color: 'rgba(0, 150, 255, 0.15)' }},
            splitArea: { 
                areaStyle: { 
                    color: ['rgba(0, 212, 255, 0.02)', 'rgba(0, 212, 255, 0.05)']
                }}
        },
        series: [{
            type: 'radar',
            data: [
                {
                    value: [2.1, 4.2, 1.5, 3.8, 4.2, 89],
                    name: '当前睡眠质量',
                    areaStyle: {
                        color: 'rgba(0, 212, 255, 0.3)'
                    },
                    lineStyle: { color: '#00d4ff', width: 2 },
                    itemStyle: { color: '#00d4ff' }
                },
                {
                    value: [2.5, 4.5, 1.8, 4.5, 4.5, 95],
                    name: '理想标准',
                    areaStyle: {
                        color: 'rgba(0, 255, 136, 0.1)'
                    },
                    lineStyle: { color: '#00ff88', width: 2, type: 'dashed' },
                    itemStyle: { color: '#00ff88' }
                }
            ]
        }]
    };
    
    charts.sleepQuality.setOption(option);
}

// 7. 区域地图 (简化版散点图模拟)
function initRegionMapChart() {
    const chartDom = document.getElementById('regionMapChart');
    charts.regionMap = echarts.init(chartDom);
    
    // 模拟区域数据
    const regions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆'];
    const data = regions.map((name, i) => ({
        name: name,
        value: [
            116 + Math.random() * 30,
            30 + Math.random() * 20,
            Math.floor(Math.random() * 3000 + 500),
            Math.random() > 0.7 ? 'high_risk' : (Math.random() > 0.4 ? 'normal' : 'warning')
        ]
    }));
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(10, 25, 50, 0.9)',
            borderColor: '#0096ff',
            formatter: function(params) {
                return `<strong>${params.data.name}</strong><br/>
                        用户数: ${params.data.value[2]}<br/>
                        状态: ${params.data.value[3] === 'high_risk' ? '<span style="color:#ff4757">高风险</span>' : 
                              params.data.value[3] === 'warning' ? '<span style="color:#ffa502">需关注</span>' : 
                              '<span style="color:#00ff88">正常</span>'}`;
            }
        },
        geo: {
            map: 'china',
            roam: true,
            zoom: 1.2,
            center: [104, 36],
            label: { emphasis: { show: true, color: '#fff' }},
            itemStyle: {
                normal: {
                    areaColor: 'rgba(20, 40, 80, 0.6)',
                    borderColor: '#0096ff',
                    borderWidth: 0.5
                },
                emphasis: {
                    areaColor: 'rgba(0, 150, 255, 0.4)'
                }
            }
        },
        series: [{
            name: '用户分布',
            type: 'effectScatter',
            coordinateSystem: 'geo',
            data: data.map(item => ({
                name: item.name,
                value: item.value.slice(0, 3)
            })),
            symbolSize: function(val) { return Math.max(val[2] / 100, 8); },
            showEffectOn: 'render',
            rippleEffect: {
                brushType: 'stroke',
                scale: 3,
                period: 4
            },
            itemStyle: {
                color: function(params) {
                    return params.data.value[2] > 2000 ? '#ff4757' :
                           params.data.value[2] > 1200 ? '#ffa502' : '#00d4ff';
                }
            },
            zlevel: 1
        }, {
            name: '风险标记',
            type: 'scatter',
            coordinateSystem: 'geo',
            data: data.filter(d => d.value[3] === 'high_risk').map(d => ({
                name: d.name,
                value: d.value.slice(0, 2)
            })),
            symbolSize: 20,
            symbol: 'pin',
            itemStyle: { color: '#ff4757' },
            zlevel: 2
        }]
    };
    
    // 如果没有中国地图，使用简化的散点图
    try {
        charts.regionMap.setOption(option);
    } catch(e) {
        console.log('地图加载失败，使用备选方案');
        initFallbackMap(data);
    }
}

// 备用地图方案（纯散点）
function initFallbackMap(data) {
    const option = {
        backgroundColor: 'transparent',
        xAxis: { 
            type: 'value', 
            show: false,
            min: 80, max: 150 
        },
        yAxis: { 
            type: 'value', 
            show: false,
            min: 15, max: 55 
        },
        series: [{
            type: 'scatter',
            symbolSize: function(val) { return val[2] / 50; },
            data: data.map(d => ({
                name: d.name,
                value: d.value.slice(0, 3)
            })),
            itemStyle: {
                color: function(params) {
                    return params.data.value[2] > 2000 ? '#ff4757' :
                           params.data.value[2] > 1200 ? '#ffa502' : '#00d4ff';
                },
                opacity: 0.8
            },
            label: {
                show: true,
                position: 'top',
                formatter: '{b}',
                color: '#8ba3c7',
                fontSize: 11
            }
        }]
    };
    
    charts.regionMap.setOption(option);
}

// 8. 数据管道状态 (仪表盘组)
function initPipelineStatusChart() {
    const chartDom = document.getElementById('pipelineStatusChart');
    charts.pipelineStatus = echarts.init(chartDom);
    
    const option = {
        backgroundColor: 'transparent',
        series: [
            {
                type: 'gauge',
                center: ['25%', '55%'],
                radius: '70%',
                startAngle: 200,
                endAngle: -20,
                min: 0,
                max: 100,
                splitNumber: 5,
                axisLine: {
                    lineStyle: {
                        width: 8,
                        color: [[1, '#00ff88']]
                    }
                },
                pointer: { width: 3 },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                title: { offsetCenter: [0, '30%'], fontSize: 11, color: '#8ba3c7' },
                detail: { valueAnimation: true, fontSize: 18, color: '#00d4ff', offsetCenter: [0, '0%'] },
                data: [{ value: 99.2, name: 'Kafka' }]
            },
            {
                type: 'gauge',
                center: ['50%', '55%'],
                radius: '70%',
                startAngle: 200,
                endAngle: -20,
                min: 0,
                max: 100,
                splitNumber: 5,
                axisLine: {
                    lineStyle: {
                        width: 8,
                        color: [[1, '#00d4ff']]
                    }
                },
                pointer: { width: 3 },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                title: { offsetCenter: [0, '30%'], fontSize: 11, color: '#8ba3c7' },
                detail: { valueAnimation: true, fontSize: 18, color: '#00d4ff', offsetCenter: [0, '0%'] },
                data: [{ value: 97.8, name: 'Flink' }]
            },
            {
                type: 'gauge',
                center: ['75%', '55%'],
                radius: '70%',
                startAngle: 200,
                endAngle: -20,
                min: 0,
                max: 100,
                splitNumber: 5,
                axisLine: {
                    lineStyle: {
                        width: 8,
                        color: [[0.85, '#00ff88'], [1, '#ffa502']]
                    }
                },
                pointer: { width: 3 },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                title: { offsetCenter: [0, '30%'], fontSize: 11, color: '#8ba3c7' },
                detail: { valueAnimation: true, fontSize: 18, color: '#ffa502', offsetCenter: [0, '0%'] },
                data: [{ value: 91.5, name: 'Hive' }]
            }
        ]
    };
    
    charts.pipelineStatus.setOption(option);
}

// 工具函数：生成时间序列数据
function generateTimeSeriesData(count, baseValue, variance) {
    const data = [];
    let current = baseValue;
    for (let i = 0; i < count; i++) {
        current += (Math.random() - 0.5) * variance;
        current = Math.max(50, Math.min(140, current));
        data.push(Math.round(current));
    }
    return data;
}

// 生成时间标签
function generateTimeLabels(count) {
    const labels = [];
    const now = new Date();
    for (let i = count - 1; i >= 0; i--) {
        const time = new Date(now - i * 60000);
        labels.push(time.getHours().toString().padStart(2, '0') + ':' + 
                     time.getMinutes().toString().padStart(2, '0'));
    }
    return labels;
}

// 启动实时数据更新
function startRealtimeUpdate() {
    updateInterval = setInterval(function() {
        updateRealtimeData();
    }, 3000); // 每3秒更新一次
}

// 更新实时数据
function updateRealtimeData() {
    // 更新心率图表
    if (charts.heartRate) {
        const newData = generateTimeSeriesData(1, 74, 8)[0];
        const option = charts.heartRate.getOption();
        option.series[0].data.shift();
        option.series[0].data.push(newData);
        option.xAxis.data.shift();
        option.xAxis.data.push(new Date().toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'}));
        charts.heartRate.setOption(option);
        
        // 更新KPI显示
        document.getElementById('avgHeartRate').textContent = newData;
    }
    
    // 随机更新KPI数值
    const onlineUsers = parseInt(document.getElementById('onlineUsers').textContent.replace(/,/g, ''));
    const newOnlineUsers = onlineUsers + Math.floor(Math.random() * 20 - 10);
    document.getElementById('onlineUsers').textContent = newOnlineUsers.toLocaleString();
    
    const alertCount = parseInt(document.getElementById('alertCount').textContent);
    const newAlertCount = Math.max(0, alertCount + Math.floor(Math.random() * 5 - 2));
    document.getElementById('alertCount').textContent = newAlertCount;
    
    // 模拟新增警报
    if (Math.random() > 0.7) {
        addRandomAlert();
    }
}

// 添加随机警报
function addRandomAlert() {
    const alertTypes = [
        { type: 'critical', icon: '!', class: 'alert-critical', titles: ['血压异常', '体温过高', '心率危急'] },
        { type: 'warning', icon: '⚠', class: 'alert-high', titles: ['心率偏高', '活动量过低', '睡眠不足'] },
        { type: 'info', icon: 'ℹ', class: 'alert-medium', titles: ['健康趋势变化', '设备离线提醒', '数据延迟警告'] }
    ];
    
    const alert = alertTypes[Math.floor(Math.random() * alertTypes.length)];
    const userId = Math.floor(Math.random() * 2000) + 1000;
    const title = alert.titles[Math.floor(Math.random() * alert.titles.length)];
    
    const alertHtml = `
        <div class="alert-item ${alert.type}">
            <div class="alert-icon ${alert.class}">${alert.icon}</div>
            <div class="alert-content">
                <div class="alert-title">用户#${userId} ${title}</div>
                <div class="alert-time">刚刚 · 自动检测</div>
            </div>
        </div>
    `;
    
    const alertList = document.getElementById('alertList');
    alertList.insertAdjacentHTML('afterbegin', alertHtml);
    
    // 保持最多显示8条警报
    while (alertList.children.length > 8) {
        alertList.removeChild(alertList.lastChild);
    }
}

// 响应式调整
function handleResize() {
    Object.values(charts).forEach(chart => {
        if (chart && chart.resize) {
            chart.resize();
        }
    });
}