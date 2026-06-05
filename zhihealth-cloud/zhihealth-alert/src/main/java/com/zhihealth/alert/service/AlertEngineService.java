package com.zhihealth.alert.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zhihealth.alert.entity.AlertRecord;
import com.zhihealth.alert.entity.AlertRule;
import com.zhihealth.alert.mapper.AlertRecordMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class AlertEngineService extends ServiceImpl<AlertRecordMapper, AlertRecord> {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private AlertRuleService alertRuleService;

    private static final String ALERT_COOLDOWN_PREFIX = "alert:cooldown:";
    private static final String ALERT_COUNTER_PREFIX = "alert:counter:";
    private static final int DEFAULT_COOLDOWN_SECONDS = 300;

    public Page<AlertRecord> getRecordsByPage(int pageNum, int pageSize, Integer status, Long userId) {
        Page<AlertRecord> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<AlertRecord> wrapper = new LambdaQueryWrapper<>();
        
        if (status != null) {
            wrapper.eq(AlertRecord::getStatus, status);
        }
        if (userId != null) {
            wrapper.eq(AlertRecord::getUserId, userId);
        }
        
        wrapper.orderByDesc(AlertRecord::getAlertTime);
        return this.page(page, wrapper);
    }

    public Map<String, Object> evaluateData(Map<String, Object> healthData) {
        Map<String, Object> result = new HashMap<>();
        result.put("evaluated", false);
        result.put("alerts", new ArrayList<>());

        try {
            String dataType = (String) healthData.get("dataType");
            if (dataType == null || dataType.isEmpty()) {
                log.warn("数据类型为空，跳过预警评估");
                return result;
            }

            List<AlertRule> rules = alertRuleService.getRulesByDataType(dataType);
            if (rules == null || rules.isEmpty()) {
                log.debug("数据类型{}没有配置预警规则", dataType);
                return result;
            }

            List<Map<String, Object>> triggeredAlerts = new ArrayList<>();
            
            for (AlertRule rule : rules) {
                boolean triggered = evaluateRule(rule, healthData);
                if (triggered) {
                    Map<String, Object> alertInfo = createAlertRecord(rule, healthData);
                    triggeredAlerts.add(alertInfo);
                    
                    saveAlertAsync(rule, healthData, alertInfo);
                }
            }

            result.put("evaluated", true);
            result.put("alerts", triggeredAlerts);
            result.put("totalRules", rules.size());
            result.put("triggeredCount", triggeredAlerts.size());
            
        } catch (Exception e) {
            log.error("预警评估异常", e);
            result.put("error", e.getMessage());
        }

        return result;
    }

    private boolean evaluateRule(AlertRule rule, Map<String, Object> data) {
        if (!rule.getEnabled()) {
            return false;
        }

        Object valueObj = data.get(rule.getMetric());
        if (valueObj == null) {
            return false;
        }

        double currentValue;
        if (valueObj instanceof Number) {
            currentValue = ((Number) valueObj).doubleValue();
        } else {
            try {
                currentValue = Double.parseDouble(valueObj.toString());
            } catch (NumberFormatException e) {
                log.warn("无法解析数值: {}", valueObj);
                return false;
            }
        }

        double threshold = rule.getThreshold();
        String condition = rule.getCondition();

        boolean triggered = false;
        
        switch (condition) {
            case "gt":
                triggered = currentValue > threshold;
                break;
            case "gte":
                triggered = currentValue >= threshold;
                break;
            case "lt":
                triggered = currentValue < threshold;
                break;
            case "lte":
                triggered = currentValue <= threshold;
                break;
            case "eq":
                triggered = Math.abs(currentValue - threshold) < 0.001;
                break;
            case "neq":
                triggered = Math.abs(currentValue - threshold) >= 0.001;
                break;
            default:
                triggered = false;
        }

        if (triggered && isCooldownActive(rule.getId())) {
            log.debug("规则{}处于冷却期，跳过预警", rule.getRuleName());
            return false;
        }

        return triggered;
    }

    private boolean isCooldownActive(Long ruleId) {
        String key = ALERT_COOLDOWN_PREFIX + ruleId;
        Boolean exists = redisTemplate.hasKey(key);
        return Boolean.TRUE.equals(exists);
    }

    private void setCooldown(Long ruleId) {
        String key = ALERT_COOLDOWN_PREFIX + ruleId;
        redisTemplate.opsForValue().set(key, "1", DEFAULT_COOLDOWN_SECONDS, TimeUnit.SECONDS);
    }

    private Map<String, Object> createAlertRecord(AlertRule rule, Map<String, Object> data) {
        Map<String, Object> alertInfo = new HashMap<>();
        
        Object valueObj = data.get(rule.getMetric());
        double currentValue = valueObj instanceof Number ? ((Number) valueObj).doubleValue() : 0;
        
        alertInfo.put("ruleId", rule.getId());
        alertInfo.put("ruleName", rule.getRuleName());
        alertInfo.put("dataType", rule.getDataType());
        alertInfo.put("metric", rule.getMetric());
        alertInfo.put("currentValue", currentValue);
        alertInfo.put("threshold", rule.getThreshold());
        alertInfo.put("condition", rule.getCondition());
        alertInfo.put("level", rule.getLevel());
        alertInfo.put("unit", rule.getUnit());
        alertInfo.put("message", generateAlertMessage(rule, currentValue));
        alertInfo.put("timestamp", LocalDateTime.now().toString());
        
        return alertInfo;
    }

    private String generateAlertMessage(AlertRule rule, double currentValue) {
        String conditionText = "";
        
        switch (rule.getCondition()) {
            case "gt":
                conditionText = "大于";
                break;
            case "gte":
                conditionText = "大于等于";
                break;
            case "lt":
                conditionText = "小于";
                break;
            case "lte":
                conditionText = "小于等于";
                break;
            case "eq":
                conditionText = "等于";
                break;
            case "neq":
                conditionText = "不等于";
                break;
            default:
                conditionText = "未知条件";
        }
        
        return String.format("[%s] %s当前值%.2f%s，已%s阈值%.2f%s",
                getLevelText(rule.getLevel()),
                rule.getMetric(),
                currentValue,
                rule.getUnit() != null ? rule.getUnit() : "",
                conditionText,
                rule.getThreshold(),
                rule.getUnit() != null ? rule.getUnit() : "");
    }

    private String getLevelText(Integer level) {
        String levelText = "";
        
        switch (level) {
            case 1:
                levelText = "🔴 严重";
                break;
            case 2:
                levelText = "🟠 警告";
                break;
            case 3:
                levelText = "🟡 提醒";
                break;
            default:
                levelText = "ℹ️ 信息";
        }
        
        return levelText;
    }

    @Async
    public void saveAlertAsync(AlertRule rule, Map<String, Object> data, Map<String, Object> alertInfo) {
        try {
            AlertRecord record = new AlertRecord();
            record.setRuleId(rule.getId());
            record.setRuleName(rule.getRuleName());
            
            Object userIdObj = data.get("userId");
            if (userIdObj != null) {
                record.setUserId(userIdObj instanceof Number ? ((Number) userIdObj).longValue() : Long.parseLong(userIdObj.toString()));
            }
            
            Object deviceIdObj = data.get("deviceId");
            if (deviceIdObj != null) {
                record.setDeviceId(deviceIdObj instanceof Number ? ((Number) deviceIdObj).longValue() : Long.parseLong(deviceIdObj.toString()));
            }
            
            record.setDataType(rule.getDataType());
            record.setMetric(rule.getMetric());
            record.setCurrentValue((Double) alertInfo.get("currentValue"));
            record.setThreshold(rule.getThreshold());
            record.setCondition(rule.getCondition());
            record.setLevel(rule.getLevel());
            record.setMessage((String) alertInfo.get("message"));
            record.setStatus(0);
            record.setAlertTime(LocalDateTime.now());
            
            this.save(record);
            
            setCooldown(rule.getId());
            
            incrementAlertCounter(rule.getId());
            
            publishAlertEvent(record);
            
            log.info("预警记录已保存: {}", JSON.toJSONString(record));
            
        } catch (Exception e) {
            log.error("保存预警记录失败", e);
        }
    }

    private void incrementAlertCounter(Long ruleId) {
        String key = ALERT_COUNTER_PREFIX + ruleId + ":" + 
                     java.time.LocalDate.now().toString();
        redisTemplate.opsForValue().increment(key);
        redisTemplate.expire(key, 7, TimeUnit.DAYS);
    }

    private void publishAlertEvent(AlertRecord record) {
        String channel = "alert:event";
        redisTemplate.convertAndSend(channel, JSON.toJSONString(record));
    }

    public Map<String, Object> getAlertStatistics(Long userId, String startDate, String endDate) {
        Map<String, Object> stats = new HashMap<>();
        
        LambdaQueryWrapper<AlertRecord> wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(AlertRecord::getUserId, userId);
        }
        
        long totalCount = this.count(wrapper);
        stats.put("totalCount", totalCount);
        
        wrapper.eq(AlertRecord::getStatus, 0);
        long activeCount = this.count(wrapper);
        stats.put("activeCount", activeCount);
        
        wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(AlertRecord::getUserId, userId);
        }
        wrapper.eq(AlertRecord::getStatus, 1);
        long resolvedCount = this.count(wrapper);
        stats.put("resolvedCount", resolvedCount);
        
        wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(AlertRecord::getUserId, userId);
        }
        wrapper.eq(AlertRecord::getLevel, 1);
        long criticalCount = this.count(wrapper);
        stats.put("criticalCount", criticalCount);
        
        return stats;
    }

    public boolean resolveAlert(Long recordId, String resolvedBy, String remark) {
        AlertRecord record = this.getById(recordId);
        if (record != null && record.getStatus() == 0) {
            record.setStatus(1);
            record.setResolveTime(LocalDateTime.now());
            record.setResolvedBy(resolvedBy);
            record.setRemark(remark);
            return this.updateById(record);
        }
        return false;
    }

    public List<AlertRecord> getActiveAlerts(Long userId) {
        LambdaQueryWrapper<AlertRecord> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AlertRecord::getStatus, 0)
               .eq(AlertRecord::getUserId, userId)
               .orderByAsc(AlertRecord::getLevel)
               .orderByDesc(AlertRecord::getAlertTime);

        return this.list(wrapper);
    }

    /**
     * 获取导出数据（支持条件筛选）
     */
    public List<AlertRecord> getExportRecords(Integer status, Long userId, String startDate, String endDate) {
        LambdaQueryWrapper<AlertRecord> wrapper = new LambdaQueryWrapper<>();

        if (status != null) {
            wrapper.eq(AlertRecord::getStatus, status);
        }
        if (userId != null) {
            wrapper.eq(AlertRecord::getUserId, userId);
        }
        if (startDate != null && !startDate.isEmpty()) {
            wrapper.ge(AlertRecord::getAlertTime, LocalDateTime.parse(startDate));
        }
        if (endDate != null && !endDate.isEmpty()) {
            wrapper.le(AlertRecord::getAlertTime, LocalDateTime.parse(endDate));
        }

        wrapper.orderByDesc(AlertRecord::getAlertTime);

        // 导出最多10000条记录
        Page<AlertRecord> page = new Page<>(1, 10000);
        return this.page(page, wrapper).getRecords();
    }

    /**
     * 定时巡检: 扫描最近数据并触发预警
     * 由 HealthScheduleTask 每5分钟调用
     *
     * @return 触发的预警数量
     */
    public int checkAndTriggerAlerts() {
        int triggeredCount = 0;
        try {
            // 获取所有启用的预警规则
            List<AlertRule> allRules = alertRuleService.list(
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<AlertRule>()
                            .eq(AlertRule::getEnabled, true)
            );

            // 遍历规则，评估最近5分钟的数据
            for (AlertRule rule : allRules) {
                if (isCooldownActive(rule.getId())) continue;

                // 构造模拟数据进行阈值比对（实际应从storage服务拉取）
                Map<String, Object> sampleData = new java.util.HashMap<>();
                sampleData.put("dataType", rule.getDataType());
                sampleData.put(rule.getMetric(), getLatestMetricValue(rule.getDataType(), rule.getMetric()));
                sampleData.put("userId", 1L);

                boolean triggered = evaluateRule(rule, sampleData);
                if (triggered) {
                    saveAlertAsync(rule, sampleData, createAlertRecord(rule, sampleData));
                    triggeredCount++;
                }
            }

            log.info("[巡检] 规则检查完成, 触发预警: {} 条", triggeredCount);
        } catch (Exception e) {
            log.error("[巡检] 异常", e);
        }
        return triggeredCount;
    }

    /**
     * 获取最新指标值（从Redis缓存或数据库查询）
     */
    private double getLatestMetricValue(String dataType, String metric) {
        String cacheKey = "health:latest:" + dataType + ":" + metric;
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof Number) {
            return ((Number) cached).doubleValue();
        }
        return 0.0; // 无数据时返回安全默认值
    }
}
