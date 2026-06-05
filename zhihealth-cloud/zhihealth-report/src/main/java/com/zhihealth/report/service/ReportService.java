package com.zhihealth.report.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhihealth.common.util.PageQuery;
import com.zhihealth.report.entity.ReportRecord;
import com.zhihealth.report.mapper.ReportRecordMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReportService {

    private final ReportRecordMapper reportRecordMapper;
    private final StringRedisTemplate redisTemplate;
    
    public Page<ReportRecord> getReportList(PageQuery pageQuery,
                                            String reportType,
                                            String status,
                                            Long userId,
                                            String startTime,
                                            String endTime) {
        Page<ReportRecord> page = new Page<>(pageQuery.getPageNum(), pageQuery.getPageSize());
        
        LambdaQueryWrapper<ReportRecord> wrapper = new LambdaQueryWrapper<>();
        
        if (reportType != null && !reportType.isEmpty()) {
            wrapper.eq(ReportRecord::getReportType, reportType);
        }
        
        if (status != null && !status.isEmpty()) {
            wrapper.eq(ReportRecord::getStatus, status);
        }
        
        if (userId != null) {
            wrapper.eq(ReportRecord::getUserId, userId);
        }
        
        if (startTime != null && !startTime.isEmpty()) {
            wrapper.ge(ReportRecord::getGenerateTime, startTime);
        }
        
        if (endTime != null && !endTime.isEmpty()) {
            wrapper.le(ReportRecord::getGenerateTime, endTime + " 23:59:59");
        }
        
        wrapper.orderByDesc(ReportRecord::getGenerateTime);
        
        return reportRecordMapper.selectPage(page, wrapper);
    }

    public Map<String, Object> generateReport(Long userId,
                                               String reportType,
                                               List<String> dateRange,
                                               String format,
                                               List<String> includeContent) {
        Map<String, Object> result = new HashMap<>();
        long startTime = System.currentTimeMillis();
        
        try {
            String title = buildReportTitle(userId, reportType);
            
            ReportRecord record = new ReportRecord();
            record.setUserId(userId);
            record.setTitle(title);
            record.setReportType(reportType);
            record.setFormat(format.toLowerCase());
            record.setStatus("generating");
            record.setGenerateTime(LocalDateTime.now());
            
            reportRecordMapper.insert(record);
            
            cacheReportStatus(record.getId(), "generating");
            
            Thread.sleep(2000);
            
            String filePath = generateReportFile(record, includeContent);
            long fileSize = estimateFileSize(format);
            
            String summary = generateSummary(userId, reportType);
            String aiInsights = generateAiInsights(userId);
            String recommendations = generateRecommendations(userId, reportType);
            
            long executionTime = System.currentTimeMillis() - startTime;
            
            record.setStatus("completed");
            record.setFilePath(filePath);
            record.setFileSize(fileSize);
            record.setSummary(summary);
            record.setAiInsights(aiInsights);
            record.setRecommendations(recommendations);
            record.setExecutionTimeMs(executionTime);
            
            reportRecordMapper.updateById(record);
            
            cacheReportStatus(record.getId(), "completed");
            
            result.put("success", true);
            result.put("reportId", record.getId());
            result.put("title", title);
            result.put("filePath", filePath);
            result.put("fileSize", fileSize);
            result.put("format", format.toUpperCase());
            result.put("executionTimeMs", executionTime);
            result.put("message", "报告生成成功");
            
        } catch (Exception e) {
            log.error("生成报告失败", e);
            result.put("success", false);
            result.put("error", "报告生成失败: " + e.getMessage());
        }
        
        return result;
    }

    public ReportRecord getReportDetail(Long id) {
        return reportRecordMapper.selectById(id);
    }

    public byte[] downloadReport(Long id) {
        ReportRecord record = reportRecordMapper.selectById(id);
        
        if (record == null) {
            throw new RuntimeException("报告不存在");
        }
        
        if (!"completed".equals(record.getStatus())) {
            throw new RuntimeException("报告尚未生成完成");
        }
        
        return generateMockReportBytes(record.getFormat());
    }

    public boolean deleteReport(Long id) {
        int rows = reportRecordMapper.deleteById(id);
        return rows > 0;
    }

    public Map<String, Object> getReportStatistics() {
        Map<String, Object> stats = new HashMap<>();
        
        long totalCount = reportRecordMapper.selectCount(new LambdaQueryWrapper<>());
        
        long todayCount = reportRecordMapper.selectCount(
            new LambdaQueryWrapper<ReportRecord>()
                .ge(ReportRecord::getGenerateTime, 
                    LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd 00:00:00")))
        );
        
        long completedCount = reportRecordMapper.selectCount(
            new LambdaQueryWrapper<ReportRecord>()
                .eq(ReportRecord::getStatus, "completed")
        );
        
        stats.put("totalCount", totalCount);
        stats.put("todayCount", todayCount);
        stats.put("completedCount", completedCount);
        stats.put("generatingCount", totalCount - completedCount);
        
        return stats;
    }

    private String buildReportTitle(Long userId, String reportType) {
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy年MM月dd日");
        String dateStr = LocalDateTime.now().format(formatter);

        String typeText;
        switch (reportType) {
            case "comprehensive":
                typeText = "综合健康";
                break;
            case "specialized":
                typeText = "专项分析";
                break;
            case "trend":
                typeText = "趋势预测";
                break;
            case "anomaly":
                typeText = "异常检测";
                break;
            default:
                typeText = "健康数据";
                break;
        }

        return String.format("用户%d - %s报告（%s）", userId, typeText, dateStr);
    }

    private void cacheReportStatus(Long reportId, String status) {
        String key = "report:status:" + reportId;
        redisTemplate.opsForValue().set(key, status, 1, TimeUnit.HOURS);
    }

    private String generateReportFile(ReportRecord record, List<String> includeContent) {
        String basePath = "/reports/" + record.getUserId() + "/";
        String fileName = String.format("report_%d_%s.%s",
            record.getId(),
            LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss")),
            record.getFormat()
        );
        
        return basePath + fileName;
    }

    private long estimateFileSize(String format) {
        String fmt = format.toLowerCase();
        switch (fmt) {
            case "pdf":
                return (long)(Math.random() * 3000000 + 500000);
            case "excel":
                return (long)(Math.random() * 1500000 + 300000);
            case "word":
                return (long)(Math.random() * 1000000 + 200000);
            default:
                return (long)(Math.random() * 500000 + 100000);
        }
    }

    @SuppressWarnings("unchecked")
    private String generateSummary(Long userId, String reportType) {
        Map<String, Object> summary = new HashMap<>();
        summary.put("overallScore", 85 + Math.random() * 10);
        summary.put("healthLevel", "良好");

        List<Map<String, Object>> keyMetrics = new ArrayList<>();
        keyMetrics.add(buildMetricMap("心血管健康", 88, "normal"));
        keyMetrics.add(buildMetricMap("代谢指标", 82, "attention"));
        keyMetrics.add(buildMetricMap("运动能力", 90, "good"));
        keyMetrics.add(buildMetricMap("睡眠质量", 78, "normal"));
        summary.put("keyMetrics", keyMetrics);

        summary.put("dataRange", "最近30天");
        summary.put("totalRecords", 1256);

        return JSON.toJSONString(summary);
    }

    @SuppressWarnings("unchecked")
    private String generateAiInsights(Long userId) {
        List<Map<String, Object>> insights = new ArrayList<>();

        Map<String, Object> insight1 = new HashMap<>();
        insight1.put("type", "positive");
        insight1.put("title", "心血管功能稳定");
        insight1.put("description", "近期血压和心率数据均在正常范围内波动，整体心血管功能表现良好");
        insight1.put("confidence", 0.92);
        insights.add(insight1);

        Map<String, Object> insight2 = new HashMap<>();
        insight2.put("type", "warning");
        insight2.put("title", "血糖偶有偏高");
        insight2.put("description", "空腹血糖值在部分时段出现轻度升高，建议控制碳水化合物摄入并定期监测");
        insight2.put("confidence", 0.78);
        insights.add(insight2);

        Map<String, Object> insight3 = new HashMap<>();
        insight3.put("type", "info");
        insight3.put("title", "运动习惯良好");
        insight3.put("description", "每周保持3-4次有氧运动，步数达标率85%，建议增加力量训练");
        insight3.put("confidence", 0.85);
        insights.add(insight3);

        return JSON.toJSONString(insights);
    }

    @SuppressWarnings("unchecked")
    private String generateRecommendations(Long userId, String reportType) {
        List<Map<String, Object>> recommendations = new ArrayList<>();

        recommendations.add(buildRecMap("high", "饮食调整", "优化膳食结构",
            "减少高盐高脂食物摄入，增加蔬菜水果比例，每日饮水量保持在2000ml以上"));

        recommendations.add(buildRecMap("medium", "运动计划", "规律有氧运动",
            "每周至少进行3次有氧运动，每次30分钟以上，推荐快走或游泳"));

        recommendations.add(buildRecMap("medium", "定期检查", "完成年度体检",
            "建议完成年度体检，重点关注血脂、肝肾功能等指标"));

        recommendations.add(buildRecMap("low", "作息调整", "改善睡眠质量",
            "保持规律作息，睡前避免使用电子设备，确保7-8小时睡眠时间"));

        return JSON.toJSONString(recommendations);
    }

    private Map<String, Object> buildMetricMap(String name, int score, String status) {
        Map<String, Object> map = new HashMap<>();
        map.put("name", name);
        map.put("score", score);
        map.put("status", status);
        return map;
    }

    private Map<String, Object> buildRecMap(String priority, String category, String title, String content) {
        Map<String, Object> map = new HashMap<>();
        map.put("priority", priority);
        map.put("category", category);
        map.put("title", title);
        map.put("content", content);
        map.put("actionable", true);
        return map;
    }

    private byte[] generateMockReportBytes(String format) {
        int size = (int)(Math.random() * 100000 + 50000);
        byte[] bytes = new byte[size];
        for (int i = 0; i < size; i++) {
            bytes[i] = (byte)(Math.random() * 256);
        }
        return bytes;
    }
}
