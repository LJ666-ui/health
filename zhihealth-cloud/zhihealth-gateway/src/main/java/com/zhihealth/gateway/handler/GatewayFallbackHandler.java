package com.zhihealth.gateway.handler;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.web.reactive.error.ErrorWebExceptionHandler;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * 网关降级处理器
 * - 服务熔断/超时时返回友好提示
 * - 统一错误响应格式
 */
@Slf4j
@Component
@Order(-2)
public class GatewayFallbackHandler implements ErrorWebExceptionHandler {

    @Override
    public Mono<Void> handle(ServerWebExchange exchange, Throwable ex) {
        ServerHttpResponse response = exchange.getResponse();
        String path = exchange.getRequest().getURI().getPath();

        // 根据异常类型返回不同的降级响应
        Map<String, Object> result = buildFallbackResponse(path, ex);

        log.warn("网关降级处理: path={}, error={}", path, ex.getMessage());

        byte[] bytes = toJsonBytes(result);
        DataBuffer buffer = response.bufferFactory().wrap(bytes);

        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        response.setStatusCode(HttpStatus.SERVICE_UNAVAILABLE);

        return response.writeWith(Mono.just(buffer));
    }

    /**
     * 构建降级响应（根据不同服务返回差异化提示）
     */
    private Map<String, Object> buildFallbackResponse(String path, Throwable ex) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", 503);
        result.put("data", null);

        String message;

        if (path.contains("/api/ai/")) {
            message = "AI分析服务繁忙，请稍后重试或切换模型";
            result.put("code", 5031);
        } else if (path.contains("/api/storage/")) {
            message = "数据存储服务暂时不可用，数据已缓存稍后同步";
            result.put("code", 5032);
        } else if (path.contains("/api/alert/")) {
            message = "预警服务暂时不可用，请检查设备连接";
            result.put("code", 5033);
        } else if (path.contains("/api/user/")) {
            message = "用户服务暂时不可用，请重新登录";
            result.put("code", 5034);
        } else {
            message = "服务暂时不可用，请稍后重试";
        }

        result.put("msg", message);

        return result;
    }

    private byte[] toJsonBytes(Map<String, Object> data) {
        try {
            return com.alibaba.fastjson2.JSON.toJSONString(data).getBytes(StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "{\"code\":500,\"msg\":\"系统内部错误\"}".getBytes(StandardCharsets.UTF_8);
        }
    }
}
