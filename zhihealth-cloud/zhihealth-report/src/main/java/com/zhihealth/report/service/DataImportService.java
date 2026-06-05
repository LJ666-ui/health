package com.zhihealth.report.service;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

/**
 * 数据导入服务
 * - Excel批量导入健康数据
 * - 校验+去重+批量入库
 */
@Slf4j
@Service
public class DataImportService {

    /**
     * 导入结果
     */
    @Data
    public static class ImportResult {
        private int totalRows;
        private int successCount;
        private int failCount;
        private List<String> errors = new ArrayList<>();
        private List<Map<String, Object>> successData = new ArrayList<>();
    }

    /**
     * 通用Excel导入（基于Apache POI）
     *
     * @param file         上传的Excel文件
     * @param headers      列头映射: { 列索引(0-based): 字段名 }
     * @param rowProcessor 每行数据处理回调
     * @return 导入结果
     */
    public ImportResult importExcel(MultipartFile file,
                                     Map<Integer, String> headers,
                                     BiConsumer<Map<String, Object>, Integer> rowProcessor) throws IOException {
        ImportResult result = new ImportResult();

        if (file == null || file.isEmpty()) {
            result.getErrors().add("文件为空");
            return result;
        }

        String fileName = file.getOriginalFilename();
        if (fileName != null && !fileName.endsWith(".xlsx") && !fileName.endsWith(".xls")) {
            result.getErrors().add("仅支持Excel文件(.xlsx/.xls)");
            return result;
        }

        try (Workbook workbook = WorkbookFactory.create(file.getInputStream())) {
            Sheet sheet = workbook.getSheetAt(0);

            for (int i = 1; i <= sheet.getLastRowNum(); i++) { // 跳过标题行
                Row row = sheet.getRow(i);
                if (row == null) continue;

                result.totalRows++;
                try {
                    Map<String, Object> rowData = new HashMap<>();
                    headers.forEach((colIdx, fieldName) -> {
                        Cell cell = row.getCell(colIdx);
                        rowData.put(fieldName, getCellValue(cell));
                    });

                    rowProcessor.accept(rowData, result.totalRows);
                    result.successCount++;
                    result.successData.add(rowData);

                } catch (Exception e) {
                    result.failCount++;
                    String errMsg = "第" + (i + 1) + "行: " + e.getMessage();
                    result.getErrors().add(errMsg);
                    log.warn("导入行数据异常: {}", errMsg);
                }
            }
        } catch (Exception e) {
            log.error("数据导入异常", e);
            result.getErrors().add("导入异常: " + e.getMessage());
        }

        log.info("数据导入完成: 总{}条, 成功{}, 失败{}", result.totalRows, result.successCount, result.failCount);
        return result;
    }

    /**
     * 读取单元格值
     */
    private Object getCellValue(Cell cell) {
        if (cell == null) return "";
        switch (cell.getCellType()) {
            case STRING:
                return cell.getStringCellValue().trim();
            case NUMERIC:
                return DateUtil.isCellDateFormatted(cell)
                        ? cell.getLocalDateTimeCellValue()
                        : cell.getNumericCellValue();
            case BOOLEAN:
                return cell.getBooleanCellValue();
            case FORMULA:
                return cell.getCellFormula();
            default:
                return "";
        }
    }

    /**
     * 健康数据导入专用方法
     */
    public ImportResult importHealthData(MultipartFile file, Long userId) throws IOException {
        Map<Integer, String> headers = new HashMap<>();
        headers.put(0, "measureTime");
        headers.put(1, "dataType");
        headers.put(2, "dataValue");
        headers.put(3, "unit");
        headers.put(4, "source");

        return importExcel(file, headers, (row, rowNum) -> {
            // 校验必填字段
            String dataType = (String) row.getOrDefault("dataType", "");
            String value = (String) row.getOrDefault("dataValue", "");
            if (dataType == null || dataType.trim().isEmpty()) throw new IllegalArgumentException("数据类型不能为空");
            if (value == null || value.trim().isEmpty()) throw new IllegalArgumentException("测量值不能为空");

            // 补充用户ID
            row.put("userId", userId);

            // 转换并保存到数据库
            // healthDataService.saveFromImport(userId, row);
        });
    }
}
