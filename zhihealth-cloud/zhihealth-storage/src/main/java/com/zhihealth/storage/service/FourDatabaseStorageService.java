package com.zhihealth.storage.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zhihealth.storage.entity.HealthRecord;
import com.zhihealth.storage.mapper.HealthRecordMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class FourDatabaseStorageService extends ServiceImpl<HealthRecordMapper, HealthRecord> {
    
    private final StringRedisTemplate redisTemplate;
    private final MongoTemplate mongoTemplate;
    
    public Map<String, Object> storeToAllDatabases(HealthRecord record) {
        Map<String, Object> results = new HashMap<>();
        
        try {
            storeToMySQL(record);
            results.put("mysql", true);
        } catch (Exception e) {
            log.error("MySQL storage failed: {}", e.getMessage());
            results.put("mysql", false);
        }
        
        try {
            storeToRedis(record);
            results.put("redis", true);
        } catch (Exception e) {
            log.error("Redis storage failed: {}", e.getMessage());
            results.put("redis", false);
        }
        
        try {
            storeToMongoDB(record);
            results.put("mongodb", true);
        } catch (Exception e) {
            log.error("MongoDB storage failed: {}", e.getMessage());
            results.put("mongodb", false);
        }
        
        log.info("Four-database storage completed for user {}, device {}", 
                record.getUserId(), record.getDeviceId());
        
        return results;
    }
    
    private void storeToMySQL(HealthRecord record) {
        this.save(record);
        log.debug("Stored to MySQL successfully");
    }
    
    private void storeToRedis(HealthRecord record) {
        String latestKey = "storage:latest:" + record.getUserId() + ":" + record.getDataType();
        String historyKey = "storage:history:" + record.getUserId() + ":" + record.getDeviceId();
        
        Map<String, String> data = new HashMap<>();
        data.put("id", String.valueOf(record.getId()));
        data.put("userId", String.valueOf(record.getUserId()));
        data.put("deviceId", String.valueOf(record.getDeviceId()));
        data.put("dataType", record.getDataType());
        if (record.getHeartRate() != null) data.put("heartRate", record.getHeartRate().toString());
        if (record.getBodyTemp() != null) data.put("bodyTemp", record.getBodyTemp().toString());
        if (record.getBloodPressureSystolic() != null) data.put("bloodPressureSystolic", String.valueOf(record.getBloodPressureSystolic()));
        if (record.getBloodPressureDiastolic() != null) data.put("bloodPressureDiastolic", String.valueOf(record.getBloodPressureDiastolic()));
        if (record.getSteps() != null) data.put("steps", String.valueOf(record.getSteps()));
        if (record.getSleepHours() != null) data.put("sleepHours", record.getSleepHours().toString());
        data.put("timestamp", String.valueOf(record.getTimestamp()));
        data.put("createdAt", Instant.now().toString());
        
        redisTemplate.opsForHash().putAll(latestKey, data);
        redisTemplate.expire(latestKey, 7, java.util.concurrent.TimeUnit.DAYS);
        
        redisTemplate.opsForList().leftPush(historyKey, data.toString());
        redisTemplate.opsForList().trim(historyKey, 0, 999);
        redisTemplate.expire(historyKey, 30, java.util.concurrent.TimeUnit.DAYS);
        
        log.debug("Stored to Redis successfully");
    }
    
    private void storeToMongoDB(HealthRecord record) {
        Map<String, Object> mongoDoc = new HashMap<>();
        mongoDoc.put("userId", record.getUserId());
        mongoDoc.put("deviceId", record.getDeviceId());
        mongoDoc.put("dataType", record.getDataType());
        if (record.getHeartRate() != null) mongoDoc.put("heartRate", record.getHeartRate());
        if (record.getBodyTemp() != null) mongoDoc.put("bodyTemp", record.getBodyTemp());
        if (record.getBloodPressureSystolic() != null) mongoDoc.put("bloodPressureSystolic", record.getBloodPressureSystolic());
        if (record.getBloodPressureDiastolic() != null) mongoDoc.put("bloodPressureDiastolic", record.getBloodPressureDiastolic());
        if (record.getSteps() != null) mongoDoc.put("steps", record.getSteps());
        if (record.getSleepHours() != null) mongoDoc.put("sleepHours", record.getSleepHours());
        mongoDoc.put("timestamp", record.getTimestamp());
        mongoDoc.put("storedAt", Instant.now());
        mongoDoc.put("source", "four_database_storage");
        
        mongoTemplate.insert(mongoDoc, "health_records");
        log.debug("Stored to MongoDB successfully");
    }
}
