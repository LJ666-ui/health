package com.zhihealth.gateway.config;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * 熔断降级配置
 * 基于Resilience4j实现：
 * - 慢调用比例阈值：50%
 * - 熔断持续时间：30秒
 * - 半开状态允许请求数：3个
 * - 失败率阈值：50%
 */
// @Configuration  // Temporarily disabled - Resilience4j version conflict
public class ResilienceConfig {

    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry() {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig config =
                io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                        .failureRateThreshold(50)
                        .slowCallDurationThreshold(Duration.ofSeconds(2))
                        .slowCallRateThreshold(50)
                        .waitDurationInOpenState(Duration.ofSeconds(30))
                        .permittedNumberOfCallsInHalfOpenState(3)
                        .slidingWindowSize(10)
                        .slidingWindowType(io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                        .recordExceptions(
                                java.net.ConnectException.class,
                                java.net.SocketTimeoutException.class,
                                java.io.IOException.class,
                                org.springframework.web.client.ResourceAccessException.class
                        )
                        .build();

        return CircuitBreakerRegistry.of(config);
    }

    /**
     * 用户服务熔断器
     */
    @Bean
    public CircuitBreaker userCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker("userService");
    }

    /**
     * AI服务熔断器（AI响应较慢，放宽阈值）
     */
    @Bean
    public CircuitBreaker aiCircuitBreaker(CircuitBreakerRegistry registry) {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig aiConfig =
                io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                        .failureRateThreshold(60)
                        .slowCallDurationThreshold(Duration.ofSeconds(10))
                        .slowCallRateThreshold(70)
                        .waitDurationInOpenState(Duration.ofSeconds(20))
                        .permittedNumberOfCallsInHalfOpenState(2)
                        .slidingWindowSize(5)
                        .recordExceptions(
                                java.net.ConnectException.class,
                                java.net.SocketTimeoutException.class,
                                java.util.concurrent.TimeoutException.class
                        )
                        .build();
        return registry.circuitBreaker("aiService", aiConfig);
    }

    /**
     * 数据存储服务熔断器
     */
    @Bean
    public CircuitBreaker storageCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker("storageService");
    }

    /**
     * 预警服务熔断器
     */
    @Bean
    public CircuitBreaker alertCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker("alertService");
    }
}
