package com.zhihealth.collect.service;

import com.alibaba.fastjson2.JSON;
import com.zhihealth.common.exception.BusinessException;
import com.zhihealth.collect.dto.HealthDataDTO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class HealthDataCollectService {
    
    private final StringRedisTemplate redisTemplate;
    
    @Value("${collect.validation.heart-rate.min:30}")
    private int heartRateMin;
    
    @Value("${collect.validation.heart-rate.max:220}")
    private int heartRateMax;
    
    @Value("${collect.validation.body-temp.min:35.0}")
    private double bodyTempMin;
    
    @Value("${collect.validation.body-temp.max:42.0}")
    private double bodyTempMax;
    
    public Map<String, Object> collectSingle(HealthDataDTO data) {
        validateData(data);
        checkDuplicate(data);
        
        Map<String, Object> healthRecord = buildHealthRecord(data);
        
        cacheToRedis(data, healthRecord);
        
        log.info("Health data collected successfully for device: {}, user: {}", 
                data.getDeviceId(), data.getUserId());
        
        Map<String, Object> result = new HashMap<>();
        result.put("status", "success");
        result.put("deviceId", data.getDeviceId());
        result.put("timestamp", data.getTimestamp());
        return result;
    }
    
    public Map<String, Object> collectBatch(List<HealthDataDTO> dataList) {
        if (dataList.size() > 100) {
            throw new BusinessException("Batch size cannot exceed 100 records");
        }
        
        int successCount = 0;
        int failCount = 0;
        
        for (HealthDataDTO data : dataList) {
            try {
                collectSingle(data);
                successCount++;
            } catch (Exception e) {
                log.error("Failed to process record for device {}: {}", data.getDeviceId(), e.getMessage());
                failCount++;
            }
        }
        
        Map<String, Object> result = new HashMap<>();
        result.put("totalRecords", dataList.size());
        result.put("successCount", successCount);
        result.put("failCount", failCount);
        return result;
    }
    
    private void validateData(HealthDataDTO data) {
        if (data.getHeartRate() != null) {
            int hr = data.getHeartRate().intValue();
            if (hr < heartRateMin || hr > heartRateMax) {
                throw new BusinessException("Heart rate must be between " + heartRateMin + " and " + heartRateMax);
            }
        }
        
        if (data.getBodyTemp() != null) {
            double temp = data.getBodyTemp().doubleValue();
            if (temp < bodyTempMin || temp > bodyTempMax) {
                throw new BusinessException("Body temperature must be between " + bodyTempMin + " and " + bodyTempMax);
            }
        }
        
        if (data.getBloodPressureSystolic() != null) {
            if (data.getBloodPressureSystolic() < 60 || data.getBloodPressureSystolic() > 200) {
                throw new BusinessException("Systolic blood pressure must be between 60 and 200");
            }
        }
        
        if (data.getBloodPressureDiastolic() != null) {
            if (data.getBloodPressureDiastolic() < 40 || data.getBloodPressureDiastolic() > 130) {
                throw new BusinessException("Diastolic blood pressure must be between 40 and 130");
            }
        }
    }
    
    private void checkDuplicate(HealthDataDTO data) {
        String key = "collect:duplicate:" + data.getDeviceId() + ":" + data.getTimestamp();
        Boolean exists = redisTemplate.hasKey(key);
        if (Boolean.TRUE.equals(exists)) {
            throw new BusinessException("Duplicate data detected for this device and timestamp");
        }
        redisTemplate.opsForValue().set(key, "1", 24, java.util.concurrent.TimeUnit.HOURS);
    }
    
    private Map<String, Object> buildHealthRecord(HealthDataDTO data) {
        Map<String, Object> record = new HashMap<>();
        record.put("deviceId", data.getDeviceId());
        record.put("userId", data.getUserId());
        record.put("dataType", data.getDataType());
        record.put("timestamp", data.getTimestamp());
        record.put("collectedAt", LocalDateTime.now().toString());
        
        if (data.getHeartRate() != null) {
            record.put("heartRate", data.getHeartRate());
        }
        if (data.getBodyTemp() != null) {
            record.put("bodyTemp", data.getBodyTemp());
        }
        if (data.getBloodPressureSystolic() != null && data.getBloodPressureDiastolic() != null) {
            record.put("bloodPressureSystolic", data.getBloodPressureSystolic());
            record.put("bloodPressureDiastolic", data.getBloodPressureDiastolic());
        }
        if (data.getSteps() != null) {
            record.put("steps", data.getSteps());
        }
        if (data.getSleepHours() != null) {
            record.put("sleepHours", data.getSleepHours());
        }
        
        return record;
    }
    
    private void cacheToRedis(HealthDataDTO data, Map<String, Object> record) {
        String latestKey = "health:latest:" + data.getUserId() + ":" + data.getDeviceId();
        String historyKey = "health:history:" + data.getUserId() + ":" + data.getDeviceId();
        
        redisTemplate.opsForHash().putAll(latestKey, convertToStringMap(record));
        redisTemplate.expire(latestKey, 7, java.util.concurrent.TimeUnit.DAYS);
        
        redisTemplate.opsForList().leftPush(historyKey, JSON.toJSONString(record));
        redisTemplate.opsForList().trim(historyKey, 0, 999);
        redisTemplate.expire(historyKey, 30, java.util.concurrent.TimeUnit.DAYS);
    }
    
    private Map<String, String> convertToStringMap(Map<String, Object> map) {
        Map<String, String> stringMap = new HashMap<>();
        map.forEach((k, v) -> stringMap.put(k, v != null ? v.toString() : ""));
        return stringMap;
    }
}
