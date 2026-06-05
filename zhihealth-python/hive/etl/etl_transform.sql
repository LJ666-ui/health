-- =====================================================
-- ZhiHealth Hive数仓 ETL脚本
-- 数据流转: ODS -> DWD -> DWS -> ADS
-- =====================================================

-- =====================================================
-- 1. ODS层到DWD层数据转换
-- =====================================================

-- 1.1 心率数据清洗 (ODS -> DWD)
INSERT OVERWRITE TABLE dwd_heart_rate_detail 
PARTITION (dt = '${hivevar:batch_date}')
SELECT 
    row_number() over (order by record_id) as detail_id,
    user_id,
    device_id,
    heart_rate,
    cast(collect_time as timestamp) as measure_time,
    CASE 
        WHEN heart_rate IS NOT NULL AND heart_rate BETWEEN 40 AND 200 THEN 100
        WHEN heart_rate IS NOT NULL AND (heart_rate < 40 OR heart_rate > 200) THEN 50
        ELSE 0
    END as quality_score,
    CASE 
        WHEN heart_rate < 50 OR heart_rate > 120 THEN TRUE
        ELSE FALSE
    END as is_abnormal
FROM ods_health_raw_data
WHERE dt = '${hivevar:batch_date}'
  AND data_type = 'heart_rate'
  AND heart_rate IS NOT NULL;

-- 1.2 血压数据清洗与分类 (ODS -> DWD)
INSERT OVERWRITE TABLE dwd_blood_pressure_detail 
PARTITION (dt = '${hivevar:batch_date}')
SELECT 
    row_number() over (order by record_id) as detail_id,
    user_id,
    device_id,
    blood_pressure_systolic as systolic,
    blood_pressure_diastolic as diastolic,
    CAST(ROUND((blood_pressure_systolic - blood_pressure_diastolic) * 0.8 + 60, 0) AS INT) as pulse_rate,
    cast(collect_time as timestamp) as measure_time,
    'sitting' as body_position,
    CASE 
        WHEN blood_pressure_systolic >= 180 OR blood_pressure_diastolic >= 120 THEN TRUE
        ELSE FALSE
    END as is_abnormal,
    CASE 
        WHEN blood_pressure_systolic < 120 AND blood_pressure_diastolic < 80 THEN 'normal'
        WHEN blood_pressure_systolic < 130 AND blood_pressure_diastolic < 80 THEN 'elevated'
        WHEN blood_pressure_systolic < 140 OR blood_pressure_diastolic < 90 THEN 'high_stage1'
        WHEN blood_pressure_systolic < 180 OR blood_pressure_diastolic < 120 THEN 'high_stage2'
        ELSE 'crisis'
    END as bp_level
FROM ods_health_raw_data
WHERE dt = '${hivevar:batch_date}'
  AND data_type = 'blood_pressure'
  AND blood_pressure_systolic IS NOT NULL
  AND blood_pressure_diastolic IS NOT NULL;

-- 1.3 活动量数据转换 (ODS -> DWD)
INSERT OVERWRITE TABLE dwd_activity_detail 
PARTITION (dt = '${hivevar:batch_date}')
SELECT 
    row_number() over (order by record_id) as detail_id,
    user_id,
    device_id,
    steps,
    ROUND(steps * 0.7, 2) as distance,
    ROUND(steps * 0.04, 2) as calories,
    CASE 
        WHEN steps > 10000 THEN 90
        WHEN steps > 7500 THEN 60
        WHEN steps > 5000 THEN 30
        ELSE 10
    END as activity_minutes,
    CASE 
        WHEN steps > 15000 THEN 'running'
        WHEN steps > 8000 THEN 'walking'
        ELSE 'light_activity'
    END as activity_type,
    cast(collect_time as DATE) as record_date
FROM ods_health_raw_data
WHERE dt = '${hivevar:batch_date}'
  AND data_type = 'steps'
  AND steps IS NOT NULL;

-- 1.4 睡眠数据转换 (ODS -> DWD)
INSERT OVERWRITE TABLE dwd_sleep_detail 
PARTITION (dt = '${hivevar:batch_date}')
SELECT 
    row_number() over (order by record_id) as detail_id,
    user_id,
    device_id,
    sleep_hours as total_sleep_hours,
    ROUND(sleep_hours * 0.25, 2) as deep_sleep_hours,
    ROUND(sleep_hours * 0.55, 2) as light_sleep_hours,
    ROUND(sleep_hours * 0.20, 2) as rem_sleep_hours,
    CASE 
        WHEN sleep_hours BETWEEN 7 AND 9 THEN 0
        WHEN sleep_hours BETWEEN 6 AND 7 OR sleep_hours BETWEEN 9 AND 10 THEN 1
        ELSE FLOOR(RAND() * 3 + 1)
    END as awake_times,
    CASE 
        WHEN sleep_hours BETWEEN 7 AND 9 THEN 95
        WHEN sleep_hours BETWEEN 6.5 AND 7 OR sleep_hours BETWEEN 9 AND 10 THEN 80
        WHEN sleep_hours BETWEEN 6 AND 6.5 OR sleep_hours BETWEEN 10 AND 11 THEN 65
        ELSE 40
    END as sleep_quality_score,
    date_sub(cast(collect_time as TIMESTAMP), INTERVAL RAND()*2 HOUR) as bed_time,
    cast(collect_time as TIMESTAMP) as wake_time,
    cast(collect_time as DATE) as record_date
