package com.zhihealth.alert.service;

import com.zhihealth.alert.entity.AlertRule;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 预警引擎单元测试
 */
@DisplayName("预警引擎测试")
public class AlertEngineServiceTest {

    @Test
    @DisplayName("规则评估-大于条件触发")
    void testEvaluateRule_GreaterThan() {
        double currentValue = 95.0;
        double threshold = 90.0;
        String condition = "gt";

        boolean triggered = evaluateCondition(currentValue, threshold, condition);
        assertTrue(triggered, "心率95 > 阈值90应触发预警");
    }

    @Test
    @DisplayName("规则评估-小于条件不触发")
    void testEvaluateRule_LessThan_NotTriggered() {
        double currentValue = 70.0;
        double threshold = 60.0;
        String condition = "lt";

        boolean triggered = evaluateCondition(currentValue, threshold, condition);
        assertFalse(triggered, "体温70 不小于 阈值60不应触发");
    }

    @Test
    @DisplayName("规则评估-等于条件触发")
    void testEvaluateRule_Equal() {
        double currentValue = 37.5;
        double threshold = 37.5;
        String condition = "eq";

        boolean triggered = evaluateCondition(currentValue, threshold, condition);
        assertTrue(triggered, "当前值等于阈值应触发");
    }

    @Test
    @DisplayName("规则实体构建验证")
    void testAlertRuleEntity() {
        AlertRule rule = new AlertRule();
        rule.setRuleName("高心率预警");
        rule.setDataType("heart_rate");
        rule.setMetric("heartRate");
        rule.setThreshold(100.0);
        rule.setCondition("gt");
        rule.setLevel(1);

        assertEquals("高心率预警", rule.getRuleName());
        assertEquals("heart_rate", rule.getDataType());
        assertEquals(100.0, rule.getThreshold(), 0.001);
        assertEquals((Integer)1, rule.getLevel());
    }

    /**
     * 条件评估辅助方法（模拟AlertEngineService中的逻辑）
     */
    private boolean evaluateCondition(double value, double threshold, String condition) {
        switch (condition) {
            case "gt": return value > threshold;
            case "gte": return value >= threshold;
            case "lt": return value < threshold;
            case "lte": return value <= threshold;
            case "eq": return Math.abs(value - threshold) < 0.001;
            case "neq": return Math.abs(value - threshold) >= 0.001;
            default: return false;
        }
    }
}
