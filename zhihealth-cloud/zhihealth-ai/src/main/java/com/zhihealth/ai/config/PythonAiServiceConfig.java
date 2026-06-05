package com.zhihealth.ai.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "python-ai-service")
public class PythonAiServiceConfig {
    
    private String url = "http://localhost:5000";
    
    private int timeout = 30;
}
