package com.zhihealth.cache.controller;

import com.zhihealth.common.result.Result;
import com.zhihealth.cache.service.CacheService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/cache")
@RequiredArgsConstructor
public class CacheController {
    
    private final CacheService cacheService;
    
    @GetMapping("/latest/{userId}")
    public Result<Map<String, Object>> getLatestHealthData(@PathVariable Long userId) {
        Map<String, Object> data = cacheService.getLatestHealthData(userId);
        return Result.success(data);
    }
    
    @GetMapping("/history/{userId}/{deviceId}")
    public Result<List<String>> getHealthHistory(@PathVariable Long userId,
                                                  @PathVariable Long deviceId,
                                                  @RequestParam(defaultValue = "50") int limit) {
        List<String> history = cacheService.getHealthHistory(userId, deviceId, limit);
        return Result.success(history);
    }
    
    @DeleteMapping("/invalidate")
    public Result<Boolean> invalidateCache(@RequestParam String pattern) {
        boolean result = cacheService.invalidateCache(pattern);
        return Result.success(result);
    }
    
    @GetMapping("/statistics")
    public Result<Map<String, Object>> getCacheStatistics() {
        Map<String, Object> stats = cacheService.getCacheStatistics();
        return Result.success(stats);
    }
}
