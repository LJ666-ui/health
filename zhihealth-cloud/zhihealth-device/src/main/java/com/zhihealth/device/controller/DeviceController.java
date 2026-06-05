package com.zhihealth.device.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zhihealth.common.result.Result;
import com.zhihealth.common.util.PageQuery;
import com.zhihealth.device.entity.DeviceInfo;
import com.zhihealth.device.service.DeviceInfoService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/device")
@RequiredArgsConstructor
public class DeviceController {
    
    private final DeviceInfoService deviceInfoService;
    
    @PostMapping
    public Result<DeviceInfo> addDevice(@RequestBody DeviceInfo device) {
        DeviceInfo result = deviceInfoService.addDevice(device);
        return Result.success(result);
    }
    
    @PutMapping("/{id}")
    public Result<Void> updateDevice(@PathVariable Long id, @RequestBody DeviceInfo device) {
        deviceInfoService.updateDevice(id, device);
        return Result.success();
    }
    
    @DeleteMapping("/{id}")
    public Result<Void> deleteDevice(@PathVariable Long id) {
        deviceInfoService.deleteDevice(id);
        return Result.success();
    }
    
    @GetMapping("/list")
    public Result<Page<DeviceInfo>> getDeviceList(PageQuery pageQuery,
                                                   @RequestParam(required = false) String deviceType,
                                                   @RequestParam(required = false) Integer status,
                                                   @RequestParam(required = false) Long userId) {
        Page<DeviceInfo> page = deviceInfoService.getDeviceList(pageQuery, deviceType, status, userId);
        return Result.success(page);
    }
    
    @GetMapping("/{id}")
    public Result<DeviceInfo> getDeviceDetail(@PathVariable Long id) {
        DeviceInfo device = deviceInfoService.getDeviceDetail(id);
        return Result.success(device);
    }
    
    @PostMapping("/{deviceId}/bind")
    public Result<Void> bindDevice(@PathVariable Long deviceId,
                                   @RequestHeader("X-User-Id") Long userId) {
        deviceInfoService.bindDevice(deviceId, userId);
        return Result.success();
    }
    
    @PostMapping("/{deviceId}/unbind")
    public Result<Void> unbindDevice(@PathVariable Long deviceId,
                                     @RequestHeader("X-User-Id") Long userId) {
        deviceInfoService.unbindDevice(deviceId, userId);
        return Result.success();
    }
    
    @PostMapping("/{deviceId}/heartbeat")
    public Result<Void> heartbeat(@PathVariable Long deviceId) {
        deviceInfoService.heartbeat(deviceId);
        return Result.success();
    }
    
    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics() {
        Map<String, Object> stats = deviceInfoService.getStatistics();
        return Result.success(stats);
    }
}
