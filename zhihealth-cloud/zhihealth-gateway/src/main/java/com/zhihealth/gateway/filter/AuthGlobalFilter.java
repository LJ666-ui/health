package com.zhihealth.gateway.filter;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Slf4j
@Component
public class AuthGlobalFilter implements GlobalFilter, Ordered {

    @Value("${jwt.secret:zhihealth-secret-key-2024-for-health-platform-security}")
    private String secret;

    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    // 白名单：无需登录即可访问
    private static final List<String> WHITE_LIST = Arrays.asList(
        "/api/user/login",
        "/api/user/register",
        "/api/user/password/reset"
    );

    // 资源-操作映射（用于权限校验）
    private static final Map<String, String> RESOURCE_ACTION_MAP = new LinkedHashMap<>();
    static {
        // 用户管理
        RESOURCE_ACTION_MAP.put("/api/user/**", "user");
        RESOURCE_ACTION_MAP.put("/api/device/**", "device");
        RESOURCE_ACTION_MAP.put("/api/data/**", "data");
        RESOURCE_ACTION_MAP.put("/api/collect/**", "data");
        RESOURCE_ACTION_MAP.put("/api/storage/**", "data");
        // 告警中心
        RESOURCE_ACTION_MAP.put("/api/alert/**", "alert");
        // AI分析
        RESOURCE_ACTION_MAP.put("/api/ai/**", "ai");
        // 报告中心
        RESOURCE_ACTION_MAP.put("/api/report/**", "report");
        // 系统管理
        RESOURCE_ACTION_MAP.put("/api/settings/**", "settings");
        RESOURCE_ACTION_MAP.put("/api/log/**", "log");
        // 缓存
        RESOURCE_ACTION_MAP.put("/api/cache/**", "cache");
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        String method = request.getMethod().name();

        // 白名单放行
        if (isWhiteList(path)) {
            return chain.filter(exchange);
        }

        // 提取Token
        String token = extractToken(request);
        if (token == null) {
            return unauthorized(exchange, "未登录或Token已过期");
        }

        try {
            Claims claims = parseToken(token);

            Long userId = Long.parseLong(claims.getSubject());
            String username = claims.get("username", String.class);

            // 将用户信息注入请求头，传递给下游服务
            ServerHttpRequest newRequest = request.mutate()
                    .header("X-User-Id", String.valueOf(userId))
                    .header("X-Username", username)
                    .build();

            log.debug("用户[{}]访问[{} {}]", username, method, path);

            return chain.filter(exchange.mutate().request(newRequest).build());

        } catch (Exception e) {
            log.error("JWT解析失败: {}", e.getMessage());
            return unauthorized(exchange, "无效的Token");
        }
    }

    /**
     * 根据HTTP方法和路径推断操作类型
     */
    private String inferAction(String method, String path) {
        switch (method.toUpperCase()) {
            case "GET":
                if (path.contains("/list") || path.contains("/page")) return "view";
                if (path.contains("/export") || path.contains("/download")) return "export";
                return "view";
            case "POST":
                if (path.contains("/generate") || path.contains("/create")) return "create";
                if (path.contains("/import")) return "import";
                if (path.contains("/analyze") || path.contains("/predict")) return "analyze";
                if (path.contains("/handle") || path.contains("/resolve")) return "handle";
                return "create";
            case "PUT":
            case "PATCH":
                return "update";
            case "DELETE":
                return "delete";
            default:
                return "view";
        }
    }

    /**
     * 匹配路径对应的资源编码
     */
    private String matchResourceCode(String path) {
        for (Map.Entry<String, String> entry : RESOURCE_ACTION_MAP.entrySet()) {
            if (pathMatcher.match(entry.getKey(), path)) {
                return entry.getValue();
            }
        }
        return null;
    }

    private boolean isWhiteList(String path) {
        return WHITE_LIST.stream().anyMatch(pattern -> pathMatcher.match(pattern, path));
    }

    private String extractToken(ServerHttpRequest request) {
        String token = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (token != null && token.startsWith("Bearer ")) {
            return token.substring(7);
        }
        return null;
    }

    private Claims parseToken(String token) {
        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        return Jwts.parserBuilder()
                .setSigningKey(key)
                .build()
                .parseClaimsJws(token)
                .getBody();
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        String body = "{\"code\":401,\"message\":\"" + message + "\",\"data\":null}";
        DataBuffer buffer = response.bufferFactory().wrap(body.getBytes(StandardCharsets.UTF_8));

        return response.writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
