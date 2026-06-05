package com.zhihealth.report;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
@MapperScan("com.zhihealth.report.mapper")
public class ReportApplication {
    
    public static void main(String[] args) {
        SpringApplication.run(ReportApplication.class, args);
        System.out.println("========================================");
        System.out.println("   健康报告服务启动成功！端口: 8088");
        System.out.println("========================================");
    }
}
