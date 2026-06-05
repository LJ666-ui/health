package com.zhihealth.storage;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@EnableDiscoveryClient
@MapperScan("com.zhihealth.storage.mapper")
@ComponentScan(basePackages = {"com.zhihealth.storage", "com.zhihealth.common"})
public class StorageApplication {
    public static void main(String[] args) {
        SpringApplication.run(StorageApplication.class, args);
        System.out.println("============================================");
        System.out.println("   ZhiHealth Storage Service Started! Port: 8084");
        System.out.println("   Four-Database Architecture: MySQL + Redis + InfluxDB + MongoDB");
        System.out.println("============================================");
    }
}
