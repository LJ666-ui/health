package com.zhihealth.alert.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("alert_record")
public class AlertRecord extends BaseEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long ruleId;

    private String ruleName;

    private Long userId;

    private Long deviceId;

    private String dataType;

    private String metric;

    private Double currentValue;

    private Double threshold;

    private String condition;

    private Integer level;

    private String message;

    private Integer status;

    private LocalDateTime alertTime;

    private LocalDateTime resolveTime;

    private String resolvedBy;

    private String remark;
}
