package com.zhihealth.common.config;

import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Redisson分布式锁配置
 * - 单节点模式
 * - 连接池管理
 * - 看门狗自动续期
 */
@Configuration
public class RedissonConfig {

    @Value("${spring.redis.host:localhost}")
    private String redisHost;

    @Value("${spring.redis.port:6379}")
    private int redisPort;

    @Value("${spring.redis.password:}")
    private String redisPassword;

    @Value("${spring.redis.database:0}")
    private int database;

    @Bean(destroyMethod = "shutdown")
    public RedissonClient redissonClient() {
        Config config = new Config();

        String address = "redis://" + redisHost + ":" + redisPort;

        config.useSingleServer()
                .setAddress(address)
                .setDatabase(database)
                .setPassword(redisPassword != null && !redisPassword.isEmpty() ? redisPassword : null)
                // 连接池大小
                .setConnectionPoolSize(64)
                // 连接池最小空闲连接
                .setConnectionMinimumIdleSize(24)
                // 连接超时（毫秒）
                .setConnectTimeout(10000)
                // 命令等待超时（毫秒）
                .setTimeout(3000)
                // 命令失败重试次数
                .setRetryAttempts(3)
                // 命令重试间隔（毫秒）
                .setRetryInterval(1500)
                // 发布/订阅连接池大小
                .setSubscriptionConnectionPoolSize(50);

        return Redisson.create(config);
    }
}
