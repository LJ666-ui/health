package com.zhihealth.cache.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class CacheService {
    
    private final StringRedisTemplate redisTemplate;
    
    public Map<String, Object> getLatestHealthData(Long userId) {
        String pattern = "health:latest:" + userId + ":*";
        Set<String> keys = redisTemplate.keys(pattern);
        
        Map<String, Object> result = new HashMap<>();
        if (keys != null && !keys.isEmpty()) {
            for (String key : keys) {
                Map<Object, Object> data = redisTemplate.opsForHash().entries(key);
                if (!data.isEmpty()) {
                    String deviceType = key.split(":")[3];
                    result.put(deviceType, data);
                }
            }
        }
        
        return result;
    }
    
    public List<String> getHealthHistory(Long userId, Long deviceId, int limit) {
        String key = "health:history:" + userId + ":" + deviceId;
        return redisTemplate.opsForList().range(key, 0, limit - 1);
    }
    
    public void cacheHotData(String key, Object value) {
        String json = value instanceof String ? (String) value : com.alibaba.fastjson2.JSON.toJSONString(value);
        redisTemplate.opsForValue().set(key, json, 1, TimeUnit.HOURS);
        log.debug("Cached hot data with key: {}", key);
    }
    
    public void cacheWarmData(String key, Object value) {
        String json = value instanceof String ? (String) value : com.alibaba.fastjson2.JSON.toJSONString(value);
        redisTemplate.opsForValue().set(key, json, 2, TimeUnit.HOURS);
        log.debug("Cached warm data with key: {}", key);
    }
    
    public void cacheColdData(String key, Object value) {
        String json = value instanceof String ? (String) value : com.alibaba.fastjson2.JSON.toJSONString(value);
        redisTemplate.opsForValue().set(key, json, 24, TimeUnit.HOURS);
        log.debug("Cached cold data with key: {}", key);
    }
    
    public Object getCachedData(String key) {
        String value = redisTemplate.opsForValue().get(key);
        if (value != null) {
            try {
                return com.alibaba.fastjson2.JSON.parse(value);
            } catch (Exception e) {
                return value;
            }
        }
        return null;
    }
    
    public boolean invalidateCache(String pattern) {
        Set<String> keys = redisTemplate.keys(pattern);
        if (keys != null && !keys.isEmpty()) {
            Long deleted = redisTemplate.delete(keys);
            log.info("Invalidated {} cache keys matching pattern: {}", deleted, pattern);
            return true;
        }
        return false;
    }
    
    public Map<String, Object> getCacheStatistics() {
        Map<String, Object> stats = new HashMap<>();
        
        long totalKeys = 0;
        long hotDataCount = 0;
        long warmDataCount = 0;
        
        Set<String> allKeys = redisTemplate.keys("*");
        if (allKeys != null) {
            totalKeys = allKeys.size();
            
            for (String key : allKeys) {
                Long ttl = redisTemplate.getExpire(key, TimeUnit.SECONDS);
                if (ttl != null && ttl > 0) {
                    if (ttl <= 3600) {
                        hotDataCount++;
                    } else if (ttl <= 7200) {
                        warmDataCount++;
                    }
                }
            }
        }
        
        stats.put("totalCacheKeys", totalKeys);
        stats.put("hotDataCount", hotDataCount);
        stats.put("warmDataCount", warmDataCount);
        stats.put("coldDataCount", totalKeys - hotDataCount - warmDataCount);
        stats.put("cacheHitRate", "N/A");
        
        return stats;
    }
}
