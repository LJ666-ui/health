package com.zhihealth.log.aspect;

import com.alibaba.fastjson2.JSON;
import com.zhihealth.log.entity.OperationLog;
import com.zhihealth.log.service.LogService;
import javax.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Aspect
@Component
@RequiredArgsConstructor
public class OperationLogAspect {

    private final LogService logService;

    @Pointcut("execution(* com.zhihealth..controller.*.*(..)) && " +
              "!execution(* com.zhihealth.log.controller.*.*(..))")
    public void controllerPointcut() {
    }

    @Around("controllerPointcut()")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();
        
        HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getRequest();
        
        String className = joinPoint.getTarget().getClass().getSimpleName();
        String methodName = joinPoint.getSignature().getName();
        String url = request.getRequestURI();
        String httpMethod = request.getMethod();
        String ipAddress = getClientIpAddress(request);
        String userAgent = request.getHeader("User-Agent");
        
        Object[] args = joinPoint.getArgs();
        String requestParams = getRequestParams(args);
        
        Object result = null;
        String responseResult = "success";
        String errorMessage = null;
        
        try {
            result = joinPoint.proceed();
            
            if (result != null) {
                String resultStr = JSON.toJSONString(result);
                if (resultStr.contains("\"code\":5") || 
                    resultStr.contains("\"code\":4") || 
                    resultStr.contains("\"code\":40") ||
                    resultStr.contains("\"code\":50")) {
                    responseResult = "failed";
                }
            }
            
            return result;
            
        } catch (Exception e) {
            responseResult = "error";
            errorMessage = e.getMessage();
            log.error("接口调用异常: {} {}", url, e.getMessage());
            throw e;
            
        } finally {
            long duration = System.currentTimeMillis() - startTime;
            
            try {
                OperationLog operationLog = new OperationLog();
                
                operationLog.setOperator(getCurrentUser(request));
                operationLog.setOperatorId(getCurrentUserId(request));
                operationLog.setModule(extractModule(className));
                operationLog.setActionType(extractActionType(methodName, httpMethod));
                operationLog.setDescription(buildDescription(className, methodName, args));
                operationLog.setMethod(className + "." + methodName);
                operationLog.setUrl(url);
                operationLog.setRequestMethod(httpMethod);
                operationLog.setRequestParams(requestParams.length() > 2000 ? requestParams.substring(0, 2000) : requestParams);
                operationLog.setResponseData(result != null ? 
                    (JSON.toJSONString(result).length() > 2000 ? JSON.toJSONString(result).substring(0, 2000) : JSON.toJSONString(result)) : null);
                operationLog.setIpAddress(ipAddress);
                operationLog.setUserAgent(userAgent != null && userAgent.length() > 500 ? userAgent.substring(0, 500) : userAgent);
                operationLog.setResult(responseResult);
                operationLog.setDuration(duration);
                operationLog.setErrorMessage(errorMessage != null && errorMessage.length() > 500 ? errorMessage.substring(0, 500) : errorMessage);
                operationLog.setOperateTime(LocalDateTime.now());
                
                logService.saveLogAsync(operationLog);
                
            } catch (Exception e) {
                log.error("保存操作日志异常", e);
            }
        }
    }

    private String getClientIpAddress(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        
        return ip;
    }

    private String getCurrentUser(HttpServletRequest request) {
        String username = request.getHeader("X-Username");
        if (username != null && !username.isEmpty()) {
            return username;
        }
        
        Object principal = request.getUserPrincipal();
        if (principal != null && principal instanceof java.security.Principal) {
            return ((java.security.Principal) principal).getName();
        }
        
        return "系统用户";
    }

    private String getCurrentUserId(HttpServletRequest request) {
        String userId = request.getHeader("X-User-Id");
        return userId != null ? userId : "0";
    }

    private String extractModule(String className) {
        if (className.contains("User")) return "user";
        if (className.contains("Device")) return "device";
        if (className.contains("Collect")) return "collect";
        if (className.contains("Storage")) return "storage";
        if (className.contains("Alert")) return "alert";
        if (className.contains("Ai")) return "ai";
        if (className.contains("Report")) return "report";
        if (className.contains("Cache")) return "cache";
        return "other";
    }

    private String extractActionType(String methodName, String httpMethod) {
        if (methodName.contains("login") || methodName.contains("logout") || methodName.contains("register")) {
            return "auth";
        }
        if (methodName.contains("save") || methodName.contains("add") || methodName.contains("create") || 
            methodName.contains("update") || methodName.contains("delete")) {
            return "data";
        }
        if (methodName.contains("config") || methodName.contains("setting")) {
            return "config";
        }
        if (methodName.contains("export") || methodName.contains("download") || methodName.contains("upload")) {
            return "file";
        }
        
        Map<String, String> methodMap = new HashMap<>();
        methodMap.put("POST", "data");
        methodMap.put("PUT", "data");
        methodMap.put("DELETE", "data");
        methodMap.put("GET", "other");
        
        return methodMap.getOrDefault(httpMethod, "other");
    }

    private String buildDescription(String className, String methodName, Object[] args) {
        StringBuilder desc = new StringBuilder();
        
        if (methodName.contains("login")) {
            desc.append("用户登录系统");
        } else if (methodName.contains("logout")) {
            desc.append("用户退出系统");
        } else if (methodName.contains("register")) {
            desc.append("用户注册账号");
        } else if (methodName.contains("add") || methodName.contains("create") || methodName.contains("save")) {
            desc.append("新增").append(extractEntityName(className));
        } else if (methodName.contains("update") || methodName.contains("edit") || methodName.contains("modify")) {
            desc.append("修改").append(extractEntityName(className));
        } else if (methodName.contains("delete") || methodName.contains("remove")) {
            desc.append("删除").append(extractEntityName(className));
        } else if (methodName.contains("export")) {
            desc.append("导出数据");
        } else if (methodName.contains("import")) {
            desc.append("导入数据");
        } else if (methodName.contains("query") || methodName.contains("list") || methodName.contains("get")) {
            desc.append("查询").append(extractEntityName(className));
        } else {
            desc.append("执行").append(methodName).append("操作");
        }
        
        return desc.toString();
    }

    private String extractEntityName(String className) {
        if (className.contains("User")) return "用户信息";
        if (className.contains("Device")) return "设备信息";
        if (className.contains("HealthData")) return "健康数据";
        if (className.contains("AlertRule") || className.contains("AlertRecord")) return "告警规则/记录";
        if (className.contains("Report")) return "报告";
        return "数据";
    }

    private String getRequestParams(Object[] args) {
        if (args == null || args.length == 0) {
            return "{}";
        }
        
        try {
            Map<String, Object> params = new HashMap<>();
            
            for (Object arg : args) {
                if (arg instanceof MultipartFile) {
                    MultipartFile file = (MultipartFile) arg;
                    params.put("fileName", file.getOriginalFilename());
                    params.put("fileSize", file.getSize());
                    params.put("contentType", file.getContentType());
                } else if (arg instanceof HttpServletRequest) {
                    continue;
                } else if (arg instanceof String || arg instanceof Number || arg instanceof Boolean) {
                    continue;
                } else {
                    params.put(arg.getClass().getSimpleName(), arg);
                }
            }
            
            return JSON.toJSONString(params);
        } catch (Exception e) {
            return "{}";
        }
    }
}
