package com.zhihealth.alert.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("alert_rule")
public class AlertRule extends BaseEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String ruleName;

    private String ruleCode;

    private String dataType;

    private String metric;

    private String condition;

    private Double threshold;

    private String unit;

    private Integer level;

    private Boolean enabled;

    private String description;

    private Long userId;

    private Long deviceId;
}
