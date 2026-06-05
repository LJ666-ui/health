package com.zhihealth.cache;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class})
@EnableDiscoveryClient
@EnableScheduling
@ComponentScan(basePackages = {"com.zhihealth.cache", "com.zhihealth.common"})
public class CacheApplication {
    public static void main(String[] args) {
        SpringApplication.run(CacheApplication.class, args);
        System.out.println("============================================");
        System.out.println("   ZhiHealth Cache Service Started! Port: 8085");
        System.out.println("   Redis Cache + InfluxDB Time-Series");
        System.out.println("============================================");
    }
}
