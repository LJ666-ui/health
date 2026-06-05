-- =====================================================
-- ZhiHealth Hive数仓 - 数据分析与挖掘查询
-- 支持健康趋势预测、异常检测、群体分析等
-- =====================================================

-- =====================================================
-- 1. 健康趋势分析查询
-- =====================================================

-- 1.1 用户心率长期趋势分析（支持预测）
SELECT 
    user_id,
    year_month,
    monthly_avg_heart_rate,
    -- 月环比变化率
    ROUND(
        (monthly_avg_heart_rate - LAG(monthly_avg_heart_rate) OVER (
            PARTITION BY user_id ORDER BY year_month
        )) / NULLIF(LAG(monthly_avg_heart_rate) OVER (
            PARTITION BY user_id ORDER BY year_month
        ), 0) * 100, 
        2
    ) as mom_change_pct,
    -- 3个月移动平均
    AVG(monthly_avg_heart_rate) OVER (
        PARTITION BY user_id 
        ORDER BY year_month 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as ma_3month,
    -- 趋势判断
    CASE 
        WHEN monthly_avg_heart_rate > (
            AVG(monthly_avg_heart_rate) OVER (
                PARTITION BY user_id ORDER BY year_month ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
            )
        ) * 1.05 THEN 'rising'
        WHEN monthly_avg_heart_rate < (
            AVG(monthly_avg_heart_rate) OVER (
                PARTITION BY user_id ORDER BY year_month ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
            )
        ) * 0.95 THEN 'declining'
        ELSE 'stable'
    END as trend_direction
FROM dws_user_monthly_health_trend
WHERE user_id = ${user_id}
ORDER BY year_month;

-- 1.2 血压异常模式检测
WITH bp_analysis AS (
    SELECT 
        user_id,
        measure_time,
        systolic,
        diastolic,
        -- 计算个人历史均值和标准差
        AVG(systolic) OVER (PARTITION BY user_id) as avg_sys,
        STDDEV_POP(systolic) OVER (PARTITION by user_id) as std_sys,
        AVG(diastolic) over (PARTITION by user_id) as avg_dia,
        -- Z-Score标准化
        (systolic - AVG(systolic) OVER (PARTITION BY user_id)) / 
            NULLIF(STDDEV_POP(systolic) OVER (PARTITION by user_id), 0) as z_score_sys
    FROM dwd_blood_pressure_detail
    WHERE dt >= DATE_SUB(CURRENT_DATE(), 90)
)
SELECT 
    user_id,
    COUNT(*) as total_measurements,
    SUM(CASE WHEN z_score_sys > 2 OR z_score_sys < -2 THEN 1 ELSE 0 END) as abnormal_count,
    ROUND(AVG(systolic), 2) as avg_systolic,
    ROUND(AVG(diastolic), 2) as avg_diastolic,
    MAX(CASE WHEN z_score_sys > 3 THEN systolic END) as highest_abnormal_sys,
    -- 异常模式分类
    CASE 
        WHEN SUM(CASE WHEN z_score_sys > 2 THEN 1 ELSE 0 END) > COUNT(*) * 0.2 
             AND AVG(systolic) > 140 THEN 'persistent_hypertension'
        WHEN SUM(CASE WHEN z_score_sys < -2 THEN 1 ELSE 0 END) > COUNT(*) * 0.15 THEN 'hypotension_pattern'
        WHEN SUM(CASE WHEN ABS(z_score_sys) > 2 THEN 1 ELSE 0 END) > COUNT(*) * 0.3 THEN 'high_variability'
        WHEN SUM(CASE WHEN z_score_sys > 2 THEN 1 ELSE 0 END) > 0 THEN 'occasional_spikes'
        ELSE 'normal'
    END as anomaly_pattern,
    -- 风险等级评估
    CASE 
        WHEN AVG(systolic) > 160 OR SUM(CASE WHEN z_score_sys > 2.5 THEN 1 ELSE 0 END) > 5 THEN 'critical'
        WHEN AVG(systolic) > 140 OR SUM(CASE WHEN z_score_sys > 2 THEN 1 ELSE 0 END) > 3 THEN 'high_risk'
        WHEN AVG(systolic) > 130 OR SUM(CASE WHEN z_score_sys > 2 THEN 1 ELSE 0 END) > 0 THEN 'moderate_risk'
        ELSE 'low_risk'
    END as risk_level
FROM bp_analysis
GROUP BY user_id
HAVING abnormal_count > 0
ORDER BY risk_level, abnormal_count DESC;

-- =====================================================
-- 2. 用户群体细分与画像分析
-- =====================================================

-- 2.1 RFM模型应用于健康数据（最近一次活跃、频率、健康指标）
WITH user_health_rfm AS (
    SELECT 
        u.user_id,
        u.age,
        
        -- R: 最近一次数据上传距离今天的天数
        DATEDIFF(CURRENT_DATE(), MAX(dws.stat_date)) as recency_days,
        
        -- F: 近30天活跃天数（有完整数据的日期）
        COUNT(DISTINCT dws.stat_date) as frequency_days,
        
        -- M: 平均健康得分作为"价值"
        AVG(dws.health_score) as monetary_health_score
        
    FROM ods_user_info u
    JOIN dws_user_daily_health_summary dws ON u.user_id = dws.user_id
    WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)
      AND dws.stat_date >= DATE_SUB(CURRENT_DATE(), 30)
    GROUP BY u.user_id, u.age
),
rfm_scores AS (
    SELECT 
        *,
        -- R分数：越近越好（天数越少分越高）
        NTILE(4) OVER (ORDER BY recency_days DESC) as r_score,
        -- F分数：频率越高越好
        NTILE(4) OVER (ORDER BY frequency_days DESC) as f_score,
        -- M分数：健康分越高越好
        NTILE(4) OVER (ORDER BY monetary_health_score DESC) as m_score
    FROM user_health_rfm
)
SELECT 
    -- 用户分层
    CASE 
        WHEN r_score IN (3, 4) AND f_score IN (3, 4) AND m_score IN (3, 4) THEN 'health_champions'
        WHEN r_score IN (3, 4) AND f_score IN (3, 4) AND m_score IN (1, 2) THEN 'potential_improvers'
        WHEN r_score IN (1, 2) AND f_score IN (3, 4) THEN 'engaged_but_declining'
        WHEN r_score IN (3, 4) AND f_score IN (1, 2) THEN 'new_or_returning'
        WHEN r_score IN (1, 2) AND f_score IN (1, 2) AND m_score IN (1, 2) THEN 'at_risk_users'
        ELSE 'general_users'
    END as user_segment,
    
    COUNT(*) as user_count,
    
    ROUND(AVG(recency_days), 1) as avg_recency,
    ROUND(AVG(frequency_days), 1) as avg_frequency,
    ROUND(AVG(monetary_health_score), 1) as avg_health_score,
    ROUND(AVG(age), 1) as avg_age
    
