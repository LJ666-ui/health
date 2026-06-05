package com.zhihealth.alert.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhihealth.alert.entity.AlertRecord;
import com.zhihealth.alert.entity.AlertRule;
import com.zhihealth.alert.service.AlertEngineService;
import com.zhihealth.alert.service.AlertRuleService;
import com.zhihealth.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.net.URLEncoder;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/alert")
public class AlertController {

    @Autowired
    private AlertRuleService alertRuleService;

    @Autowired
    private AlertEngineService alertEngineService;

    // ==================== 预警规则管理 ====================

    @PostMapping("/rule")
    public Result<AlertRule> createRule(@RequestBody AlertRule rule) {
        rule.setEnabled(true);
        boolean success = alertRuleService.save(rule);
        return success ? Result.success(rule) : Result.error("创建预警规则失败");
    }

    @PutMapping("/rule/{ruleId}")
    public Result<AlertRule> updateRule(@PathVariable Long ruleId, @RequestBody AlertRule rule) {
        rule.setId(ruleId);
        boolean success = alertRuleService.updateById(rule);
        return success ? Result.success(rule) : Result.error("更新预警规则失败");
    }

    @GetMapping("/rule/list")
    public Result<Page<AlertRule>> getRules(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) Long userId) {

        Page<AlertRule> page = alertRuleService.getRulesByPage(pageNum, pageSize, userId);
        return Result.success(page);
    }

    @PutMapping("/rule/{ruleId}/toggle")
    public Result<Boolean> toggleRuleStatus(@PathVariable Long ruleId, @RequestParam boolean enabled) {
        boolean success = alertRuleService.toggleRuleStatus(ruleId, enabled);
        return success ? Result.success(true) : Result.error("更新规则状态失败");
    }

    @DeleteMapping("/rule/{ruleId}")
    public Result<Boolean> deleteRule(@PathVariable Long ruleId) {
        boolean success = alertRuleService.removeById(ruleId);
        return success ? Result.success(true) : Result.error("删除规则失败");
    }

    @GetMapping("/rules/enabled")
    public Result<List<AlertRule>> getEnabledRules() {
        List<AlertRule> rules = alertRuleService.getEnabledRules();
        return Result.success(rules);
    }

    // ==================== 预警记录管理 ====================

    @PostMapping("/evaluate")
    public Result<Map<String, Object>> evaluateData(@RequestBody Map<String, Object> healthData) {
        Map<String, Object> result = alertEngineService.evaluateData(healthData);
        return Result.success(result);
    }

    @GetMapping("/record/list")
    public Result<Page<AlertRecord>> getRecords(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) Long userId) {

        Page<AlertRecord> page = alertEngineService.getRecordsByPage(pageNum, pageSize, status, userId);
        return Result.success(page);
    }

    @GetMapping("/record/active")
    public Result<List<AlertRecord>> getActiveAlerts(@RequestParam(required = false) Long userId) {
        List<AlertRecord> alerts = alertEngineService.getActiveAlerts(userId);
        return Result.success(alerts);
    }

    @PutMapping("/record/{recordId}/resolve")
    public Result<Boolean> resolveAlert(
            @PathVariable Long recordId,
            @RequestParam String resolvedBy,
            @RequestParam(required = false) String remark) {

        boolean success = alertEngineService.resolveAlert(recordId, resolvedBy, remark);
        return success ? Result.success(true) : Result.error("处理预警失败");
    }

    /** 批量处理预警 */
    @PutMapping("/record/batch-resolve")
    public Result<Map<String, Object>> batchResolveAlerts(@RequestBody Map<String, Object> params) {
        @SuppressWarnings("unchecked")
        List<Long> recordIds = (List<Long>) params.get("recordIds");
        String resolvedBy = (String) params.get("resolvedBy");
        String remark = params.get("remark") != null ? (String) params.get("remark") : "";

        if (recordIds == null || recordIds.isEmpty()) {
            return Result.error("请选择要处理的预警记录");
        }

        int successCount = 0;
        int failCount = 0;
        for (Long recordId : recordIds) {
            try {
                boolean ok = alertEngineService.resolveAlert(recordId, resolvedBy, remark);
                if (ok) successCount++; else failCount++;
            } catch (Exception e) {
                failCount++;
            }
        }

        Map<String, Object> result = new java.util.HashMap<>();
        result.put("successCount", successCount);
        result.put("failCount", failCount);
        result.put("total", recordIds.size());
        return Result.success(result);
    }

    /** 导出预警记录 */
    @GetMapping("/record/export")
    public void exportRecords(
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate,
            HttpServletResponse response) {

        try {
            // 设置响应头
            String fileName = URLEncoder.encode("预警记录导出", "UTF-8").replaceAll("\\+", "%20");
            response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            response.setHeader("Content-Disposition", "attachment; filename=" + fileName + ".xlsx");

            // 查询数据并导出
            List<AlertRecord> records = alertEngineService.getExportRecords(status, userId, startDate, endDate);

            // 使用Hutool或POI生成Excel（简化实现：返回JSON格式）
            response.setContentType("application/json;charset=UTF-8");
            String json = com.alibaba.fastjson2.JSON.toJSONString(Result.success(records));
            response.getWriter().write(json);

        } catch (Exception e) {
            try {
                response.setStatus(500);
                response.setContentType("application/json;charset=UTF-8");
                response.getWriter().write(com.alibaba.fastjson2.JSON.toJSONString(Result.error("导出失败: " + e.getMessage())));
            } catch (Exception ignored) {}
        }
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics(
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate) {

        Map<String, Object> stats = alertEngineService.getAlertStatistics(userId, startDate, endDate);
        return Result.success(stats);
    }
}
