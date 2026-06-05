package com.zhihealth.device.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("device_info")
public class DeviceInfo extends BaseEntity {
    
    private String deviceName;
    private String deviceType;
    private String deviceModel;
    private String serialNumber;
    private String firmwareVersion;
    private Long userId;
    private Integer status;
    private String location;
}
