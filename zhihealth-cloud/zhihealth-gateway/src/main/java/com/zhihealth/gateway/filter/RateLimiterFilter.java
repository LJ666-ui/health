package com.zhihealth.gateway.filter;

import com.alibaba.fastjson2.JSON;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class RateLimiterFilter implements GlobalFilter, Ordered {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String RATE_LIMIT_PREFIX = "rate_limit:";
    private static final int DEFAULT_REQUESTS_PER_SECOND = 100;
    private static final int DEFAULT_REQUESTS_PER_MINUTE = 1000;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        String clientIp = getClientIp(request);

        if (isRateLimited(clientIp, path)) {
            log.warn("请求被限流: IP={}, Path={}", clientIp, path);
            return handleRateLimitExceeded(exchange);
        }

        return chain.filter(exchange);
    }

    private boolean isRateLimited(String clientIp, String path) {
        try {
            String key = RATE_LIMIT_PREFIX + clientIp + ":" + path.replace("/", ":");
            
            Long currentCount = redisTemplate.opsForValue().increment(key);
            
            if (currentCount != null && currentCount == 1) {
                redisTemplate.expire(key, Duration.ofMinutes(1));
            }

            int limit = getRateLimitForPath(path);
            
            if (currentCount != null && currentCount > limit) {
                return true;
            }

            return false;
            
        } catch (Exception e) {
            log.error("限流检查异常", e);
            return false;
        }
    }

    private int getRateLimitForPath(String path) {
        if (path.contains("/api/ai/")) {
            return 10;
        } else if (path.contains("/api/collect/")) {
            return 200;
        } else if (path.contains("/api/alert/")) {
            return 50;
        }
        
        return DEFAULT_REQUESTS_PER_MINUTE;
    }

    private Mono<Void> handleRateLimitExceeded(ServerWebExchange exchange) {
        ServerHttpResponse response = exchange.getResponse();
        
        response.setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
        response.getHeaders().add("Content-Type", "application/json; charset=utf-8");

        Map<String, Object> result = new HashMap<>();
        result.put("code", 429);
        result.put("msg", "请求过于频繁，请稍后再试");
        result.put("data", null);

        byte[] bytes = JSON.toJSONString(result).getBytes();

        response.getHeaders().setContentLength(bytes.length);

        return response.writeWith(
                reactor.core.publisher.Mono.just(new org.springframework.core.io.buffer.DefaultDataBufferFactory().wrap(bytes))
        );
    }

    private String getClientIp(ServerHttpRequest request) {
        String xForwardedFor = request.getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }

        String xRealIp = request.getHeaders().getFirst("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }

        return request.getRemoteAddress() != null ? 
               request.getRemoteAddress().getAddress().getHostAddress() : "unknown";
    }

    @Override
    public int getOrder() {
        return -200;
    }
}
