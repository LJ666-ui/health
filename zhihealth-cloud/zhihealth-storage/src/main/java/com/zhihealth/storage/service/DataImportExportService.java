package com.zhihealth.storage.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zhihealth.storage.entity.HealthRecord;
import com.zhihealth.storage.mapper.HealthRecordMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * 数据导入导出服务
 * - 支持CSV格式批量导入
 * - 支持多条件筛选导出
 * - 导入数据校验与去重
 */
@Slf4j
@Service
public class DataImportExportService extends ServiceImpl<HealthRecordMapper, HealthRecord> {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    /** 单次导入最大行数 */
    private static final int MAX_IMPORT_ROWS = 10000;

    /**
     * 批量导入健康数据（CSV）
     *
     * @param file 上传的文件（CSV格式）
     * @return 导入结果（成功数/失败数/总行数）
     */
    public Map<String, Object> importData(MultipartFile file) {
        Map<String, Object> result = new HashMap<>();
        result.put("success", false);
        result.put("totalRows", 0);
        result.put("successCount", 0);
        result.put("failCount", 0);
        result.put("errors", new ArrayList<String>());

        if (file == null || file.isEmpty()) {
            result.put("message", "上传文件不能为空");
            return result;
        }

        String originalName = file.getOriginalFilename();
        if (originalName == null || !originalName.endsWith(".csv")) {
            result.put("message", "仅支持CSV文件格式");
            return result;
        }

        try {
            List<Map<String, String>> rows = parseCsvFile(file);

            if (rows.size() > MAX_IMPORT_ROWS) {
                result.put("message", "单次导入最多支持" + MAX_IMPORT_ROWS + "条数据");
                return result;
            }

            result.put("totalRows", rows.size());

            List<String> errors = new ArrayList<>();
            int successCount = 0;
            Set<String> dedupSet = new HashSet<>();

            for (int i = 0; i < rows.size(); i++) {
                try {
                    Map<String, String> row = rows.get(i);

                    String dedupKey = row.getOrDefault("userId", "") + ":" +
                                      row.getOrDefault("deviceId", "") + ":" +
                                      row.getOrDefault("timestamp", "");

                    if (!dedupSet.add(dedupKey)) {
                        continue; // 跳过重复数据
                    }

                    HealthRecord record = buildRecordFromRow(row, i + 2);

                    validateRecord(record, i + 2, errors);

                    this.save(record);
                    successCount++;

                } catch (Exception e) {
                    errors.add("第" + (i + 2) + "行: " + e.getMessage());
                }
            }

            result.put("success", true);
            result.put("successCount", successCount);
            result.put("failCount", rows.size() - successCount);
            result.put("errors", errors);
            result.put("message", "导入完成，成功" + successCount + "条");

            log.info("数据导入完成: 总={}, 成功={}, 失败={}", rows.size(), successCount, rows.size() - successCount);

        } catch (Exception e) {
            log.error("数据导入失败", e);
            result.put("message", "导入失败: " + e.getMessage());
        }

        return result;
    }

    /**
     * 解析CSV文件
     */
    private List<Map<String, String>> parseCsvFile(MultipartFile file) throws Exception {
        List<Map<String, String>> rows = new ArrayList<>();

        BufferedReader reader = new BufferedReader(new InputStreamReader(file.getInputStream(), "UTF-8"));
        String headerLine = reader.readLine();
        if (headerLine == null) {
            return rows;
        }

        String[] headers = headerLine.split(",");
        String line;

        while ((line = reader.readLine()) != null) {
            if (line.trim().isEmpty()) continue;

            String[] values = line.split(",");
            Map<String, String> row = new HashMap<>();

            for (int i = 0; i < headers.length && i < values.length; i++) {
                row.put(headers[i].trim(), values[i].trim());
            }
            rows.add(row);
        }

        reader.close();
        return rows;
    }

    /**
     * 从行数据构建实体（适配HealthRecord字段）
     */
    private HealthRecord buildRecordFromRow(Map<String, String> row, int rowNum) {
        HealthRecord record = new HealthRecord();

        record.setUserId(parseLong(row.get("userId"), rowNum));
        record.setDeviceId(parseLong(row.get("deviceId"), rowNum));

        // 心率
        String hr = row.get("heartRate");
        if (hr != null && !hr.isEmpty()) record.setHeartRate(new BigDecimal(hr));

        // 体温
        String bt = row.get("bodyTemp");
        if (bt != null && !bt.isEmpty()) record.setBodyTemp(new BigDecimal(bt));

        // 收缩压
        String bps = row.get("bloodPressureSystolic");
        if (bps != null && !bps.isEmpty()) record.setBloodPressureSystolic(Integer.parseInt(bps));

        // 舒张压
        String bpd = row.get("bloodPressureDiastolic");
        if (bpd != null && !bpd.isEmpty()) record.setBloodPressureDiastolic(Integer.parseInt(bpd));

        // 步数
        String steps = row.get("steps");
        if (steps != null && !steps.isEmpty()) record.setSteps(Integer.parseInt(steps));

        // 睡眠时长
        String sleep = row.get("sleepHours");
        if (sleep != null && !sleep.isEmpty()) record.setSleepHours(new BigDecimal(sleep));

        // 时间戳
        String ts = row.get("timestamp");
        if (ts != null && !ts.isEmpty()) {
            try {
                long epochMillis = Long.parseLong(ts.trim());
                record.setTimestamp(epochMillis);
            } catch (NumberFormatException e) {
                record.setTimestamp(System.currentTimeMillis());
            }
        } else {
            record.setTimestamp(System.currentTimeMillis());
        }

        return record;
    }

    /**
     * 校验记录数据
     */
    private void validateRecord(HealthRecord record, int rowNum, List<String> errors) {
        if (record.getUserId() == null || record.getUserId() <= 0) {
            errors.add("第" + rowNum + "行: userId无效");
        }
    }

    private Long parseLong(String value, int rowNum) {
        if (value == null || value.trim().isEmpty()) return null;
        try {
            return Long.parseLong(value.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /**
     * 导出健康数据（多条件筛选）
     */
    public List<HealthRecord> exportData(Long userId, Long startTime, Long endTime, int limit) {
        LambdaQueryWrapper<HealthRecord> wrapper = new LambdaQueryWrapper<>();

        if (userId != null) {
            wrapper.eq(HealthRecord::getUserId, userId);
        }
        if (startTime != null && startTime > 0) {
            wrapper.ge(HealthRecord::getTimestamp, startTime);
        }
        if (endTime != null && endTime > 0) {
            wrapper.le(HealthRecord::getTimestamp, endTime);
        }

        wrapper.orderByDesc(HealthRecord::getTimestamp);

        Page<HealthRecord> page = new Page<>(1, Math.min(limit, 50000));
        return this.page(page, wrapper).getRecords();
    }
}