FROM ods_health_raw_data
WHERE dt = '${hivevar:batch_date}'
  AND data_type = 'sleep'
  AND sleep_hours IS NOT NULL;

-- =====================================================
-- 2. DWD层到DWS层数据聚合
-- =====================================================

-- 2.1 用户日健康汇总 (DWD -> DWS)
INSERT OVERWRITE TABLE dws_user_daily_health_summary 
PARTITION (dt = SUBSTRING('${hivevar:batch_date}', 1, 6))
SELECT 
    CONCAT(user_id, '_', '${hivevar:batch_date}') as summary_id,
    t1.user_id,
    cast('${hivevar:batch_date}' as DATE) as stat_date,
    
    -- 心率汇总
    COALESCE(t_hr.avg_hr, 0) as avg_heart_rate,
    COALESCE(t_hr.max_hr, 0) as max_heart_rate,
    COALESCE(t_hr.min_hr, 0) as min_heart_rate,
    COALESCE(t_hr.hr_var, 0) as heart_rate_variance,
    
    -- 血压汇总
    COALESCE(t_bp.avg_sys, 0) as avg_systolic,
    COALESCE(t_bp.avg_dia, 0) as avg_diastolic,
    COALESCE(t_bp.max_sys, 0) as max_systolic,
    COALESCE(t_bp.min_dia, 0) as min_diastolic,
    
    -- 活动汇总
    COALESCE(t_act.total_steps, 0) as total_steps,
    COALESCE(t_act.total_dist, 0) as total_distance,
    COALESCE(t_act.total_cal, 0) as total_calories,
    COALESCE(t_act.active_min, 0) as active_minutes,
    
    -- 睡眠汇总
    COALESCE(t_slp.avg_sleep, 0) as avg_sleep_hours,
    COALESCE(t_slp.avg_deep_ratio, 0) as avg_deep_sleep_ratio,
    COALESCE(t_slp.avg_sleep_score, 0) as avg_sleep_quality_score,
    
    -- 综合指标
    -- 健康评分算法：心率(25%) + 血压(25%) + 活动(25%) + 睡眠(25%)
    CAST(
        (
            COALESCE(CASE WHEN t_hr.avg_hr BETWEEN 60 AND 100 THEN 100 
                      WHEN t_hr.avg_hr BETWEEN 50 AND 110 THEN 70 ELSE 40 END, 0) * 0.25 +
            COALESCE(CASE WHEN t_bp.avg_sys < 120 AND t_bp.avg_dia < 80 THEN 100 
                      WHEN t_bp.avg_sys < 140 OR t_bp.avg_dia < 90 THEN 70 ELSE 40 END, 0) * 0.25 +
            COALESCE(CASE WHEN t_act.total_steps >= 10000 THEN 100 
                      WHEN t_act.total_steps >= 7500 THEN 70 ELSE 40 END, 0) * 0.25 +
            COALESCE(t_slp.avg_sleep_score, 0) * 0.25
        ) AS INT
    ) as health_score,
    
    -- 数据完整度
    (
        (CASE WHEN t_hr.user_id IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN t_bp.user_id IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN t_act.user_id IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN t_slp.user_id IS NOT NULL THEN 1 ELSE 0 END) / 4.0
    ) as data_completeness,
    
    -- 异常次数统计
    COALESCE(t_hr.abnormal_count, 0) + 
    COALESCE(t_bp.abnormal_count, 0) as abnormal_count,
    
    current_timestamp() as update_time
    
FROM (SELECT DISTINCT user_id FROM ods_health_raw_data WHERE dt = '${hivevar:batch_date}') t_base

LEFT JOIN (
    SELECT 
        user_id,
        AVG(heart_rate) as avg_hr,
        MAX(heart_rate) as max_hr,
        MIN(heart_rate) as min_hr,
        VARIANCE(heart_rate) as hr_var,
        SUM(CASE WHEN is_abnormal = TRUE THEN 1 ELSE 0 END) as abnormal_count
    FROM dwd_heart_rate_detail
    WHERE dt = '${hivevar:batch_date}'
    GROUP BY user_id
) t_hr ON t_base.user_id = t_hr.user_id

