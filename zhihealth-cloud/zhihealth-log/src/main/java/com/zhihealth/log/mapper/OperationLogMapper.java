package com.zhihealth.log.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zhihealth.log.entity.OperationLog;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface OperationLogMapper extends BaseMapper<OperationLog> {
}