FROM rfm_scores
GROUP BY 
    CASE 
        WHEN r_score IN (3, 4) AND f_score IN (3, 4) AND m_score IN (3, 4) THEN 'health_champions'
        WHEN r_score IN (3, 4) AND f_score IN (3, 4) AND m_score IN (1, 2) THEN 'potential_improvers'
        WHEN r_score IN (1, 2) AND f_score IN (3, 4) THEN 'engaged_but_declining'
        WHEN r_score IN (3, 4) AND f_score IN (1, 2) THEN 'new_or_returning'
        WHEN r_score IN (1, 2) AND f_score IN (1, 2) AND m_score IN (1, 2) THEN 'at_risk_users'
        ELSE 'general_users'
    END
ORDER BY avg_health_score DESC;

-- 2.2 慢性病风险人群筛选
SELECT 
    up.user_id,
    up.age_group,
    up.bmi_category,
    up.cardiovascular_risk_score,
    up.overall_health_grade,
    
    -- 高血压风险标识
    CASE 
        WHEN dws.avg_systolic >= 140 OR dws.avg_diastolic >= 90 THEN TRUE
        ELSE FALSE
    END as hypertension_risk_flag,
    
    -- 糖尿病风险简化评估（基于BMI+年龄+活动量）
    CASE 
        WHEN up.bmi_category IN ('overweight', 'obese') 
             AND up.activity_level IN ('sedentary', 'moderate')
             AND up.age_group IN ('middle-aged', 'senior')
        THEN 'high'
        WHEN up.bmi_category = 'overweight' OR up.age_group = 'senior' THEN 'medium'
        ELSE 'low'
    END as diabetes_risk_level,
    
    -- 心血管疾病综合风险
    CASE 
        WHEN up.cardiovascular_risk_score >= 70 THEN 'critical'
        WHEN up.cardiovascular_risk_score >= 50 THEN 'high'
        WHEN up.cardiovascular_risk_score >= 30 THEN 'moderate'
        ELSE 'low'
    END as cvd_overall_risk,
    
    -- 睡眠障碍风险
    CASE 
        WHEN up.sleep_pattern_type = 'insomnia' AND up.chronic_fatigue_risk = 'high' THEN 'high'
        WHEN up.sleep_pattern_type != 'normal' THEN 'medium'
        ELSE 'low'
    END as sleep_disorder_risk,

    -- 综合慢病风险指数（加权计算）
    CAST(
        (
            (CASE WHEN cardiovascular_risk_score >= 70 THEN 40 
                  WHEN cardiovascular_risk_score >= 50 THEN 25 
                  WHEN cardiovascular_risk_score >= 30 THEN 15 ELSE 5 END) +
            (CASE WHEN bmi_category = 'obese' THEN 30 
                  WHEN bmi_category = 'overweight' THEN 20 
                  WHEN bmi_category = 'underweight' THEN 10 ELSE 0 END) +
            (CASE WHEN activity_level = 'sedentary' THEN 25 
                  WHEN activity_level = 'moderate' THEN 15 
                  ELSE 5 END) +
            (CASE WHEN sleep_disorder_risk = 'high' THEN 20 
                  WHEN sleep_disorder_risk = 'medium' THEN 10 ELSE 0 END)
        ) AS INT
    ) as chronic_disease_risk_index
    
