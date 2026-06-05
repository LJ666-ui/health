package com.zhihealth.collect.dto;

import lombok.Data;
import javax.validation.constraints.*;
import java.math.BigDecimal;

@Data
public class HealthDataDTO {
    
    @NotNull(message = "Device ID is required")
    private Long deviceId;
    
    @NotNull(message = "User ID is required")
    private Long userId;
    
    @NotNull(message = "Data type is required")
    private String dataType;
    
    private BigDecimal heartRate;
    private BigDecimal bodyTemp;
    private Integer bloodPressureSystolic;
    private Integer bloodPressureDiastolic;
    private Integer steps;
    private BigDecimal sleepHours;
    
    @NotNull(message = "Timestamp is required")
    private Long timestamp;
}
