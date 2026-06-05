package com.zhihealth.alert.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zhihealth.alert.entity.AlertRule;
import com.zhihealth.alert.mapper.AlertRuleMapper;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AlertRuleService extends ServiceImpl<AlertRuleMapper, AlertRule> {

    public Page<AlertRule> getRulesByPage(int pageNum, int pageSize, Long userId) {
        Page<AlertRule> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<AlertRule> wrapper = new LambdaQueryWrapper<>();
        
        if (userId != null) {
            wrapper.eq(AlertRule::getUserId, userId);
        }
        
        wrapper.orderByDesc(AlertRule::getCreateTime);
        return this.page(page, wrapper);
    }

    public List<AlertRule> getEnabledRules() {
        LambdaQueryWrapper<AlertRule> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AlertRule::getEnabled, true);
        return this.list(wrapper);
    }

    public List<AlertRule> getRulesByDataType(String dataType) {
        LambdaQueryWrapper<AlertRule> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AlertRule::getDataType, dataType)
               .eq(AlertRule::getEnabled, true);
        return this.list(wrapper);
    }

    public AlertRule getByRuleCode(String ruleCode) {
        LambdaQueryWrapper<AlertRule> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AlertRule::getRuleCode, ruleCode);
        return this.getOne(wrapper);
    }

    public boolean toggleRuleStatus(Long ruleId, boolean enabled) {
        AlertRule rule = this.getById(ruleId);
        if (rule != null) {
            rule.setEnabled(enabled);
            return this.updateById(rule);
        }
        return false;
    }
}