FROM ads_user_health_profile up
JOIN (
    SELECT user_id, AVG(avg_systolic) as avg_systolic, AVG(avg_diastolic) as avg_diastolic
    FROM dws_user_daily_health_summary
    WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)
    GROUP BY user_id
) dws ON up.user_id = dws.user_id
WHERE chronic_disease_risk_index >= 50  -- 只显示中高风险用户
ORDER BY chronic_disease_risk_index DESC;

-- =====================================================
-- 3. 时间序列分析与预测
-- =====================================================

-- 3.1 用户步数周度季节性分析
WITH weekly_steps AS (
    SELECT 
        user_id,
        WEEKOFYEAR(record_date) as week_num,
        YEAR(record_date) as year_val,
        SUM(steps) as total_weekly_steps,
        AVG(steps) as avg_daily_steps,
        -- 周几分布（假设record_date包含星期信息）
        DAYOFWEEK(record_date) as day_of_week
    FROM dwd_activity_detail
    WHERE dt >= DATE_SUB(CURRENT_DATE(), 365)
    GROUP BY user_id, record_date
)
SELECT 
    day_of_week,
    CASE day_of_week
        WHEN 1 THEN 'Sunday'
        WHEN 2 THEN 'Monday'
        WHEN 3 THEN 'Tuesday'
        WHEN 4 THEN 'Wednesday'
        WHEN 5 THEN 'Thursday'
        WHEN 6 THEN 'Friday'
        WHEN 7 THEN 'Saturday'
    END as day_name,
    
    ROUND(AVG(avg_daily_steps), 2) as avg_steps,
    ROUND(STDDEV(avg_daily_steps), 2) as steps_stddev,
    MIN(avg_daily_steps) as min_steps,
    MAX(avg_daily_steps) as max_steps,
    
    -- 与平均值的偏差百分比
    ROUND(
        (AVG(avg_daily_steps) - (SELECT AVG(avg_daily_steps) FROM weekly_steps)) / 
        (SELECT AVG(avg_daily_steps) FROM weekly_steps) * 100, 
        2
    ) as deviation_from_mean_pct,
    
    -- 活跃程度评级
    CASE 
        WHEN AVG(avg_daily_steps) > 12000 THEN 'very_active_day'
        WHEN AVG(avg_daily_steps) > 10000 THEN 'active_day'
        WHEN AVG(avg_daily_steps) > 8000 THEN 'moderate_day'
        ELSE 'low_activity_day'
    END as activity_rating
    