LEFT JOIN (
    SELECT 
        user_id,
        AVG(systolic) as avg_sys,
        AVG(diastolic) as avg_dia,
        MAX(systolic) as max_sys,
        MIN(diastolic) as min_dia,
        SUM(CASE WHEN is_abnormal = TRUE THEN 1 ELSE 0 END) as abnormal_count
    FROM dwd_blood_pressure_detail
    WHERE dt = '${hivevar:batch_date}'
    GROUP BY user_id
) t_bp ON t_base.user_id = t_bp.user_id

LEFT JOIN (
    SELECT 
        user_id,
        SUM(steps) as total_steps,
        SUM(distance) as total_dist,
        SUM(calories) as total_cal,
        SUM(activity_minutes) as active_min
    FROM dwd_activity_detail
    WHERE dt = '${hivevar:batch_date}'
    GROUP BY user_id
) t_act ON t_base.user_id = t_act.user_id

LEFT JOIN (
    SELECT 
        user_id,
        AVG(total_sleep_hours) as avg_sleep,
        AVG(deep_sleep_hours/NULLIF(total_sleep_hours, 0)) as avg_deep_ratio,
        AVG(sleep_quality_score) as avg_sleep_score
    FROM dwd_sleep_detail
    WHERE dt = '${hivevar:batch_date}'
    GROUP BY user_id
) t_slp ON t_base.user_id = t_slp.user_id;

-- =====================================================
-- 3. DWS层到ADS层数据应用
-- =====================================================

-- 3.1 用户健康画像生成 (DWS -> ADS)
INSERT OVERWRITE TABLE ads_user_health_profile
SELECT 
    ROW_NUMBER() OVER (ORDER BY u.user_id) as profile_id,
    u.user_id,
    
    -- 年龄段分组
    CASE 
        WHEN u.age < 35 THEN 'young'
        WHEN u.age < 55 THEN 'middle-aged'
        ELSE 'senior'
    END as age_group,
    
    -- BMI计算与分类
    CASE 
        WHEN u.weight / POWER(u.height/100, 2) < 18.5 THEN 'underweight'
        WHEN u.weight / POWER(u.height/100, 2) < 24 THEN 'normal'
        WHEN u.weight / POWER(u.height/100, 2) < 28 THEN 'overweight'
        ELSE 'obese'
    END as bmi_category,
    
    -- 活动水平评估
    CASE 
        WHEN dws.avg_daily_steps > 12000 THEN 'very_active'
        WHEN dws.avg_daily_steps > 8000 THEN 'active'
        WHEN dws.avg_daily_steps > 5000 THEN 'moderate'
        ELSE 'sedentary'
    END as activity_level,
    
    -- 心血管风险评分
    CAST(
        CASE 
            WHEN dws_monthly.avg_systolic > 140 OR dws_monthly.avg_diastolic > 90 THEN 
                LEAST(100, 50 + (dws_monthly.avg_systolic - 120) * 1.5 + (dws_monthly.avg_diastolic - 80) * 2)
            WHEN dws.heart_rate_variance > 200 THEN 65
            ELSE 30
        END AS INT
    ) as cardiovascular_risk_score,
    
    -- 血压趋势分析
    CASE 
        WHEN LAG(dws_monthly.avg_systolic) OVER (PARTITION BY u.user_id ORDER BY dws_monthly.year_month) IS NULL THEN 'stable'
        WHEN dws_monthly.avg_systolic < LAG(dws_monthly.avg_systolic) OVER (PARTITION BY u.user_id ORDER BY dws_monthly.year_month) THEN 'improving'
        WHEN dws_monthly.avg_systolic - LAG(dws_monthly.avg_systolic) OVER (PARTITION BY u.user_id ORDER BY dws_monthly.year_month) < 5 THEN 'stable'
        ELSE 'worsening'
    END as bp_trend,
    
    SQRT(dws.heart_rate_variance) as hr_variability,
    
    -- 睡眠模式识别
    CASE 
        WHEN dws.avg_sleep_hours < 6 THEN 'insomnia'
        WHEN dws.avg_sleep_quality_score < 60 THEN 'irregular'
        ELSE 'normal'
    END as sleep_pattern_type,
    
    CASE 
        WHEN dws.avg_sleep_quality_score < 50 AND dws.avg_sleep_hours < 6 THEN 'high'
        WHEN dws.avg_sleep_quality_score < 70 THEN 'medium'
        ELSE 'low'
    END as chronic_fatigue_risk,
    
    -- 综合健康等级
    CASE 
        WHEN dws.health_score >= 85 THEN 'A'
        WHEN dws.health_score >= 70 THEN 'B'
        WHEN dws.health_score >= 55 THEN 'C'
        WHEN dws.health_score >= 40 THEN 'D'
        ELSE 'E'
    END as overall_health_grade,
    
    -- 健康年龄估算（简化算法）
    CAST(u.age - (dws.health_score - 60) / 4 AS INT) as health_age,
    CAST(u.age - (dws.health_score - 60) / 4 - u.age AS INT) as biological_age_diff,
    
    dws.health_score / 100.0 as wellness_index,
    
    -- 风险预警列表
    COLLECT_LIST(
        CASE 
            WHEN dws_monthly.avg_systolic > 140 THEN '高血压风险'
            WHEN dws.health_score < 50 THEN '综合健康风险'
            WHEN dws.avg_sleep_hours < 5.5 THEN '睡眠不足风险'
            WHEN dws.avg_daily_steps < 3000 THEN '缺乏运动风险'
            ELSE NULL
        END
    ) as risk_alerts,
    
    -- 个性化建议
    COLLECT_LIST(
        CASE 
            WHEN dws.health_score >= 85 THEN '保持当前健康生活方式'
            WHEN dws.activity_level = 'sedentary' THEN '建议增加日常活动量至每天8000步以上'
            WHEN dws.sleep_pattern_type = 'insomnia' THEN '建议调整作息时间，保证7-8小时睡眠'
            WHEN cardiovascular_risk_score > 60 THEN '建议定期监测血压，低盐饮食'
            WHEN dws.avg_sleep_quality_score < 70 THEN '改善睡眠环境，避免睡前使用电子设备'
            ELSE '继续保持规律作息和适量运动'
        END
    ) as recommendations,
    
    current_timestamp() as last_update_time
    
