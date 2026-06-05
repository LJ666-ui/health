package com.zhihealth.log.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhihealth.common.result.Result;
import com.zhihealth.common.util.PageQuery;
import com.zhihealth.log.entity.OperationLog;
import com.zhihealth.log.service.LogService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/log")
@RequiredArgsConstructor
public class LogController {

    private final LogService logService;

    @GetMapping("/list")
    public Result<Page<OperationLog>> getLogList(PageQuery pageQuery,
                                                  @RequestParam(required = false) String actionType,
                                                  @RequestParam(required = false) String operator,
                                                  @RequestParam(required = false) String module,
                                                  @RequestParam(required = false) String result,
                                                  @RequestParam(required = false) String startTime,
                                                  @RequestParam(required = false) String endTime) {
        Page<OperationLog> page = logService.getLogList(pageQuery, actionType, operator, module, result, startTime, endTime);
        return Result.success(page);
    }

    @GetMapping("/{id}")
    public Result<OperationLog> getLogDetail(@PathVariable Long id) {
        OperationLog log = logService.getLogDetail(id);
        if (log == null) {
            return Result.error(404, "日志不存在");
        }
        return Result.success(log);
    }

    @DeleteMapping("/batch")
    public Result<Void> deleteLogs(@RequestBody List<Long> ids) {
        boolean success = logService.deleteLogs(ids);
        if (success) {
            return Result.success();
        } else {
            return Result.error(500, "删除失败");
        }
    }

    @DeleteMapping("/clear")
    public Result<Map<String, Object>> clearLogs(@RequestParam String beforeDate) {
        long deletedCount = logService.clearLogsBeforeDate(java.time.LocalDate.parse(beforeDate));
        
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("deletedCount", deletedCount);
        result.put("message", "成功清理" + deletedCount + "条历史日志");
        
        return Result.success(result);
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics() {
        Map<String, Object> stats = logService.getLogStatistics();
        return Result.success(stats);
    }

    @GetMapping("/recent")
    public Result<List<Map<String, Object>>> getRecentLogs(@RequestParam(defaultValue = "10") int limit) {
        List<Map<String, Object>> logs = logService.getRecentLogs(limit);
        return Result.success(logs);
    }

    @GetMapping("/export")
    public ResponseEntity<byte[]> exportLogs(@RequestParam(required = false) String actionType,
                                              @RequestParam(required = false) String operator,
                                              @RequestParam(required = false) String module,
                                              @RequestParam(required = false) String result,
                                              @RequestParam(required = false) String startTime,
                                              @RequestParam(required = false) String endTime) {
        byte[] data = logService.exportLogs(actionType, operator, module, result, startTime, endTime);

        String filename;
        try {
            filename = URLEncoder.encode("操作日志_" + java.time.LocalDate.now() + ".csv", "UTF-8")
                    .replaceAll("\\+", "%20");
        } catch (java.io.UnsupportedEncodingException e) {
            filename = "operation_log.csv";
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("text/csv; charset=utf-8"));
        headers.setContentDispositionFormData("attachment", filename);
        headers.setContentLength(data.length);

        return ResponseEntity.ok()
                .headers(headers)
                .body(data);
    }
}