FROM weekly_steps
GROUP BY day_of_week
ORDER BY day_of_week;

-- 3.2 睡眠质量时间序列分解（趋势+周期）
WITH daily_sleep AS (
    SELECT 
        user_id,
        record_date,
        total_sleep_hours,
        sleep_quality_score,
        -- 提取月份用于季节性分析
        MONTH(record_date) as month_num,
        -- 星期几
        DAYOFWEEK(record_date) as dow
    FROM dwd_sleep_detail
    WHERE dt >= DATE_SUB(CURRENT_DATE(), 180)
),
sleep_stats AS (
    SELECT 
        month_num,
        dow,
        AVG(total_sleep_hours) as avg_sleep_hours,
        AVG(sleep_quality_score) as avg_sleep_quality,
        COUNT(*) as sample_count
    FROM daily_sleep
    GROUP BY month_num, dow
)
SELECT 
    s.month_num,
    CASE s.dow
        WHEN 1 THEN 'Sun' WHEN 2 THEN 'Mon' WHEN 3 THEN 'Tue'
        WHEN 4 THEN 'Wed' WHEN 5 THEN 'Thu' WHEN 6 THEN 'Fri' WHEN 7 THEN 'Sat'
    END as weekday,
    
    s.avg_sleep_hours,
    s.avg_sleep_quality,
    
    -- 月度趋势成分（当月平均值 vs 总体平均值）
    ROUND(
        (s.avg_sleep_hours - (SELECT AVG(avg_sleep_hours) FROM sleep_stats)) /
        NULLIF((SELECT AVG(avg_sleep_hours) FROM sleep_stats), 0) * 100, 
        2
    ) as seasonal_deviation_pct,
    
    -- 工作日 vs 周末效应
    CASE 
        WHEN s.dow IN (1, 7) THEN 'weekend'
        ELSE 'weekday'
    END as day_type,
    
    ROUND(s.avg_sleep_hours - 
          (SELECT AVG(avg_sleep_hours) FROM sleep_stats WHERE dow IN (1, 7)), 
          2
    ) as weekend_diff_vs_weekend_avg,
    
    ROUND(s.avg_sleep_hours - 
          (SELECT AVG(avg_sleep_hours) FROM sleep_stats WHERE dow NOT IN (1, 7)), 
          2
    ) as weekday_diff_vs_workday_avg
    
FROM sleep_stats s
ORDER BY s.month_num, s.dow;

-- =====================================================
-- 4. 关联规则挖掘（健康指标关联性）
-- =====================================================

