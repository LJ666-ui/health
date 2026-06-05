package com.zhihealth.ai.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("ai_analysis_record")
public class AiAnalysisRecord extends BaseEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String analysisType;

    private String inputData;

    private String resultData;

    private String modelUsed;

    private Double confidenceScore;

    private Integer status;

    private String errorMessage;

    private LocalDateTime analysisTime;

    private Long executionTimeMs;
}
