package com.zhihealth.device.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zhihealth.common.exception.BusinessException;
import com.zhihealth.common.util.PageQuery;
import com.zhihealth.device.entity.DeviceInfo;
import com.zhihealth.device.mapper.DeviceInfoMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class DeviceInfoService extends ServiceImpl<DeviceInfoMapper, DeviceInfo> {
    
    private final RedisTemplate<String, Object> redisTemplate;
    
    public DeviceInfo addDevice(DeviceInfo device) {
        LambdaQueryWrapper<DeviceInfo> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(DeviceInfo::getSerialNumber, device.getSerialNumber());
        if (this.count(wrapper) > 0) {
            throw new BusinessException("Device serial number already exists");
        }
        
        device.setStatus(1);
        this.save(device);
        return device;
    }
    
    public void updateDevice(Long id, DeviceInfo updateDevice) {
        DeviceInfo device = this.getById(id);
        if (device == null) {
            throw new BusinessException("Device not found");
        }
        
        if (updateDevice.getDeviceName() != null) {
            device.setDeviceName(updateDevice.getDeviceName());
        }
        if (updateDevice.getDeviceType() != null) {
            device.setDeviceType(updateDevice.getDeviceType());
        }
        if (updateDevice.getDeviceModel() != null) {
            device.setDeviceModel(updateDevice.getDeviceModel());
        }
        if (updateDevice.getLocation() != null) {
            device.setLocation(updateDevice.getLocation());
        }
        if (updateDevice.getFirmwareVersion() != null) {
            device.setFirmwareVersion(updateDevice.getFirmwareVersion());
        }
        
        this.updateById(device);
    }
    
    public void deleteDevice(Long id) {
        DeviceInfo device = this.getById(id);
        if (device == null) {
            throw new BusinessException("Device not found");
        }
        
        this.removeById(id);
        redisTemplate.delete("device:online:" + id);
    }
    
    public Page<DeviceInfo> getDeviceList(PageQuery pageQuery, String deviceType, Integer status, Long userId) {
        Page<DeviceInfo> page = pageQuery.toPage();
        LambdaQueryWrapper<DeviceInfo> wrapper = new LambdaQueryWrapper<>();
        
        if (deviceType != null && !deviceType.isEmpty()) {
            wrapper.eq(DeviceInfo::getDeviceType, deviceType);
        }
        if (status != null) {
            wrapper.eq(DeviceInfo::getStatus, status);
        }
        if (userId != null) {
            wrapper.eq(DeviceInfo::getUserId, userId);
        }
        
        wrapper.orderByDesc(DeviceInfo::getCreateTime);
        return this.page(page, wrapper);
    }
    
    public DeviceInfo getDeviceDetail(Long id) {
        DeviceInfo device = this.getById(id);
        if (device == null) {
            throw new BusinessException("Device not found");
        }
        return device;
    }
    
    public void bindDevice(Long deviceId, Long userId) {
        DeviceInfo device = this.getById(deviceId);
        if (device == null) {
            throw new BusinessException("Device not found");
        }
        
        if (device.getUserId() != null && !device.getUserId().equals(userId)) {
            throw new BusinessException("Device already bound to another user");
        }
        
        device.setUserId(userId);
        this.updateById(device);
    }
    
    public void unbindDevice(Long deviceId, Long userId) {
        DeviceInfo device = this.getById(deviceId);
        if (device == null) {
            throw new BusinessException("Device not found");
        }
        
        if (!userId.equals(device.getUserId())) {
            throw new BusinessException("You are not the owner of this device");
        }
        
        device.setUserId(null);
        this.updateById(device);
    }
    
    public void heartbeat(Long deviceId) {
        DeviceInfo device = this.getById(deviceId);
        if (device == null) {
            throw new BusinessException("Device not found");
        }
        
        device.setStatus(1);
        this.updateById(device);
        
        redisTemplate.opsForValue().set(
                "device:online:" + deviceId,
                System.currentTimeMillis(),
                5,
                TimeUnit.MINUTES
        );
    }
    
    public Map<String, Object> getStatistics() {
        Map<String, Object> stats = new HashMap<>();
        
        long totalDevices = this.count();
        long onlineDevices = 0;
        
        List<DeviceInfo> devices = this.list();
        for (DeviceInfo device : devices) {
            Boolean isOnline = redisTemplate.hasKey("device:online:" + device.getId());
            if (Boolean.TRUE.equals(isOnline)) {
                onlineDevices++;
            }
        }
        
        stats.put("totalDevices", totalDevices);
        stats.put("onlineDevices", onlineDevices);
        stats.put("offlineDevices", totalDevices - onlineDevices);
        stats.put("onlineRate", totalDevices > 0 ? (double) onlineDevices / totalDevices * 100 : 0);
        
        return stats;
    }
}
