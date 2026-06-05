package com.zhihealth.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * 全链路TraceId追踪过滤器
 * - 为每个请求生成唯一TraceId
 * - 透传上游传入的TraceId（支持微服务间链路追踪）
 * - 写入响应头便于前端排查问题
 */
@Slf4j
@Component
public class TraceIdFilter implements GlobalFilter, Ordered {

    /** 请求头：TraceId */
    public static final String TRACE_ID_HEADER = "X-Trace-Id";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String traceId = request.getHeaders().getFirst(TRACE_ID_HEADER);

        // 如果上游未传递TraceId，则生成新的
        if (traceId == null || traceId.isEmpty()) {
            traceId = generateTraceId();
        }

        // 将TraceId添加到请求头，传递给下游服务
        final String finalTraceId = traceId;
        ServerHttpRequest mutatedRequest = request.mutate()
                .header(TRACE_ID_HEADER, finalTraceId)
                .build();

        // 记录日志（配合MDC使用）
        log.info("[TraceId: {}] 请求开始: method={}, path={}",
                finalTraceId,
                request.getMethod(),
                request.getURI().getPath());

        return chain.filter(exchange.mutate().request(mutatedRequest).build())
                .contextWrite(ctx -> ctx.put(TRACE_ID_HEADER, finalTraceId))
                .doFinally(signalType -> log.info("[TraceId: {}] 请求结束: signal={}", finalTraceId, signalType));
    }

    /**
     * 生成唯一TraceId
     * 格式：时间戳后8位 + 随机UUID前8位
     */
    private String generateTraceId() {
        long timestamp = System.currentTimeMillis();
        String uuidPart = UUID.randomUUID().toString().replace("-", "").substring(0, 8);
        return Long.toHexString(timestamp) + "-" + uuidPart;
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE; // 最高优先级，最先执行
    }
}
