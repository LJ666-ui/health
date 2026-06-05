-- =====================================================
-- ZhiHealth 智慧健康大数据平台 - Hive数据仓库架构
-- 采用分层设计: ODS -> DWD -> DWS -> ADS
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS zhihealth_warehouse
COMMENT 'ZhiHealth健康数据仓库'
LOCATION '/user/hive/warehouse/zhihealth_warehouse'
WITH DBPROPERTIES ('creator' = 'zhihealth', 'version' = '1.0');

USE zhihealth_warehouse;

-- =====================================================
-- ODS层 (Operational Data Store) - 原始数据层
-- =====================================================

-- 健康原始数据表 (ODS)
CREATE EXTERNAL TABLE IF NOT EXISTS ods_health_raw_data (
    record_id BIGINT COMMENT '记录ID',
    user_id BIGINT COMMENT '用户ID',
    device_id BIGINT COMMENT '设备ID',
    device_type STRING COMMENT '设备类型',
    data_type STRING COMMENT '数据类型(heart_rate/body_temp/blood_pressure/steps/sleep)',
    heart_rate DECIMAL(6,2) COMMENT '心率',
    body_temp DECIMAL(4,2) COMMENT '体温',
    blood_pressure_systolic INT COMMENT '收缩压',
    blood_pressure_diastolic INT COMMENT '舒张压',
    steps INT COMMENT '步数',
    sleep_hours DECIMAL(4,2) COMMENT '睡眠时长',
    data_value STRING COMMENT '原始数据值(JSON格式)',
    collect_time TIMESTAMP COMMENT '采集时间',
    receive_time TIMESTAMP COMMENT '接收时间',
    source_system STRING COMMENT '来源系统',
    etl_time TIMESTAMP COMMENT 'ETL处理时间'
)
COMMENT 'ODS层-健康原始数据'
PARTITIONED BY (dt STRING COMMENT '日期分区', hour STRING COMMENT '小时分区')
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\t'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 用户信息表 (ODS)
CREATE EXTERNAL TABLE IF NOT EXISTS ods_user_info (
    user_id BIGINT COMMENT '用户ID',
    username STRING COMMENT '用户名',
    gender STRING COMMENT '性别(M/F)',
    age INT COMMENT '年龄',
    height DECIMAL(5,2) COMMENT '身高(cm)',
    weight DECIMAL(5,2) COMMENT '体重(kg)',
    phone STRING COMMENT '手机号',
    email STRING COMMENT '邮箱',
    address STRING COMMENT '地址',
    create_time TIMESTAMP COMMENT '创建时间',
    update_time TIMESTAMP COMMENT '更新时间'
)
COMMENT 'ODS层-用户基础信息'
PARTITIONED BY (dt STRING COMMENT '日期分区')
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\t'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 设备信息表 (ODS)
CREATE EXTERNAL TABLE IF NOT EXISTS ods_device_info (
    device_id BIGINT COMMENT '设备ID',
    device_name STRING COMMENT '设备名称',
    device_type STRING COMMENT '设备类型(smartwatch/scale/thermometer/band)',
    device_model STRING COMMENT '设备型号',
    manufacturer STRING COMMENT '制造商',
    firmware_version STRING COMMENT '固件版本',
    user_id BIGINT COMMENT '绑定用户ID',
    status STRING COMMENT '设备状态(active/inactive/offline)',
    last_active_time TIMESTAMP COMMENT '最后活跃时间',
    create_time TIMESTAMP COMMENT '创建时间'
)
COMMENT 'ODS层-设备信息'
PARTITIONED BY (dt STRING COMMENT '日期分区')
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\t'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- =====================================================
-- DWD层 (Data Warehouse Detail) - 明细数据层
-- =====================================================

