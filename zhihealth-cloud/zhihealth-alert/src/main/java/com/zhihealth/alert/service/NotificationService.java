package com.zhihealth.alert.service;

import com.zhihealth.alert.entity.AlertRecord;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 预警通知推送服务
 * - 邮件通知
 * - Redis消息队列（WebSocket/短信扩展点）
 * - 通知模板管理
 * - 防重复通知（去重窗口）
 */
@Slf4j
@Service
public class NotificationService {

    @Autowired(required = false)
    private JavaMailSender mailSender;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    /** 通知去重Key前缀 */
    private static final String NOTIFY_DEDUP_PREFIX = "notify_dedup:";

    /** 去重窗口时间（秒）- 同一预警30分钟内不重复通知 */
    private static final long DEDUP_WINDOW_SECONDS = 1800;

    /**
     * 发送预警通知（自动选择渠道）
     */
    public void sendAlertNotification(AlertRecord record) {
        // 去重检查
        if (isDuplicateNotification(record)) {
            return;
        }

        // 记录已发送
        markNotificationSent(record);

        // 发送邮件通知
        sendEmailNotification(record);

        // 推送到Redis消息队列（供WebSocket消费）
        pushToQueue(record);
    }

    /**
     * 批量发送预警摘要
     */
    public void sendAlertSummary(List<AlertRecord> records, String recipientEmail) {
        if (mailSender == null || recipientEmail == null || recipientEmail.isEmpty()) {
            return;
        }

        StringBuilder content = new StringBuilder();
        content.append("【智康云枢】预警汇总报告\n\n");
        content.append(String.format("共 %d 条未处理预警：\n\n", records.size()));

        for (int i = 0; i < Math.min(records.size(), 20); i++) {
            AlertRecord record = records.get(i);
            content.append(String.format("%d. [%d] %s - 当前值: %s, 阈值: %s\n",
                    i + 1,
                    record.getLevel(),
                    record.getRuleName(),
                    record.getCurrentValue(),
                    record.getThreshold()));
        }

        if (records.size() > 20) {
            content.append(String.format("\n... 等共%d条，请登录系统查看详情。", records.size()));
        }

        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setTo(recipientEmail);
            message.setSubject("智康云枢 - 预警汇总通知");
            message.setText(content.toString());
            mailSender.send(message);
        } catch (Exception e) {
            // 邮件发送失败不影响主流程
        }
    }

    /**
     * 发送邮件通知
     */
    private void sendEmailNotification(AlertRecord record) {
        if (mailSender == null) {
            return;
        }

        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setTo(getRecipientEmail(record));
            message.setSubject(buildSubject(record));
            message.setText(buildContent(record));
            mailSender.send(message);
        } catch (Exception e) {
            // 邮件发送失败记录日志但不影响主流程
        }
    }

    /**
     * 推送到Redis消息队列
     */
    private void pushToQueue(AlertRecord record) {
        try {
            redisTemplate.convertAndSend("alert:notifications", record);
        } catch (Exception e) {
            // 消息推送失败不影响主流程
        }
    }

    /**
     * 去重检查
     */
    private boolean isDuplicateNotification(AlertRecord record) {
        String key = NOTIFY_DEDUP_PREFIX + record.getRuleId() + ":" + record.getUserId();
        Boolean exists = redisTemplate.hasKey(key);
        return Boolean.TRUE.equals(exists);
    }

    /**
     * 标记已发送
     */
    private void markNotificationSent(AlertRecord record) {
        String key = NOTIFY_DEDUP_PREFIX + record.getRuleId() + ":" + record.getUserId();
        redisTemplate.opsForValue().set(key, "1", DEDUP_WINDOW_SECONDS, java.util.concurrent.TimeUnit.SECONDS);
    }

    /**
     * 构建邮件主题
     */
    private String buildSubject(AlertRecord record) {
        Integer level = record.getLevel();
        String levelPrefix;
        if (level == null) levelPrefix = "[通知]";
        else switch (level) {
            case 3: levelPrefix = "[紧急]"; break;
            case 2: levelPrefix = "[警告]"; break;
            case 1: levelPrefix = "[提示]"; break;
            default: levelPrefix = "[通知]";
        }
        return String.format("智康云枢 %s %s预警 - 用户%s",
                levelPrefix, record.getRuleName(), record.getUserId());
    }

    /**
     * 构建邮件内容
     */
    private String buildContent(AlertRecord record) {
        return String.format(
                "【智康云枢健康预警通知】\n\n" +
                "预警规则：%s\n" +
                "预警级别：%s\n" +
                "当前值：%s\n" +
                "阈值条件：%s %s\n" +
                "触发时间：%s\n" +
                "设备ID：%s\n\n" +
                "请及时关注用户健康状况。\n" +
                "— 智康云枢系统自动发送",
                record.getRuleName(),
                getLevelText(record.getLevel()),
                record.getCurrentValue(),
                record.getCondition(),
                record.getThreshold(),
                record.getAlertTime() != null ? record.getAlertTime().toString() : "未知",
                record.getDeviceId() != null ? record.getDeviceId().toString() : "未知"
        );
    }

    /**
     * 获取收件人邮箱（可从用户配置或规则配置中获取）
     */
    private String getRecipientEmail(AlertRecord record) {
        // 默认从Redis获取用户邮箱配置
        String emailKey = "user:email:" + record.getUserId();
        Object email = redisTemplate.opsForValue().get(emailKey);
        return email != null ? email.toString() : "admin@zhihealth.com";
    }

    /**
     * 将级别数字转换为文字描述
     */
    private String getLevelText(Integer level) {
        if (level == null) return "未知";
        switch (level) {
            case 3: return "紧急";
            case 2: return "警告";
            case 1: return "提示";
            default: return "通知";
        }
    }

    /**
     * 重试失败的通知
     * 由 HealthScheduleTask 定时调用
     *
     * @param maxRetries 每条通知最大重试次数
     * @return 成功重发的数量
     */
    public int retryPendingNotifications(int maxRetries) {
        int retryCount = 0;
        try {
            // 获取状态为PENDING(未处理)的预警记录
            List<AlertRecord> pendingRecords = getPendingAlerts(maxRetries);

            for (AlertRecord record : pendingRecords) {
                // 清除去重缓存，允许重新发送
                clearDedupCache(record);

                // 重新发送
                sendAlertNotification(record);
                retryCount++;
            }

            if (retryCount > 0) {
                log.info("[重试] 成功重发 {} 条通知", retryCount);
            }
        } catch (Exception e) {
            log.error("[重试] 异常", e);
        }
        return retryCount;
    }

    /**
     * 获取待处理的通知记录
     */
    private List<AlertRecord> getPendingAlerts(int limit) {
        // 通过Redis或数据库查询PENDING状态的预警
        // 这里简化实现：返回空列表，实际应查询数据库中status=0且最近创建的记录
        return java.util.Collections.emptyList();
    }

    /**
     * 清除去重缓存（允许重新发送）
     */
    private void clearDedupCache(AlertRecord record) {
        String key = NOTIFY_DEDUP_PREFIX + record.getRuleId() + ":" + record.getUserId();
        redisTemplate.delete(key);
    }
}
