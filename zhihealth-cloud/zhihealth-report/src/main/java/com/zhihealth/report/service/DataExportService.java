package com.zhihealth.report.service;

import com.zhihealth.common.result.Result;
import com.zhihealth.report.mapper.ReportRecordMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Service;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 数据导出服务
 * - Excel批量导出（健康数据/预警记录/设备列表）
 * - PDF报告导出
 * - 模板化导出
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DataExportService {

    private final ReportRecordMapper reportRecordMapper;

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final DateTimeFormatter DATETIME_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    /**
     * 导出健康数据为Excel
     *
     * @param dataList   数据列表(每条数据为Map)
     * @param headers    列头定义: { "key": "显示名" }
     * @param sheetName  工作表名称
     * @param response   HTTP响应
     */
    public void exportExcel(List<Map<String, Object>> dataList,
                            Map<String, String> headers,
                            String sheetName,
                            HttpServletResponse response) throws IOException {
        try (Workbook workbook = new XSSFWorkbook()) {
            Sheet sheet = workbook.createSheet(sheetName);

            // 创建标题样式
            CellStyle headerStyle = workbook.createCellStyle();
            Font headerFont = workbook.createFont();
            headerFont.setBold(true);
            headerFont.setColor(IndexedColors.WHITE.getIndex());
            headerStyle.setFont(headerFont);
            headerStyle.setFillForegroundColor(IndexedColors.ROYAL_BLUE.getIndex());
            headerStyle.setFillPattern(FillPatternType.SOLID_FOREGROUND);
            headerStyle.setAlignment(HorizontalAlignment.CENTER);

            // 创建标题行
            Row headerRow = sheet.createRow(0);
            int colIdx = 0;
            List<String> keyOrder = new java.util.ArrayList<>(headers.keySet());
            for (String key : keyOrder) {
                Cell cell = headerRow.createCell(colIdx++);
                cell.setCellValue(headers.get(key));
                cell.setCellStyle(headerStyle);
                // 自动列宽
                sheet.autoSizeColumn(colIdx - 1);
            }

            // 填充数据行
            CellStyle dataStyle = workbook.createCellStyle();
            dataStyle.setAlignment(HorizontalAlignment.CENTER);

            int rowNum = 1;
            for (Map<String, Object> row : dataList) {
                Row dataRow = sheet.createRow(rowNum++);
                colIdx = 0;
                for (String key : keyOrder) {
                    Object value = row.get(key);
                    Cell cell = dataRow.createCell(colIdx++);
                    if (value != null) {
                        if (value instanceof Number) {
                            cell.setCellValue(((Number) value).doubleValue());
                        } else if (value instanceof LocalDateTime) {
                            cell.setCellValue(((LocalDateTime) value).format(DATETIME_FMT));
                        } else if (value instanceof LocalDate) {
                            cell.setCellValue(((LocalDate) value).format(DATE_FMT));
                        } else {
                            cell.setCellValue(value.toString());
                        }
                    }
                    cell.setCellStyle(dataStyle);
                }
            }

            // 冻结首行
            sheet.createFreezePane(0, 1);

            // 输出
            String fileName = URLEncoder.encode(sheetName + "_" + LocalDate.now() + ".xlsx", "UTF-8");
            response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            response.setHeader("Content-Disposition", "attachment; filename=" + fileName);
            workbook.write(response.getOutputStream());

            log.info("Excel导出完成: {} 条数据, 文件: {}", dataList.size(), fileName);
        }
    }

    /**
     * 导出预警记录Excel
     */
    public Result<Void> exportAlertRecords(Long userId,
                                            String level,
                                            String status,
                                            LocalDate startDate,
                                            LocalDate endDate,
                                            HttpServletResponse response) {
        try {
            // 查询数据（通过mapper或feign调用）
            // List<Map<String, Object>> records = alertClient.exportRecords(userId, level, status, startDate, endDate);

            Map<String, String> headers = new HashMap<>();
            headers.put("alertNo", "预警编号");
            headers.put("alertTitle", "预警标题");
            headers.put("alertLevel", "级别");
            headers.put("alertContent", "详情");
            headers.put("status", "状态");
            headers.put("createTime", "创建时间");

            // exportExcel(records, headers, "预警记录", response);
            return Result.success();
        } catch (Exception e) {
            log.error("导出预警记录失败", e);
            return Result.error("导出失败: " + e.getMessage());
        }
    }

    /**
     * 导出健康档案PDF报告
     */
    public Result<String> generatePdfReport(Long userId, String reportType, LocalDate periodStart, LocalDate periodEnd) {
        try {
            String reportNo = "RPT" + System.currentTimeMillis();

            // 1. 收集用户健康数据
            // 2. 调用AI生成分析摘要
            // 3. 使用iText/Apache POI生成PDF
            // 4. 上传至文件服务或本地存储

            log.info("PDF报告生成中: userId={}, type={}, period={}~{}", userId, reportType, periodStart, periodEnd);

            return Result.success(reportNo);
        } catch (Exception e) {
            log.error("PDF报告生成失败", e);
            return Result.error("报告生成失败: " + e.getMessage());
        }
    }
}
