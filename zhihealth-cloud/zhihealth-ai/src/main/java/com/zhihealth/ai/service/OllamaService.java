package com.zhihealth.ai.service;

import com.alibaba.fastjson2.JSON;
import lombok.extern.slf4j.Slf4j;
import okhttp3.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class OllamaService {

    @Value("${ollama.url:http://localhost:11434}")
    private String ollamaUrl;

    @Value("${ollama.model:qwen2:7b}")
    private String model;

    @Value("${ollama.timeout:60}")
    private int timeout;

    private final OkHttpClient httpClient = new OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(timeout, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();

    public Map<String, Object> chat(String prompt) {
        Map<String, Object> result = new HashMap<>();

        try {
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", model);
            requestBody.put("prompt", prompt);
            requestBody.put("stream", false);

            String jsonBody = JSON.toJSONString(requestBody);
            RequestBody body = RequestBody.create(
                    jsonBody,
                    MediaType.parse("application/json; charset=utf-8")
            );

            Request request = new Request.Builder()
                    .url(ollamaUrl + "/api/generate")
                    .post(body)
                    .build();

            log.info("调用Ollama大模型: {}", ollamaUrl);

            try (Response response = httpClient.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    String responseBody = response.body().string();
                    Map<String, Object> ollamaResponse = JSON.parseObject(responseBody, Map.class);

                    result.put("success", true);
                    result.put("response", ollamaResponse.get("response"));
                    result.put("model", ollamaResponse.get("model"));
                    result.put("totalDuration", ollamaResponse.get("total_duration"));
                    result.put("promptEvalCount", ollamaResponse.get("eval_count"));
                    result.put("evalCount", ollamaResponse.get("eval_count"));

                    log.info("Ollama大模型响应成功");
                } else {
                    result.put("success", false);
                    result.put("error", "Ollama HTTP请求失败: " + response.code());
                    log.error("Ollama HTTP错误: {}", response.code());
                }
            }

        } catch (IOException e) {
            result.put("success", false);
            result.put("error", "Ollama服务调用异常: " + e.getMessage());
            log.error("Ollama服务调用异常", e);
        }

        return result;
    }

    public Map<String, Object> healthConsultation(String question, Map<String, Object> userContext) {
        StringBuilder promptBuilder = new StringBuilder();
        promptBuilder.append("你是一个专业的健康管理AI助手。请根据用户的健康数据提供专业建议。\n\n");

        if (userContext != null && !userContext.isEmpty()) {
            promptBuilder.append("用户健康数据：\n");
            promptBuilder.append(JSON.toJSONString(userContext));
            promptBuilder.append("\n\n");
        }

        promptBuilder.append("用户问题：").append(question).append("\n\n");
        promptBuilder.append("请用简洁专业的中文回答，包含：\n");
        promptBuilder.append("1. 问题分析\n");
        promptBuilder.append("2. 健康建议\n");
        promptBuilder.append("3. 注意事项\n");
        promptBuilder.append("4. 是否需要就医建议");

        return chat(promptBuilder.toString());
    }

    public Map<String, Object> generateHealthAdvice(Map<String, Object> healthData) {
        StringBuilder promptBuilder = new StringBuilder();
        promptBuilder.append("根据以下健康数据，为用户生成个性化的健康建议：\n\n");
        promptBuilder.append(JSON.toJSONString(healthData));
        promptBuilder.append("\n\n请从以下几个方面给出建议：\n");
        promptBuilder.append("1. 运动建议\n");
        promptBuilder.append("2. 饮食建议\n");
        promptBuilder.append("3. 作息调整\n");
        promptBuilder.append("4. 健康风险提示\n");
        promptBuilder.append("5. 改善目标设定");

        return chat(promptBuilder.toString());
    }

    public boolean isOllamaAvailable() {
        try {
            Request request = new Request.Builder()
                    .url(ollamaUrl + "/api/tags")
                    .get()
                    .build();

            try (Response response = httpClient.newCall(request).execute()) {
                return response.isSuccessful();
            }
        } catch (Exception e) {
            log.warn("Ollama服务不可用: {}", e.getMessage());
            return false;
        }
    }
}
