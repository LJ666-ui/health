package com.zhihealth.common.interceptor;

import com.zhihealth.common.annotation.Idempotent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * 幂等性校验拦截器
 * - 校验请求头中的幂等Token
 * - Token一次性使用，消费后立即删除
 * - 支持基于参数的严格幂等模式
 */
@Slf4j
@Component
public class IdempotentInterceptor implements HandlerInterceptor {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    /** 请求头：幂等Token */
    private static final String IDEMPOTENT_TOKEN_HEADER = "X-Idempotent-Token";

    /** Redis Key前缀 */
    private static final String IDEMPOTENT_KEY_PREFIX = "idempotent:";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        if (!(handler instanceof HandlerMethod)) {
            return true;
        }

        HandlerMethod handlerMethod = (HandlerMethod) handler;
        Idempotent idempotent = handlerMethod.getMethodAnnotation(Idempotent.class);

        if (idempotent == null) {
            return true;
        }

        // 获取Token
        String token = request.getHeader(IDEMPOTENT_TOKEN_HEADER);
        if (token == null || token.isEmpty()) {
            writeResponse(response, 400, "缺少幂等性Token，请先获取");
            return false;
        }

        // 构建Redis Key
        String redisKey = IDEMPOTENT_KEY_PREFIX + token;

        // 检查并消费Token（原子操作）
        Boolean deleted = stringRedisTemplate.delete(redisKey);

        if (Boolean.TRUE.equals(deleted)) {
            log.info("幂等性校验通过: method={}, uri={}, token={}",
                    request.getMethod(), request.getRequestURI(), token);
            return true;
        } else {
            log.warn("重复请求被拦截: method={}, uri={}, token={}",
                    request.getMethod(), request.getRequestURI(), token);
            writeResponse(response, 409, idempotent.message());
            return false;
        }
    }

    /**
     * 生成幂等Token（供Controller调用）
     */
    public static String generateToken(StringRedisTemplate redisTemplate) {
        String token = java.util.UUID.randomUUID().toString().replace("-", "");
        String key = IDEMPOTENT_KEY_PREFIX + token;
        // 默认5分钟过期
        redisTemplate.opsForValue().set(key, "1", 300, java.util.concurrent.TimeUnit.SECONDS);
        return token;
    }

    private void writeResponse(HttpServletResponse response, int code, String message) throws java.io.IOException {
        response.setStatus(code);
        response.setContentType("application/json;charset=UTF-8");
        String body = "{\"code\":" + code + ",\"msg\":\"" + message + "\",\"data\":null}";
        response.getWriter().write(body);
    }
}
