package com.zhihealth.collect.controller;

import com.zhihealth.common.result.Result;
import com.zhihealth.collect.dto.HealthDataDTO;
import com.zhihealth.collect.service.HealthDataCollectService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/collect")
@RequiredArgsConstructor
public class HealthDataController {
    
    private final HealthDataCollectService healthDataCollectService;
    
    @PostMapping("/single")
    public Result<Map<String, Object>> collectSingle(@RequestBody HealthDataDTO data) {
        Map<String, Object> result = healthDataCollectService.collectSingle(data);
        return Result.success(result);
    }
    
    @PostMapping("/batch")
    public Result<Map<String, Object>> collectBatch(@RequestBody List<HealthDataDTO> dataList) {
        Map<String, Object> result = healthDataCollectService.collectBatch(dataList);
        return Result.success(result);
    }
}
