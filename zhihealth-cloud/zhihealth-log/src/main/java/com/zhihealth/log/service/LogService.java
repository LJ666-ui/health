package com.zhihealth.log.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhihealth.common.util.PageQuery;
import com.zhihealth.log.entity.OperationLog;
import com.zhihealth.log.mapper.OperationLogMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class LogService {

    private final OperationLogMapper operationLogMapper;
    private final StringRedisTemplate redisTemplate;

    public Page<OperationLog> getLogList(PageQuery pageQuery,
                                         String actionType,
                                         String operator,
                                         String module,
                                         String result,
                                         String startTime,
                                         String endTime) {
        Page<OperationLog> page = new Page<>(pageQuery.getPageNum(), pageQuery.getPageSize());

        LambdaQueryWrapper<OperationLog> wrapper = new LambdaQueryWrapper<>();

        if (actionType != null && !actionType.isEmpty()) {
            wrapper.eq(OperationLog::getActionType, actionType);
        }

        if (operator != null && !operator.isEmpty()) {
            wrapper.like(OperationLog::getOperator, operator);
        }

        if (module != null && !module.isEmpty()) {
            wrapper.eq(OperationLog::getModule, module);
        }

        if (result != null && !result.isEmpty()) {
            wrapper.eq(OperationLog::getResult, result);
        }

        if (startTime != null && !startTime.isEmpty()) {
            wrapper.ge(OperationLog::getOperateTime, startTime);
        }

        if (endTime != null && !endTime.isEmpty()) {
            wrapper.le(OperationLog::getOperateTime, endTime + " 23:59:59");
        }

        wrapper.orderByDesc(OperationLog::getOperateTime);

        return operationLogMapper.selectPage(page, wrapper);
    }

    public OperationLog getLogDetail(Long id) {
        return operationLogMapper.selectById(id);
    }

    @Async
    public void saveLogAsync(OperationLog operationLog) {
        try {
            operationLogMapper.insert(operationLog);
            
            incrementDailyCount();
            
        } catch (Exception e) {
            log.error("保存操作日志失败", e);
        }
    }

    public boolean deleteLogs(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return false;
        }
        
        int rows = operationLogMapper.deleteBatchIds(ids);
        return rows > 0;
    }

    public long clearLogsBeforeDate(LocalDate beforeDate) {
        LambdaQueryWrapper<OperationLog> wrapper = new LambdaQueryWrapper<>();
        wrapper.lt(OperationLog::getOperateTime, beforeDate.atStartOfDay());
        
        return operationLogMapper.delete(wrapper);
    }

    public Map<String, Object> getLogStatistics() {
        Map<String, Object> stats = new java.util.HashMap<>();
        
        LocalDateTime today = LocalDate.now().atStartOfDay();
        
        long totalCount = operationLogMapper.selectCount(new LambdaQueryWrapper<>());
        
        long todayCount = operationLogMapper.selectCount(
            new LambdaQueryWrapper<OperationLog>()
                .ge(OperationLog::getOperateTime, today)
        );
        
        long successCount = operationLogMapper.selectCount(
            new LambdaQueryWrapper<OperationLog>()
                .eq(OperationLog::getResult, "success")
        );
        
        long failedCount = operationLogMapper.selectCount(
            new LambdaQueryWrapper<OperationLog>()
                .eq(OperationLog::getResult, "failed")
        );
        
        stats.put("totalCount", totalCount);
        stats.put("todayCount", todayCount);
        stats.put("successCount", successCount);
        stats.put("failedCount", failedCount);
        stats.put("successRate", totalCount > 0 ? String.format("%.2f%%", (double) successCount / totalCount * 100) : "0%");
        
        List<Map<String, Object>> moduleStats = getModuleStatistics();
        stats.put("moduleStats", moduleStats);
        
        List<Map<String, Object>> actionTypeStats = getActionTypeStatistics();
        stats.put("actionTypeStats", actionTypeStats);
        
        return stats;
    }

    public List<Map<String, Object>> getRecentLogs(int limit) {
        LambdaQueryWrapper<OperationLog> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByDesc(OperationLog::getOperateTime);
        wrapper.last("LIMIT " + limit);
        
        List<OperationLog> logs = operationLogMapper.selectList(wrapper);
        
        return logs.stream().map(log -> {
            Map<String, Object> map = new java.util.HashMap<>();
            map.put("id", log.getId());
            map.put("operator", log.getOperator());
            map.put("module", log.getModule());
            map.put("actionType", log.getActionType());
            map.put("description", log.getDescription());
            map.put("result", log.getResult());
            map.put("operateTime", log.getOperateTime());
            return map;
        }).collect(java.util.stream.Collectors.toList());
    }

    public byte[] exportLogs(String actionType,
                              String operator,
                              String module,
                              String result,
                              String startTime,
                              String endTime) {
        PageQuery pageQuery = new PageQuery();
        pageQuery.setPageNum(1);
        pageQuery.setPageSize(10000);
        
        Page<OperationLog> page = getLogList(pageQuery, actionType, operator, module, result, startTime, endTime);
        
        StringBuilder csv = new StringBuilder();
        csv.append("序号,操作人,操作模块,操作类型,操作描述,IP地址,执行结果,耗时(ms),操作时间\n");
        
        int index = 1;
        for (OperationLog log : page.getRecords()) {
            csv.append(index++)
                .append(",")
                .append(escapeCsv(log.getOperator()))
                .append(",")
                .append(log.getModule())
                .append(",")
                .append(log.getActionType())
                .append(",")
                .append(escapeCsv(log.getDescription()))
                .append(",")
                .append(log.getIpAddress())
                .append(",")
                .append(log.getResult())
                .append(",")
                .append(log.getDuration())
                .append(",")
                .append(log.getOperateTime())
                .append("\n");
        }
        
        return csv.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    private void incrementDailyCount() {
        String key = "log:daily:" + LocalDate.now().toString();
        redisTemplate.opsForValue().increment(key);
        redisTemplate.expire(key, 30, TimeUnit.DAYS);
    }

    private List<Map<String, Object>> getModuleStatistics() {
        String[] modules = {"user", "device", "collect", "storage", "alert", "ai", "settings", "report"};
        List<Map<String, Object>> stats = new java.util.ArrayList<>();
        
        for (String module : modules) {
            long count = operationLogMapper.selectCount(
                new LambdaQueryWrapper<OperationLog>().eq(OperationLog::getModule, module)
            );
            
            Map<String, Object> item = new java.util.HashMap<>();
            item.put("module", module);
            item.put("count", count);
            stats.add(item);
        }
        
        return stats;
    }

    private List<Map<String, Object>> getActionTypeStatistics() {
        String[] types = {"auth", "data", "config", "alert", "ai", "file", "other"};
        List<Map<String, Object>> stats = new java.util.ArrayList<>();
        
        for (String type : types) {
            long count = operationLogMapper.selectCount(
                new LambdaQueryWrapper<OperationLog>().eq(OperationLog::getActionType, type)
            );
            
            Map<String, Object> item = new java.util.HashMap<>();
            item.put("actionType", type);
            item.put("count", count);
            stats.add(item);
        }
        
        return stats;
    }

    private String escapeCsv(String value) {
        if (value == null) {
            return "";
        }
        
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            value = value.replace("\"", "\"\"");
            return "\"" + value + "\"";
        }
        
        return value;
    }
}
