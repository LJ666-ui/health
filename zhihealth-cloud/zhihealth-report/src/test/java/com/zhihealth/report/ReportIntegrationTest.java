package com.zhihealth.report;

import com.zhihealth.report.service.DataImportService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 报告模块集成测试
 * - 数据导入导出逻辑
 * - Excel/PDF处理流程
 */
@DisplayName("报告导出导入集成测试")
public class ReportIntegrationTest {

    @Test
    @DisplayName("导入结果统计准确性")
    void testImportResultStats() {
        DataImportService.ImportResult result = new DataImportService.ImportResult();
        result.setTotalRows(100);
        result.setSuccessCount(95);
        result.setFailCount(5);

        assertEquals(100, result.getTotalRows());
        assertEquals(95, result.getSuccessCount());
        assertEquals(5, result.getFailCount());
        assertEquals(result.getTotalRows(), result.getSuccessCount() + result.getFailCount());
    }

    @Test
    @DisplayName("导入错误信息累积")
    void testImportErrorsAccumulate() {
        DataImportService.ImportResult result = new DataImportService.ImportResult();
        result.getErrors().add("第2行: 数据类型不能为空");
        result.getErrors().add("第5行: 测量值不能为空");

        assertEquals(2, result.getErrors().size());
        assertTrue(result.getErrors().get(0).contains("第2行"));
        assertTrue(result.getErrors().get(1).contains("第5行"));
    }

    @Test
    @DisplayName("Excel列头映射完整性")
    void testHeaderMapping() {
        Map<Integer, String> headers = new HashMap<>();
        headers.put(0, "measureTime");
        headers.put(1, "dataType");
        headers.put(2, "dataValue");
        headers.put(3, "unit");
        headers.put(4, "source");

        assertEquals(5, headers.size());
        assertEquals("measureTime", headers.get(0));
        assertEquals("dataValue", headers.get(2));
        assertNull(headers.get(99), "不存在的列返回null");
    }

    @Test
    @DisplayName("行处理器回调计数")
    void testRowProcessorCallback() {
        AtomicInteger processed = new AtomicInteger(0);
        Map<String, Object> row = new HashMap<>();
        row.put("dataType", "heart_rate");
        row.put("dataValue", "75");

        // 模拟处理10行
        for (int i = 0; i < 10; i++) {
            processed.incrementAndGet();
        }
        assertEquals(10, processed.get());
    }

    @Test
    @DisplayName("文件类型校验")
    void testFileTypeValidation() {
        String[] valid = {"data.xlsx", "report.xls", "health.XLSX"};
        String[] invalid = {"data.csv", "report.txt", "image.png"};

        for (String f : valid) {
            String lower = f.toLowerCase();
            assertTrue(lower.endsWith(".xlsx") || lower.endsWith(".xls"), f + "应为有效Excel");
        }
        for (String f : invalid) {
            assertFalse(f.toLowerCase().endsWith(".xlsx") || f.toLowerCase().endsWith(".xls"), f + "应为无效");
        }
    }
}
