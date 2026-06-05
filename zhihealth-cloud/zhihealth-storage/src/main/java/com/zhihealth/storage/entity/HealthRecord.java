package com.zhihealth.storage.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.math.BigDecimal;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("health_record")
public class HealthRecord extends BaseEntity {
    
    private Long userId;
    private Long deviceId;
    private String dataType;
    private BigDecimal heartRate;
    private BigDecimal bodyTemp;
    private Integer bloodPressureSystolic;
    private Integer bloodPressureDiastolic;
    private Integer steps;
    private BigDecimal sleepHours;
    private Long timestamp;
}