-- 心率明细表 (DWD)
CREATE TABLE IF NOT EXISTS dwd_heart_rate_detail (
    detail_id BIGINT COMMENT '明细ID',
    user_id BIGINT COMMENT '用户ID',
    device_id BIGINT COMMENT '设备ID',
    heart_rate DECIMAL(6,2) COMMENT '心率值',
    measure_time TIMESTAMP COMMENT '测量时间',
    quality_score INT COMMENT '数据质量评分(1-100)',
    is_abnormal BOOLEAN COMMENT '是否异常'
)
COMMENT 'DWD层-心率明细数据'
PARTITIONED BY (dt STRING COMMENT '日期分区')
CLUSTERED BY (user_id) INTO 32 BUCKETS
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 血压明细表 (DWD)
CREATE TABLE IF NOT EXISTS dwd_blood_pressure_detail (
    detail_id BIGINT COMMENT '明细ID',
    user_id BIGINT COMMENT '用户ID',
    device_id BIGINT COMMENT '设备ID',
    systolic INT COMMENT '收缩压',
    diastolic INT COMMENT '舒张压',
    pulse_rate INT COMMENT '脉率',
    measure_time TIMESTAMP COMMENT '测量时间',
    body_position STRING COMMENT '体位(sitting/standing/lying)',
    is_abnormal BOOLEAN COMMENT '是否异常',
    bp_level STRING COMMENT '血压等级(normal/elevated/high_stage1/high_stage2/crisis)'
)
COMMENT 'DWD层-血压明细数据'
PARTITIONED BY (dt STRING COMMENT '日期分区')
CLUSTERED BY (user_id) INTO 32 BUCKETS
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 活动量明细表 (DWD)
CREATE TABLE IF NOT EXISTS dwd_activity_detail (
    detail_id BIGINT COMMENT '明细ID',
    user_id BIGINT COMMENT '用户ID',
    device_id BIGINT COMMENT '设备ID',
    steps INT COMMENT '步数',
    distance DECIMAL(8,2) COMMENT '距离(米)',
    calories DECIMAL(8,2) COMMENT '消耗卡路里',
    activity_minutes INT COMMENT '活动时长(分钟)',
    activity_type STRING COMMENT '活动类型(walking/running/cycling/etc)',
    record_date DATE COMMENT '记录日期'
)
COMMENT 'DWD层-活动量明细数据'
PARTITIONED BY (dt STRING COMMENT '日期分区')
CLUSTERED BY (user_id) INTO 32 BUCKETS
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 睡眠明细表 (DWD)
CREATE TABLE IF NOT EXISTS dwd_sleep_detail (
    detail_id BIGINT COMMENT '明细ID',
    user_id BIGINT COMMENT '用户ID',
    device_id BIGINT COMMENT '设备ID',
    total_sleep_hours DECIMAL(4,2) COMMENT '总睡眠时长',
    deep_sleep_hours DECIMAL(4,2) COMMENT '深睡时长',
    light_sleep_hours DECIMAL(4,2) COMMENT '浅睡时长',
    rem_sleep_hours DECIMAL(4,2) COMMENT 'REM睡眠时长',
    awake_times INT COMMENT '清醒次数',
    sleep_quality_score INT COMMENT '睡眠质量评分(0-100)',
    bed_time TIMESTAMP COMMENT '入睡时间',
    wake_time TIMESTAMP COMMENT '起床时间',
    record_date DATE COMMENT '记录日期'
)
COMMENT 'DWD层-睡眠明细数据'
PARTITIONED BY (dt STRING COMMENT '日期分区')
CLUSTERED BY (user_id) INTO 32 BUCKETS
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- =====================================================
-- DWS层 (Data Warehouse Summary) - 汇总数据层
-- =====================================================

-- 用户日健康汇总表 (DWS)
CREATE TABLE IF NOT EXISTS dws_user_daily_health_summary (
    summary_id BIGINT COMMENT '汇总ID',
    user_id BIGINT COMMENT '用户ID',
    stat_date DATE COMMENT '统计日期',
    
    -- 心率汇总
    avg_heart_rate DECIMAL(6,2) COMMENT '平均心率',
    max_heart_rate DECIMAL(6,2) COMMENT '最大心率',
    min_heart_rate DECIMAL(6,2) COMMENT '最小心率',
    heart_rate_variance DECIMAL(8,4) COMMENT '心率方差',
    
    -- 血压汇总
    avg_systolic INT COMMENT '平均收缩压',
    avg_diastolic INT COMMENT '平均舒张压',
    max_systolic INT COMMENT '最大收缩压',
    min_diastolic INT COMMENT '最小舒张压',
    
    -- 活动汇总
    total_steps BIGINT COMMENT '总步数',
    total_distance DECIMAL(10,2) COMMENT '总距离(米)',
    total_calories DECIMAL(10,2) COMMENT '总卡路里',
    active_minutes INT COMMENT '活跃分钟数',
    
    -- 睡眠汇总
    avg_sleep_hours DECIMAL(4,2) COMMENT '平均睡眠时长',
    avg_deep_sleep_ratio DECIMAL(4,4) COMMENT '深睡比例',
    avg_sleep_quality_score INT COMMENT '平均睡眠质量分',
    
    -- 综合指标
    health_score INT COMMENT '综合健康评分(0-100)',
    data_completeness DECIMAL(4,4) COMMENT '数据完整度',
    abnormal_count INT COMMENT '异常次数',
    
    update_time TIMESTAMP COMMENT '更新时间'
)
COMMENT 'DWS层-用户每日健康数据汇总'
PARTITIONED BY (dt STRING COMMENT '月份分区(yyyyMM)')
CLUSTERED BY (user_id) INTO 16 BUCKETS
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 用户周健康汇总表 (DWS)
CREATE TABLE IF NOT EXISTS dws_user_weekly_health_summary (
    summary_id BIGINT,
    user_id BIGINT,
    week_start_date DATE COMMENT '周起始日期',
    week_end_date DATE COMMENT '周结束日期',
    week_number INT COMMENT '周数',
    
    avg_daily_steps BIGINT COMMENT '日均步数',
    avg_heart_rate DECIMAL(6,2) COMMENT '平均心率',
    avg_blood_pressure STRING COMMENT '平均血压(收缩压/舒张压)',
    avg_sleep_hours DECIMAL(4,2) COMMENT '日均睡眠',
    total_calories DECIMAL(12,2) COMMENT '周总消耗卡路里',
    
    step_goal_achievement DECIMAL(4,4) COMMENT '步数目标达成率',
    trend_vs_last_week STRING COMMENT '与上周对比(up/down/stable)',
    health_trend_score INT COMMENT '健康趋势评分',
    
    create_time TIMESTAMP
)
COMMENT 'DWS层-用户每周健康数据汇总'
PARTITIONED BY (year_week STRING COMMENT '年周分区(yyyyWW)')
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 用户月度健康趋势表 (DWS)
CREATE TABLE IF NOT EXISTS dws_user_monthly_health_trend (
    trend_id BIGINT,
    user_id BIGINT,
    year_month STRING COMMENT '年月(yyyyMM)',
    
    monthly_avg_heart_rate DECIMAL(6,2),
    monthly_avg_systolic INT,
    monthly_avg_diastolic INT,
    monthly_total_steps BIGINT,
    monthly_avg_sleep DECIMAL(4,2),
    monthly_avg_calories DECIMAL(12,2),
    
    month_over_month_change STRING COMMENT '环比变化',
    health_improvement_index DECIMAL(4,4) COMMENT '健康改善指数',
    risk_level STRING COMMENT '风险等级(low/medium/high)',
    
    create_time TIMESTAMP
)
COMMENT 'DWS层-用户月度健康趋势分析'
PARTITIONED BY (year_month_part STRING COMMENT '季度分区(yyyyQq)')
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- =====================================================
-- ADS层 (Application Data Service) - 应用数据层
-- =====================================================

