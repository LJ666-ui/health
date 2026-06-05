package com.zhihealth.common.annotation;

import java.lang.annotation.*;

/**
 * 接口幂等性注解
 * - 基于Token + Redis实现幂等性保证
 * - 防止表单重复提交/网络重试导致的数据重复
 * - 使用方式：在Controller方法上添加@Idempotent
 *
 * 使用流程：
 * 1. 前端调用 GET /api/idempotent/token 获取幂等Token
 * 2. 将Token放入请求头 X-Idempotent-Token
 * 3. 后端校验Token，同一Token只能成功执行一次
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Idempotent {

    /** 幂等Token在Redis中的过期时间（秒），默认5分钟 */
    long expireSeconds() default 300;

    /** 提示信息 */
    String message() default "请勿重复操作";

    /** 是否包含请求参数生成key（更严格的幂等） */
    boolean includeParams() default false;
}
