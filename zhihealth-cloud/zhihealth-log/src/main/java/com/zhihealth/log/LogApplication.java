package com.zhihealth.log;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
@MapperScan("com.zhihealth.log.mapper")
public class LogApplication {
    
    public static void main(String[] args) {
        SpringApplication.run(LogApplication.class, args);
        System.out.println("========================================");
        System.out.println("   操作日志服务启动成功！端口: 8089");
        System.out.println("========================================");
    }
}
