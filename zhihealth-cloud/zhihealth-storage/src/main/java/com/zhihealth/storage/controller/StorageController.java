package com.zhihealth.storage.controller;

import com.zhihealth.common.result.Result;
import com.zhihealth.storage.entity.HealthRecord;
import com.zhihealth.storage.service.FourDatabaseStorageService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/storage")
@RequiredArgsConstructor
public class StorageController {
    
    private final FourDatabaseStorageService fourDatabaseStorageService;
    
    @PostMapping("/store")
    public Result<Map<String, Object>> storeData(@RequestBody HealthRecord record) {
        Map<String, Object> results = fourDatabaseStorageService.storeToAllDatabases(record);
        return Result.success(results);
    }
    
    @PostMapping("/batch-store")
    public Result<Map<String, Object>> batchStore(@RequestBody List<HealthRecord> records) {
        if (records.size() > 50) {
            throw new RuntimeException("Batch size cannot exceed 50 records");
        }
        
        Map<String, Object> summary = new java.util.HashMap<>();
        int totalSuccess = 0;
        int totalFail = 0;
        
        for (HealthRecord record : records) {
            try {
                Map<String, Object> result = fourDatabaseStorageService.storeToAllDatabases(record);
                long successCount = result.values().stream()
                        .filter(v -> Boolean.TRUE.equals(v))
                        .count();
                if (successCount >= 2) {
                    totalSuccess++;
                } else {
                    totalFail++;
                }
            } catch (Exception e) {
                totalFail++;
            }
        }
        
        summary.put("totalRecords", records.size());
        summary.put("success", totalSuccess);
        summary.put("failed", totalFail);
        
        return Result.success(summary);
    }
}
