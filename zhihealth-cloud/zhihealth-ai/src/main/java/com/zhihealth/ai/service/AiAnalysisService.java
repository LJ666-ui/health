package com.zhihealth.ai.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zhihealth.ai.config.PythonAiServiceConfig;
import com.zhihealth.ai.entity.AiAnalysisRecord;
import com.zhihealth.ai.mapper.AiAnalysisRecordMapper;
import lombok.extern.slf4j.Slf4j;
import okhttp3.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class AiAnalysisService extends ServiceImpl<AiAnalysisRecordMapper, AiAnalysisRecord> {

    @Autowired
    private PythonAiServiceConfig pythonAiServiceConfig;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private final OkHttpClient httpClient = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();

    private static final String AI_CACHE_PREFIX = "ai:analysis:";
    private static final int CACHE_EXPIRE_HOURS = 24;

    public Page<AiAnalysisRecord> getRecordsByPage(int pageNum, int pageSize, Long userId, String analysisType) {
        Page<AiAnalysisRecord> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<AiAnalysisRecord> wrapper = new LambdaQueryWrapper<>();
        
        if (userId != null) {
            wrapper.eq(AiAnalysisRecord::getUserId, userId);
        }
        if (analysisType != null && !analysisType.isEmpty()) {
            wrapper.eq(AiAnalysisRecord::getAnalysisType, analysisType);
        }
        
        wrapper.orderByDesc(AiAnalysisRecord::getAnalysisTime);
        return this.page(page, wrapper);
    }

    public Map<String, Object> callPythonAiService(String endpoint, Map<String, Object> params) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            String url = pythonAiServiceConfig.getUrl() + endpoint;
            
            String jsonBody = JSON.toJSONString(params);
            RequestBody body = RequestBody.create(
                    jsonBody,
                    MediaType.parse("application/json; charset=utf-8")
            );

            Request request = new Request.Builder()
                    .url(url)
                    .post(body)
                    .build();

            log.info("调用Python AI服务: {}", url);

            try (Response response = httpClient.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    String responseBody = response.body().string();
                    result = JSON.parseObject(responseBody, Map.class);
                    result.put("success", true);
                    log.info("Python AI服务响应成功");
                } else {
                    result.put("success", false);
                    result.put("error", "HTTP请求失败: " + response.code());
                    log.error("Python AI服务HTTP错误: {}", response.code());
                }
            }
            
        } catch (IOException e) {
            result.put("success", false);
            result.put("error", "调用Python AI服务异常: " + e.getMessage());
            log.error("调用Python AI服务异常", e);
        }

        return result;
    }

    public Map<String, Object> analyzeHealthData(Long userId, Map<String, Object> healthData) {
        Map<String, Object> result = new HashMap<>();
        long startTime = System.currentTimeMillis();
        
        try {
            String cacheKey = generateCacheKey(userId, healthData);
            Map<String, Object> cachedResult = getCachedResult(cacheKey);
            
            if (cachedResult != null) {
                log.info("命中AI分析缓存");
                cachedResult.put("fromCache", true);
                return cachedResult;
            }
            
            Map<String, Object> params = new HashMap<>();
            params.put("userId", userId);
            params.put("data", healthData);
            params.put("mode", "analyze");

            result = callPythonAiService("/api/ai/analyze", params);
            
            long executionTime = System.currentTimeMillis() - startTime;
            
            if ((Boolean) result.getOrDefault("success", false)) {
                saveAnalysisRecord(userId, "health_data_analysis", 
                                 JSON.toJSONString(healthData),
                                 JSON.toJSONString(result),
                                 "python_ml_pipeline",
                                 null,
                                 1,
                                 null,
                                 LocalDateTime.now(),
                                 executionTime);
                
                cacheResult(cacheKey, result);
                
                result.put("executionTimeMs", executionTime);
                result.put("fromCache", false);
            }
            
        } catch (Exception e) {
            result.put("success", false);
            result.put("error", "健康数据分析异常: " + e.getMessage());
            log.error("健康数据分析异常", e);
        }

        return result;
    }

    public Map<String, Object> predictHealthTrend(Long userId, List<Map<String, Object>> timeSeriesData, int days) {
        Map<String, Object> result = new HashMap<>();
        long startTime = System.currentTimeMillis();
        
        try {
            Map<String, Object> params = new HashMap<>();
            params.put("userId", userId);
            params.put("timeSeriesData", timeSeriesData);
            params.put("forecastDays", days);

            result = callPythonAiService("/api/ai/predict", params);
            
            long executionTime = System.currentTimeMillis() - startTime;
            
            if ((Boolean) result.getOrDefault("success", false)) {
                saveAnalysisRecord(userId, "trend_prediction",
                                 JSON.toJSONString(timeSeriesData),
                                 JSON.toJSONString(result),
                                 "prophet_lstm_arima",
                                 null,
                                 1,
                                 null,
                                 LocalDateTime.now(),
                                 executionTime);
                
                result.put("executionTimeMs", executionTime);
            }
            
        } catch (Exception e) {
            result.put("success", false);
            result.put("error", "健康趋势预测异常: " + e.getMessage());
            log.error("健康趋势预测异常", e);
        }

        return result;
    }

    public Map<String, Object> detectAnomalies(Long userId, Map<String, Object> healthData) {
        Map<String, Object> result = new HashMap<>();
        long startTime = System.currentTimeMillis();
        
        try {
            Map<String, Object> params = new HashMap<>();
            params.put("userId", userId);
            params.put("data", healthData);

            result = callPythonAiService("/api/ai/detect-anomalies", params);
            
            long executionTime = System.currentTimeMillis() - startTime;
            
            if ((Boolean) result.getOrDefault("success", false)) {
                saveAnalysisRecord(userId, "anomaly_detection",
                                 JSON.toJSONString(healthData),
                                 JSON.toJSONString(result),
                                 "isolation_forest_random_forest",
                                 null,
                                 1,
                                 null,
                                 LocalDateTime.now(),
                                 executionTime);
                
                result.put("executionTimeMs", executionTime);
            }
            
        } catch (Exception e) {
            result.put("success", false);
            result.put("error", "异常检测异常: " + e.getMessage());
            log.error("异常检测异常", e);
        }

        return result;
    }

    public Map<String, Object> generateHealthReport(Long userId, List<Map<String, Object>> healthDataList) {
        Map<String, Object> result = new HashMap<>();
        long startTime = System.currentTimeMillis();
        
        try {
            Map<String, Object> params = new HashMap<>();
            params.put("userId", userId);
            params.put("healthDataList", healthDataList);

            result = callPythonAiService("/api/ai/generate-report", params);
            
            long executionTime = System.currentTimeMillis() - startTime;
            
            if ((Boolean) result.getOrDefault("success", false)) {
                saveAnalysisRecord(userId, "health_report_generation",
                                 JSON.toJSONString(healthDataList),
                                 JSON.toJSONString(result),
                                 "llm_prompt_engineering",
                                 null,
                                 1,
                                 null,
                                 LocalDateTime.now(),
                                 executionTime);
                
                result.put("executionTimeMs", executionTime);
            }
            
        } catch (Exception e) {
            result.put("success", false);
            result.put("error", "健康报告生成异常: " + e.getMessage());
            log.error("健康报告生成异常", e);
        }

        return result;
    }

    private String generateCacheKey(Long userId, Map<String, Object> data) {
        String dataHash = String.valueOf(data.hashCode());
        return AI_CACHE_PREFIX + userId + ":" + dataHash;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> getCachedResult(String cacheKey) {
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof Map) {
            return (Map<String, Object>) cached;
        }
        return null;
    }

    private void cacheResult(String cacheKey, Map<String, Object> result) {
        redisTemplate.opsForValue().set(cacheKey, result, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);
    }

    private void saveAnalysisRecord(Long userId, String analysisType, String inputData,
                                   String resultData, String modelUsed, Double confidenceScore,
                                   Integer status, String errorMessage,
                                   LocalDateTime analysisTime, Long executionTimeMs) {
        try {
            AiAnalysisRecord record = new AiAnalysisRecord();
            record.setUserId(userId);
            record.setAnalysisType(analysisType);
            record.setInputData(inputData);
            record.setResultData(resultData);
            record.setModelUsed(modelUsed);
            record.setConfidenceScore(confidenceScore);
            record.setStatus(status);
            record.setErrorMessage(errorMessage);
            record.setAnalysisTime(analysisTime);
            record.setExecutionTimeMs(executionTimeMs);
            
            this.save(record);
            
        } catch (Exception e) {
            log.error("保存AI分析记录失败", e);
        }
    }

    public List<AiAnalysisRecord> getRecentAnalyses(Long userId, int limit) {
        LambdaQueryWrapper<AiAnalysisRecord> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AiAnalysisRecord::getUserId, userId)
               .eq(AiAnalysisRecord::getStatus, 1)
               .orderByDesc(AiAnalysisRecord::getAnalysisTime)
               .last("LIMIT " + limit);
        
        return this.list(wrapper);
    }

    public Map<String, Object> getAiStatistics(Long userId) {
        Map<String, Object> stats = new HashMap<>();
        
        LambdaQueryWrapper<AiAnalysisRecord> wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(AiAnalysisRecord::getUserId, userId);
        }
        
        long totalCount = this.count(wrapper);
        stats.put("totalCount", totalCount);
        
        wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(AiAnalysisRecord::getUserId, userId);
        }
        wrapper.eq(AiAnalysisRecord::getStatus, 1);
        long successCount = this.count(wrapper);
        stats.put("successCount", successCount);
        
        wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(AiAnalysisRecord::getUserId, userId);
        }
        wrapper.eq(AiAnalysisRecord::getStatus, 0);
        long failCount = this.count(wrapper);
        stats.put("failCount", failCount);
        
        return stats;
    }
}