-- 用户健康画像宽表 (ADS)
CREATE TABLE IF NOT EXISTS ads_user_health_profile (
    profile_id BIGINT,
    user_id BIGINT,
    
    -- 基础画像
    age_group STRING COMMENT '年龄段(young/middle-aged/senior)',
    bmi_category STRING COMMENT 'BMI分类(underweight/normal/overweight/obese)',
    activity_level STRING COMMENT '活动水平(sedentary/moderate/active/very_active)',
    
    -- 心血管健康
    cardiovascular_risk_score INT COMMENT '心血管风险评分(0-100)',
    bp_trend STRING COMMENT '血压趋势(improving/stable/worsening)',
    hr_variability DECIMAL(6,2) COMMENT '心率变异性',
    
    -- 睡眠质量
    sleep_pattern_type STRING COMMENT '睡眠模式(normal/insomnia/irregular)',
    chronic_fatigue_risk STRING COMMENT '慢性疲劳风险(low/medium/high)',
    
    -- 综合评估
    overall_health_grade STRING COMMENT '健康等级(A/B/C/D/E)',
    health_age INT COMMENT '健康年龄',
    biological_age_diff INT COMMENT '生物年龄差(正=比实际年轻)',
    wellness_index DECIMAL(4,4) COMMENT '健康指数(0-1)',
    
    -- 风险预警
    risk_alerts ARRAY<STRING> COMMENT '风险预警列表',
    recommendations ARRAY<STRING> COMMENT '个性化建议',
    
    last_update_time TIMESTAMP
)
COMMENT 'ADS层-用户健康画像'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 区域健康统计报表 (ADS)
CREATE TABLE IF NOT EXISTS ads_region_health_statistics (
    stat_id BIGINT,
    region_code STRING COMMENT '区域编码',
    region_name STRING COMMENT '区域名称',
    stat_date DATE,
    
    total_users INT COMMENT '总用户数',
    active_users INT COMMENT '活跃用户数',
    
    avg_heart_rate DECIMAL(6,2) COMMENT '区域平均心率',
    avg_bp_systolic INT COMMENT '区域平均收缩压',
    avg_steps INT COMMENT '区域平均步数',
    avg_sleep_hours DECIMAL(4,2) COMMENT '区域平均睡眠',
    
    hypertension_rate DECIMAL(4,4) COMMENT '高血压患病率',
    obesity_rate DECIMAL(4,4) COMMENT '肥胖率',
    subhealth_rate DECIMAL(4,4) COMMENT '亚健康比例',
    
    health_index_ranking INT COMMENT '健康指数排名',
    create_time TIMESTAMP
)
COMMENT 'ADS层-区域健康统计分析'
PARTITIONED BY (year_month STRING COMMENT '年月分区')
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 实时健康大屏数据 (ADS)
CREATE TABLE IF NOT EXISTS ads_realtime_health_dashboard (
    dashboard_id BIGINT,
    metric_name STRING COMMENT '指标名称',
    metric_value DECIMAL(20,4) COMMENT '指标值',
    metric_unit STRING COMMENT '单位',
    dimension_type STRING COMMENT '维度类型(user/device/region/time)',
    dimension_value STRING COMMENT '维度值',
    comparison_type STRING COMMENT '对比类型(day_over_day/week_over_week/month_over_month)',
    change_rate DECIMAL(6,4) COMMENT '变化率',
    alert_threshold DECIMAL(10,4) COMMENT '告警阈值',
    is_alert BOOLEAN COMMENT '是否触发告警',
    update_time TIMESTAMP
)
COMMENT 'ADS层-实时健康大屏数据'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');