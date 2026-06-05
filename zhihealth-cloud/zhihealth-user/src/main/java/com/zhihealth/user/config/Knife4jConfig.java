package com.zhihealth.user.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * API文档配置
 *Knife4j集成配置（需在POM中启用knife4j依赖后生效）
 */
@Configuration
public class Knife4jConfig {

    /**
     * 基础API信息配置
     */
    @Bean
    public Object apiInfo() {
        // 当knife4j依赖可用时，这里会自动加载Swagger配置
        // 当前为占位配置，确保编译通过
        return new Object();
    }
}
