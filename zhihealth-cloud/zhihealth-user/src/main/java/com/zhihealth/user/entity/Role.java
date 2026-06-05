package com.zhihealth.user.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.zhihealth.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("sys_role")
public class Role extends BaseEntity {

    private String roleName;
    private String roleCode;
    private String description;
    private Integer status;
    private Integer sortOrder;
}
