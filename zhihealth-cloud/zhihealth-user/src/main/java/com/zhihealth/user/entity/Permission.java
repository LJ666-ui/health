package com.zhihealth.user.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("sys_permission")
public class Permission extends BaseEntity {

    private String permissionName;
    private String permissionCode;
    private String resourceType;
    private String resourceCode;
    private String action;
    private Integer status;
    private Long parentId;
    private Integer sortOrder;
}
