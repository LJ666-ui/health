package com.zhihealth.user;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@EnableDiscoveryClient
@MapperScan("com.zhihealth.user.mapper")
@ComponentScan(basePackages = {"com.zhihealth.user", "com.zhihealth.common"})
public class UserApplication {
    public static void main(String[] args) {
        SpringApplication.run(UserApplication.class, args);
        System.out.println("============================================");
        System.out.println("   智康云枢 - 用户权限服务启动成功！端口: 8081");
        System.out.println("============================================");
    }
}
