package com.zhihealth.ai.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhihealth.ai.entity.AiAnalysisRecord;
import com.zhihealth.ai.service.AiAnalysisService;
import com.zhihealth.ai.service.OllamaService;
import com.zhihealth.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/ai")
public class AiController {

    @Autowired
    private AiAnalysisService aiAnalysisService;

    @Autowired
    private OllamaService ollamaService;

    @PostMapping("/analyze")
    public Result<Map<String, Object>> analyzeHealthData(
            @RequestParam Long userId,
            @RequestBody Map<String, Object> healthData) {
        
        Map<String, Object> result = aiAnalysisService.analyzeHealthData(userId, healthData);
        return Result.success(result);
    }

    @PostMapping("/predict")
    public Result<Map<String, Object>> predictHealthTrend(
            @RequestParam Long userId,
            @RequestBody List<Map<String, Object>> timeSeriesData,
            @RequestParam(defaultValue = "7") int days) {
        
        Map<String, Object> result = aiAnalysisService.predictHealthTrend(userId, timeSeriesData, days);
        return Result.success(result);
    }

    @PostMapping("/detect-anomalies")
    public Result<Map<String, Object>> detectAnomalies(
            @RequestParam Long userId,
            @RequestBody Map<String, Object> healthData) {
        
        Map<String, Object> result = aiAnalysisService.detectAnomalies(userId, healthData);
        return Result.success(result);
    }

    @PostMapping("/generate-report")
    public Result<Map<String, Object>> generateHealthReport(
            @RequestParam Long userId,
            @RequestBody List<Map<String, Object>> healthDataList) {
        
        Map<String, Object> result = aiAnalysisService.generateHealthReport(userId, healthDataList);
        return Result.success(result);
    }

    @GetMapping("/record/list")
    public Result<Page<AiAnalysisRecord>> getRecords(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) String analysisType) {
        
        Page<AiAnalysisRecord> page = aiAnalysisService.getRecordsByPage(pageNum, pageSize, userId, analysisType);
        return Result.success(page);
    }

    @GetMapping("/record/recent")
    public Result<List<AiAnalysisRecord>> getRecentAnalyses(
            @RequestParam Long userId,
            @RequestParam(defaultValue = "10") int limit) {
        
        List<AiAnalysisRecord> records = aiAnalysisService.getRecentAnalyses(userId, limit);
        return Result.success(records);
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics(@RequestParam(required = false) Long userId) {
        Map<String, Object> stats = aiAnalysisService.getAiStatistics(userId);
        return Result.success(stats);
    }

    @PostMapping("/chat")
    public Result<Map<String, Object>> chat(@RequestBody Map<String, String> params) {
        String question = params.get("question");
        if (question == null || question.isEmpty()) {
            return Result.error("问题不能为空");
        }
        
        @SuppressWarnings("unchecked")
        Object userContextObj = params.get("userContext");
        Map<String, Object> userContext = null;
        
        if (userContextObj instanceof Map) {
            userContext = (Map<String, Object>) userContextObj;
        }
        
        Map<String, Object> result = ollamaService.healthConsultation(question, userContext);
        return Result.success(result);
    }

    @PostMapping("/advice")
    public Result<Map<String, Object>> generateAdvice(@RequestBody Map<String, Object> healthData) {
        Map<String, Object> result = ollamaService.generateHealthAdvice(healthData);
        return Result.success(result);
    }

    @GetMapping("/status")
    public Result<Map<String, Object>> getAiServiceStatus() {
        Map<String, Object> status = new java.util.HashMap<>();
        status.put("ollamaAvailable", ollamaService.isOllamaAvailable());
        status.put("timestamp", System.currentTimeMillis());
        return Result.success(status);
    }
}
