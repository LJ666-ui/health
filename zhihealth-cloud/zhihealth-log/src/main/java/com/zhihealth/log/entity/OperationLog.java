package com.zhihealth.log.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("operation_log")
public class OperationLog extends BaseEntity {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String operator;
    
    private String operatorId;
    
    private String module;
    
    private String actionType;
    
    private String description;
    
    private String method;
    
    private String url;
    
    private String requestMethod;
    
    private String requestParams;
    
    private String responseData;
    
    private String ipAddress;
    
    private String userAgent;
    
    private String result;
    
    private Long duration;
    
    private String errorMessage;
    
    private LocalDateTime operateTime;
    
    @TableField(exist = false)
    private String startTime;
    
    @TableField(exist = false)
    private String endTime;
}
