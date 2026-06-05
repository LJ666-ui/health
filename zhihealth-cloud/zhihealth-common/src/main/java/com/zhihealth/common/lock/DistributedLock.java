package com.zhihealth.common.lock;

import lombok.extern.slf4j.Slf4j;
import org.redisson.Redisson;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

/**
 * Redisson分布式锁工具类
 * - 可重入锁（防止同一线程死锁）
 * - 看门狗自动续期（默认30秒）
 * - 支持阻塞/非阻塞获取
 * - 支持锁等待超时
 */
@Slf4j
@Component
public class DistributedLock {

    @Autowired
    private RedissonClient redissonClient;

    /** 默认锁等待时间（秒） */
    private static final long DEFAULT_WAIT_TIME = 5;

    /** 默认锁持有时间（秒），-1表示启用看门狗自动续期 */
    private static final long DEFAULT_LEASE_TIME = -1;

    /**
     * 获取分布式锁（阻塞式，使用看门狗）
     *
     * @param lockKey 锁的key
     * @return 是否获取成功
     */
    public boolean lock(String lockKey) {
        return lock(lockKey, DEFAULT_WAIT_TIME, DEFAULT_LEASE_TIME);
    }

    /**
     * 获取分布式锁（指定参数）
     *
     * @param lockKey   锁的key
     * @param waitTime  最大等待时间（秒）
     * @param leaseTime 锁持有时间（秒），-1表示看门狗模式
     * @return 是否获取成功
     */
    public boolean lock(String lockKey, long waitTime, long leaseTime) {
        RLock lock = redissonClient.getLock(lockKey);
        try {
            boolean acquired = lock.tryLock(waitTime, leaseTime, TimeUnit.SECONDS);
            if (acquired) {
                log.debug("获取分布式锁成功: key={}", lockKey);
            } else {
                log.warn("获取分布式锁失败(超时): key={}, waitTime={}s", lockKey, waitTime);
            }
            return acquired;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("获取分布式锁被中断: key={}", lockKey, e);
            return false;
        }
    }

    /**
     * 释放分布式锁
     *
     * @param lockKey 锁的key
     */
    public void unlock(String lockKey) {
        try {
            RLock lock = redissonClient.getLock(lockKey);
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
                log.debug("释放分布式锁: key={}", lockKey);
            }
        } catch (Exception e) {
            log.error("释放分布式锁异常: key={}", lockKey, e);
        }
    }

    /**
     * 执行带锁的操作（自动释放锁，推荐使用）
     *
     * @param lockKey 锁的key
     * @param action  需要执行的逻辑
     * @return 执行结果
     */
    public <T> T executeWithLock(String lockKey, LockAction<T> action) {
        RLock lock = redissonClient.getLock(lockKey);
        try {
            lock.tryLock(DEFAULT_WAIT_TIME, DEFAULT_LEASE_TIME, TimeUnit.SECONDS);
            return action.execute();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("获取锁被中断: " + lockKey, e);
        } catch (Exception e) {
            throw new RuntimeException("执行锁内操作异常: " + lockKey, e);
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    /**
     * 执行带锁的操作（指定等待和持有时间）
     */
    public <T> T executeWithLock(String lockKey, long waitTime, long leaseTime, LockAction<T> action) {
        RLock lock = redissonClient.getLock(lockKey);
        try {
            lock.tryLock(waitTime, leaseTime, TimeUnit.SECONDS);
            return action.execute();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("获取锁被中断: " + lockKey, e);
        } catch (Exception e) {
            throw new RuntimeException("执行锁内操作异常: " + lockKey, e);
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    /**
     * 锁操作函数式接口
     */
    @FunctionalInterface
    public interface LockAction<T> {
        T execute() throws Exception;
    }
}
