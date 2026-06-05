package com.zhihealth.common.util;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.Data;

@Data
public class PageQuery {
    private Integer pageNum = 1;
    private Integer pageSize = 10;
    private String orderByColumn;
    private boolean isAsc = true;
    
    public <T> Page<T> toPage() {
        if (pageNum < 1) pageNum = 1;
        if (pageSize < 1) pageSize = 10;
        if (pageSize > 100) pageSize = 100;
        
        return new Page<>(pageNum, pageSize);
    }
}
