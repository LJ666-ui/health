package com.zhihealth.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Duration;

/**
 * 请求重试过滤器
 * - 网络异常自动重试（最多3次）
 * - 仅对GET/HEAD等幂等方法重试
 * - 指数退避策略
 */
@Slf4j
@Component
public class RetryGlobalFilter implements GlobalFilter, Ordered {

    /** 最大重试次数 */
    private static final int MAX_RETRIES = 3;

    /** 重试间隔基数（毫秒） */
    private static final long RETRY_BASE_DELAY_MS = 200;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        return chain.filter(exchange)
                .onErrorResume(throwable -> {
                    String method = exchange.getRequest().getMethod().name();
                    String path = exchange.getRequest().getURI().getPath();

                    // 仅对幂等方法和特定可重试异常进行重试
                    if (isRetryableMethod(method) && isRetryableException(throwable)) {
                        log.warn("请求失败，准备重试: method={}, path={}, error={}",
                                method, path, throwable.getMessage());
                        return retryWithBackoff(exchange, chain, 0);
                    }

                    // 非可重试场景，直接返回错误
                    return Mono.error(throwable);
                });
    }

    /**
     * 带指数退避的重试
     */
    private Mono<Void> retryWithBackoff(ServerWebExchange exchange,
                                         GatewayFilterChain chain, int retryCount) {
        if (retryCount >= MAX_RETRIES) {
            log.error("已达最大重试次数: {}", MAX_RETRIES);
            return Mono.error(new RuntimeException("服务暂时不可用，请稍后重试"));
        }

        long delay = RETRY_BASE_DELAY_MS * (long) Math.pow(2, retryCount);
        String path = exchange.getRequest().getURI().getPath();

        log.info("第{}次重试，延迟{}ms: path={}", retryCount + 1, delay, path);

        return Mono.delay(Duration.ofMillis(delay))
                .then(chain.filter(exchange)
                        .onErrorResume(e -> retryWithBackoff(exchange, chain, retryCount + 1)));
    }

    /**
     * 判断是否为幂等方法（可安全重试）
     */
    private boolean isRetryableMethod(String method) {
        return "GET".equals(method) || "HEAD".equals(method) || "OPTIONS".equals(method);
    }

    /**
     * 判断是否为可重试异常
     */
    private boolean isRetryableException(Throwable throwable) {
        return throwable instanceof java.net.ConnectException ||
               throwable instanceof java.net.SocketTimeoutException ||
               throwable instanceof java.io.IOException ||
               (throwable.getCause() != null && isRetryableException(throwable.getCause()));
    }

    @Override
    public int getOrder() {
        return -100; // 在限流之后执行
    }
}
