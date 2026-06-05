package com.zhihealth.common;

import com.zhihealth.common.result.Result;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 统一响应结果类单元测试
 */
@DisplayName("Result统一响应测试")
public class ResultTest {

    @Test
    @DisplayName("成功响应-无数据")
    void testSuccessWithoutData() {
        Result<Void> result = Result.success();
        assertEquals(200, result.getCode());
        assertNull(result.getData());
    }

    @Test
    @DisplayName("成功响应-带数据")
    void testSuccessWithData() {
        String testData = "test";
        Result<String> result = Result.success(testData);
        assertEquals(200, result.getCode());
        assertEquals("test", result.getData());
    }

    @Test
    @DisplayName("失败响应-带消息")
    void testErrorWithMessage() {
        Result<Void> result = Result.error("操作失败");
        assertEquals(500, result.getCode());
        assertEquals("操作失败", result.getMessage());
    }

    @Test
    @DisplayName("失败响应-自定义错误码")
    void testErrorWithCode() {
        Result<Void> result = Result.error(400, "参数错误");
        assertEquals(400, result.getCode());
        assertEquals("参数错误", result.getMessage());
    }
}
