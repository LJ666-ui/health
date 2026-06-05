package com.zhihealth.report.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("report_record")
public class ReportRecord extends BaseEntity {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long userId;
    
    private String title;
    
    private String reportType;
    
    private String format;
    
    private String status;
    
    private String filePath;
    
    private Long fileSize;
    
    private String summary;
    
    private String aiInsights;
    
    private String recommendations;
    
    private LocalDateTime generateTime;
    
    private Long executionTimeMs;
    
    @TableField(exist = false)
    private String generateTimeStart;
    
    @TableField(exist = false)
    private String generateTimeEnd;
}
