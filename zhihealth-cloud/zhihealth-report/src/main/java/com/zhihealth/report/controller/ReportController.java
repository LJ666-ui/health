package com.zhihealth.report.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhihealth.common.result.Result;
import com.zhihealth.common.util.PageQuery;
import com.zhihealth.report.entity.ReportRecord;
import com.zhihealth.report.service.DataExportService;
import com.zhihealth.report.service.DataImportService;
import com.zhihealth.report.service.ReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/report")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;
    private final DataExportService dataExportService;
    private final DataImportService dataImportService;

    @GetMapping("/list")
    public Result<Page<ReportRecord>> getReportList(PageQuery pageQuery,
                                                     @RequestParam(required = false) String reportType,
                                                     @RequestParam(required = false) String status,
                                                     @RequestParam(required = false) Long userId,
                                                     @RequestParam(required = false) String startTime,
                                                     @RequestParam(required = false) String endTime) {
        Page<ReportRecord> page = reportService.getReportList(pageQuery, reportType, status, userId, startTime, endTime);
        return Result.success(page);
    }

    @PostMapping("/generate")
    public Result<Map<String, Object>> generateReport(@RequestParam Long userId,
                                                       @RequestParam String reportType,
                                                       @RequestParam List<String> dateRange,
                                                       @RequestParam(defaultValue = "pdf") String format,
                                                       @RequestParam(defaultValue = "healthData,trendAnalysis") List<String> includeContent) {
        Map<String, Object> result = reportService.generateReport(userId, reportType, dateRange, format, includeContent);
        
        if ((Boolean) result.getOrDefault("success", false)) {
            return Result.success(result);
        } else {
            return Result.error(500, (String) result.get("error"));
        }
    }

    @GetMapping("/{id}")
    public Result<ReportRecord> getReportDetail(@PathVariable Long id) {
        ReportRecord report = reportService.getReportDetail(id);
        if (report == null) {
            return Result.error(404, "报告不存在");
        }
        return Result.success(report);
    }

    @GetMapping("/{id}/download")
    public ResponseEntity<byte[]> downloadReport(@PathVariable Long id) {
        try {
            byte[] bytes = reportService.downloadReport(id);
            ReportRecord report = reportService.getReportDetail(id);

            String filename = URLEncoder.encode(report.getTitle(), "UTF-8")
                    .replaceAll("\\+", "%20");

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
            headers.setContentDispositionFormData("attachment", filename + "." + report.getFormat());
            headers.setContentLength(bytes.length);

            return ResponseEntity.ok()
                    .headers(headers)
                    .body(bytes);
        } catch (Exception e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteReport(@PathVariable Long id) {
        boolean success = reportService.deleteReport(id);
        if (success) {
            return Result.success();
        } else {
            return Result.error(500, "删除失败");
        }
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics() {
        Map<String, Object> stats = reportService.getReportStatistics();
        return Result.success(stats);
    }

    // ==================== 数据导出/导入 ====================

    /**
     * 导出健康数据为Excel
     */
    @GetMapping("/export/excel")
    public void exportExcel(@RequestParam Long userId,
                            @RequestParam String dataType,
                            @RequestParam(required = false) String startDate,
                            @RequestParam(required = false) String endDate,
                            HttpServletResponse response) {
        Map<String, String> headers = new HashMap<>();
        headers.put("id", "ID");
        headers.put("dataType", "数据类型");
        headers.put("dataValue", "测量值");
        headers.put("unit", "单位");
        headers.put("measureTime", "测量时间");
        headers.put("source", "来源");
        headers.put("isAbnormal", "是否异常");
        // dataExportService.exportExcel(dataList, headers, "健康数据_" + dataType, response);
    }

    /**
     * 导入健康数据(Excel)
     */
    @PostMapping("/import/excel")
    public Result<DataImportService.ImportResult> importExcel(@RequestParam Long userId,
                                                               MultipartFile file) {
        try {
            DataImportService.ImportResult result = dataImportService.importHealthData(file, userId);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("导入失败: " + e.getMessage());
        }
    }

    /**
     * 下载导入模板
     */
    @GetMapping("/import/template")
    public void downloadTemplate(HttpServletResponse response) throws IOException {
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setHeader("Content-Disposition",
                "attachment; filename=" + URLEncoder.encode("健康数据导入模板.xlsx", "UTF-8"));

        // dataExportService.exportTemplate(response);
    }
}