FROM ods_user_info u

JOIN (
    SELECT 
        user_id,
        AVG(health_score) as health_score,
        AVG(avg_heart_rate) as avg_heart_rate,
        STDDEV_POP(avg_heart_rate) as heart_rate_variance,
        AVG(total_steps) as avg_daily_steps,
        AVG(avg_sleep_hours) as avg_sleep_hours,
        AVG(avg_sleep_quality_score) as avg_sleep_quality_score
    FROM dws_user_daily_health_summary
    WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)
    GROUP BY user_id
) dws ON u.user_id = dws.user_id

LEFT JOIN (
    SELECT 
        user_id,
        year_month,
        AVG(avg_systolic) as avg_systolic,
        AVG(avg_diastolic) as avg_diastolic
    FROM dws_user_monthly_health_trend
    WHERE year_month_part = SUBSTRING(CURRENT_DATE(), 1, 4) || 'Q' || QUARTER(CURRENT_DATE())
    GROUP BY user_id, year_month
) dws_monthly ON u.user_id = dws_monthly.user_id
ORDER BY u.user_id;

-- 3.2 区域健康统计报表 (DWS -> ADS)
INSERT OVERWRITE TABLE ads_region_health_statistics 
PARTITION (year_month = SUBSTRING('${hivevar:batch_date}', 1, 6))
SELECT 
    ROW_NUMBER() OVER (ORDER BY region_code) as stat_id,
    COALESCE(u.address, 'unknown') as region_code,
    COALESCE(u.address, '未知区域') as region_name,
    CAST('${hivevar:batch_date}' as DATE) as stat_date,
    
    COUNT(DISTINCT u.user_id) as total_users,
    COUNT(DISTINCT CASE WHEN dws.user_id IS NOT NULL THEN u.user_id END) as active_users,
    
    ROUND(AVG(dws.avg_heart_rate), 2) as avg_heart_rate,
    CAST(AVG(dws.avg_systolic) AS INT) as avg_bp_systolic,
    CAST(AVG(dws.total_steps) AS INT) as avg_steps,
    ROUND(AVG(dws.avg_sleep_hours), 2) as avg_sleep_hours,
    
    -- 高血压患病率（收缩压>=140或舒张压>=90）
    ROUND(
        SUM(CASE WHEN dws.avg_systolic >= 140 OR dws.avg_diastolic >= 90 THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(dws.user_id), 0), 
        4
    ) as hypertension_rate,
    
    -- 肥胖率（BMI>=28）
    ROUND(
        SUM(CASE WHEN u.weight / POWER(NULLIF(u.height, 0)/100, 2) >= 28 THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(u.user_id), 0),
        4
    ) as obesity_rate,
    
    -- 亚健康比例（健康评分<70）
    ROUND(
        SUM(CASE WHEN dws.health_score < 70 THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(dws.user_id), 0),
        4
    ) as subhealth_rate,
    
    -- 健康指数排名（基于平均健康分）
    RANK() OVER (ORDER BY AVG(dws.health_score) DESC) as health_index_ranking,
    
    current_timestamp() as create_time
    
FROM ods_user_info u
LEFT JOIN dws_user_daily_health_summary dws 
    ON u.user_id = dws.user_id 
    AND dt = SUBSTRING('${hivevar:batch_date}', 1, 6)
GROUP BY u.address;