-- 4.1 心率与睡眠质量关联分析
SELECT 
    CASE 
        WHEN hr.avg_hr < 60 THEN 'bradycardia'
        WHEN hr.avg_hr BETWEEN 60 AND 70 THEN 'low_normal'
        WHEN hr.avg_hr BETWEEN 71 AND 80 THEN 'normal'
        WHEN hr.avg_hr BETWEEN 81 AND 100 THEN 'elevated'
        ELSE 'tachycardia'
    END as heart_rate_category,
    
    CASE 
        WHEN slp.avg_sleep_quality >= 85 THEN 'excellent_sleep'
        WHEN slp.avg_sleep_quality >= 70 THEN 'good_sleep'
        WHEN slp.avg_sleep_quality >= 55 THEN 'fair_sleep'
        ELSE 'poor_sleep'
    END as sleep_quality_category,
    
    COUNT(*) as co_occurrence_count,
    
    -- 支持度
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM dws_user_daily_health_summary WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)), 4) as support,
    
    -- 心率类别条件下的睡眠质量置信度
    ROUND(
        COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 
            CASE 
                WHEN hr.avg_hr < 60 THEN 'bradycardia'
                WHEN hr.avg_hr BETWEEN 60 AND 70 THEN 'low_normal'
                WHEN hr.avg_hr BETWEEN 71 AND 80 THEN 'normal'
                WHEN hr.avg_hr BETWEEN 81 AND 100 THEN 'elevated'
                ELSE 'tachycardia'
            END
        ), 0), 
        4
    ) as confidence_given_hr,

    -- 提升度
    ROUND(
        COUNT(*) / NULLIF(
            (SUM(COUNT(*)) OVER (PARTITION BY 
                CASE 
                    WHEN hr.avg_hr < 60 THEN 'bradycardia'
                    WHEN hr.avg_hr BETWEEN 60 AND 70 THEN 'low_normal'
                    WHEN hr.avg_hr BETWEEN 71 AND 80 THEN 'normal'
                    WHEN hr.avg_hr BETWEEN 81 AND 100 THEN 'elevated'
                    ELSE 'tachycardia'
                END
            )) *
            (SUM(COUNT(*)) OVER (PARTITION BY 
                CASE 
                    WHEN slp.avg_sleep_quality >= 85 THEN 'excellent_sleep'
                    WHEN slp.avg_sleep_quality >= 70 THEN 'good_sleep'
                    WHEN slp.avg_sleep_quality >= 55 THEN 'fair_sleep'
                    ELSE 'poor_sleep'
                END
            )) /
            NULLIF((SELECT COUNT(*) FROM dws_user_daily_health_summary WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)), 0),
            0
        ), 
        2
    ) as lift_value

FROM dws_user_daily_health_summary dws
JOIN (
    SELECT user_id, AVG(avg_heart_rate) as avg_hr
    FROM dws_user_daily_health_summary
    WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)
    GROUP BY user_id
) hr ON dws.user_id = hr.user_id
JOIN (
    SELECT user_id, AVG(avg_sleep_quality_score) as avg_sleep_quality
    FROM dws_user_daily_health_summary
    WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)
    GROUP BY user_id
) slp ON dws.user_id = slp.user_id
WHERE dt >= SUBSTRING(DATE_SUB(CURRENT_DATE(), 30), 1, 6)
GROUP BY 
    CASE 
        WHEN hr.avg_hr < 60 THEN 'bradycardia'
        WHEN hr.avg_hr BETWEEN 60 AND 70 THEN 'low_normal'
        WHEN hr.avg_hr BETWEEN 71 AND 80 THEN 'normal'
        WHEN hr.avg_hr BETWEEN 81 AND 100 THEN 'elevated'
        ELSE 'tachycardia'
    END,
    CASE 
        WHEN slp.avg_sleep_quality >= 85 THEN 'excellent_sleep'
        WHEN slp.avg_sleep_quality >= 70 THEN 'good_sleep'
        WHEN slp.avg_sleep_quality >= 55 THEN 'fair_sleep'
        ELSE 'poor_sleep'
    END
HAVING co_occurrence_count >= 5  -- 最小支持度阈值
ORDER BY lift_value DESC;