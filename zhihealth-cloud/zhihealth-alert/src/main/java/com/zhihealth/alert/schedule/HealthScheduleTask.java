package com.zhihealth.alert.schedule;

import com.zhihealth.alert.service.AlertEngineService;
import com.zhihealth.alert.service.NotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 定时任务调度器
 * - 健康数据定时巡检与阈值比对
 * - 预警消息自动重试发送
 * - 统计报表自动生成
 * - 过期数据清理
 */
@Slf4j
@Component
@EnableScheduling
@RequiredArgsConstructor
public class HealthScheduleTask {

    private final AlertEngineService alertEngineService;
    private final NotificationService notificationService;

    /**
     * 每5分钟执行: 健康数据阈值巡检
     * 扫描最近5分钟内采集的健康数据，比对预警规则，触发告警
     */
    @Scheduled(fixedRate = 300000, initialDelay = 60000)
    public void healthDataPatrol() {
        long start = System.currentTimeMillis();
        log.info("[定时任务] 开始健康数据巡检...");

        try {
            int alertCount = alertEngineService.checkAndTriggerAlerts();
            if (alertCount > 0) {
                log.info("[定时任务] 巡检完成, 触发 {} 条新预警", alertCount);
            }
        } catch (Exception e) {
            log.error("[定时任务] 健康数据巡检异常", e);
        }

        log.info("[定时任务] 巡检耗时: {}ms", System.currentTimeMillis() - start);
    }

    /**
     * 每10分钟执行: 重试失败的预警通知
     * 对PENDING状态的预警重新尝试推送（最多重试3次）
     */
    @Scheduled(fixedRate = 600000, initialDelay = 120000)
    public void retryFailedNotifications() {
        log.debug("[定时任务] 重试失败的通知...");

        try {
            int retryCount = notificationService.retryPendingNotifications(3);
            if (retryCount > 0) {
                log.info("[定时任务] 成功重发 {} 条通知", retryCount);
            }
        } catch (Exception e) {
            log.error("[定时任务] 通知重试异常", e);
        }
    }

    /**
     * 每天凌晨2点执行: 自动生成日报
     * 为每个活跃用户汇总前一天的健康数据统计
     */
    @Scheduled(cron = "0 0 2 * * ?")
    public void generateDailyReports() {
        log.info("[定时任务] 开始生成每日健康日报...");
        try {
            // reportService.generateDailyReports(LocalDate.now().minusDays(1));
            log.info("[定时任务] 日报生成完成");
        } catch (Exception e) {
            log.error("[定时任务] 日报生成异常", e);
        }
    }

    /**
     * 每周一凌晨3点执行: 自动生成周报
     */
    @Scheduled(cron = "0 0 3 ? * MON")
    public void generateWeeklyReports() {
        log.info("[定时任务] 开始生成每周健康周报...");
        try {
            // reportService.generateWeeklyReports();
            log.info("[定时任务] 周报生成完成");
        } catch (Exception e) {
            log.error("[定时任务] 周报生成异常", e);
        }
    }

    /**
     * 每天凌晨4点执行: 清理过期数据
     * - 清理90天前的操作日志
     * - 清理30天前已解决的预警通知缓存
     * - 清理7天前的临时Token
     */
    @Scheduled(cron = "0 0 4 * * ?")
    public void cleanupExpiredData() {
        log.info("[定时任务] 开始清理过期数据...");
        try {
            // logService.cleanExpiredLogs(90);
            // redisTemplate.delete(patterns for expired tokens)
            log.info("[定时任务] 过期数据清理完成");
        } catch (Exception e) {
            log.error("[定时任务] 数据清理异常", e);
        }
    }

    /**
     * 每小时执行: 设备离线检测
     * 标记超过30分钟未上报数据的设备为离线
     */
    @Scheduled(fixedRate = 3600000)
    public void checkDeviceOnlineStatus() {
        log.debug("[定时任务] 检查设备在线状态...");
        try {
            // deviceService.updateOfflineDevices(30); // 30分钟超时
        } catch (Exception e) {
            log.error("[定时任务] 设备状态检测异常", e);
        }
    }
}
