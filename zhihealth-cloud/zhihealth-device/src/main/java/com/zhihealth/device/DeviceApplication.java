package com.zhihealth.device;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@EnableDiscoveryClient
@MapperScan("com.zhihealth.device.mapper")
@ComponentScan(basePackages = {"com.zhihealth.device", "com.zhihealth.common"})
public class DeviceApplication {
    public static void main(String[] args) {
        SpringApplication.run(DeviceApplication.class, args);
        System.out.println("============================================");
        System.out.println("   ZhiHealth Device Service Started! Port: 8082");
        System.out.println("============================================");
    }
}
