"""
移动端专用 API 接口
针对App/小程序优化的轻量级接口集合

特性：
  - 分页优化（默认20条/页，支持游标分页）
  - 数据精简（只返回必要字段）
  - 离线优先（支持增量同步）
  - 带宽友好（支持数据压缩提示）
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import wraps
from flask import Blueprint, request, jsonify, g
import pandas as pd
import numpy as np
from loguru import logger

from .response_format import (
    MobileResponse,
    ResponseCode,
    PaginationMeta,
    OfflineSyncInfo,
    compress_for_mobile
)


def mobile_auth_required(f):
    """移动端认证装饰器（支持Token和离线模式）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        offline_mode = request.headers.get('X-Offline-Mode', 'false').lower() == 'true'
        
        if not auth_header and not offline_mode:
            return jsonify(MobileResponse.error_response(
                ResponseCode.UNAUTHORIZED
            ).to_dict()), 401
        
        # Token验证逻辑
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            # TODO: 调用JWT验证
            try:
                user_context = _verify_mobile_token(token)
                g.mobile_user = user_context
            except Exception as e:
                return jsonify(MobileResponse.error_response(
                    ResponseCode.UNAUTHORIZED
                ).to_dict()), 401
        
        return f(*args, **kwargs)
    return decorated


def rate_limit_for_mobile(max_requests: int = 100, window_seconds: int = 60):
    """移动端限流装饰器（更宽松的限制）"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # TODO: 实现基于用户ID的限流
            return f(*args, **kwargs)
        return wrapped
    return decorator


def create_mobile_blueprint():
    """创建移动端API蓝图"""
    bp = Blueprint('mobile_api', __name__, url_prefix='/api/mobile/v2')
    
    # ==================== 用户相关 ====================
    
    @bp.route('/profile', methods=['GET'])
    @mobile_auth_required
    @rate_limit_for_mobile(60)
    def get_user_profile():
        """
        获取当前用户简要信息（移动端精简版）
        
        Returns:
            200: 用户基本信息
        """
        user_id = getattr(g.mobile_user, 'user_id', None) or request.args.get('uid')
        
        profile_data = {
            'userId': user_id or 'demo_001',
            'nickname': '健康达人',
            'avatar': 'https://api.zhihealth.com/avatars/default.png',
            'healthScore': 85,
            'level': 'Gold',
            'memberSince': '2025-01-15',
            'todayStats': {
                'steps': 8432,
                'calories': 420,
                'sleepHours': 7.5,
                'heartRateAvg': 72
            }
        }
        
        return jsonify(MobileResponse.success_response(
            data=compress_for_mobile(profile_data),
            cache_hint={'max_age': 300, 'revalidate': True}
        ).to_dict())
    
    @bp.route('/dashboard', methods=['GET'])
    @mobile_auth_required
    def get_dashboard_summary():
        """
        移动端首页仪表板（关键指标卡片）
        
        Query Parameters:
            refresh: bool (是否强制刷新缓存)
        
        Returns:
            200: 仪表板数据
        """
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        dashboard = {
            'greeting': _get_greeting(),
            'healthScore': {
                'current': 82,
                'change': '+3',
                'trend': 'up',
                'lastUpdated': datetime.now().strftime('%H:%M')
            },
            'quickMetrics': [
                {'icon': '❤️', 'label': '心率', 'value': '72 bpm', 'status': 'normal'},
                {'icon': '🩸', 'label': '血压', 'value': '120/80', 'status': 'normal'},
                {'icon': '🌡️', 'label': '体温', 'value': '36.6°C', 'status': 'normal'},
                {'icon': '😴', 'label': '睡眠', 'value': '7.5h', 'status': 'good'}
            ],
            'alerts': {
                'unreadCount': 2,
                'latest': [
                    {'id': 'a001', 'type': 'info', 'title': '今日步数目标达成！', 'time': '10分钟前'},
                    {'id': 'a002', 'type': 'warning', 'title': '血压略高，建议监测', 'time': '2小时前'}
                ]
            },
            'weeklyTrend': {
                'labels': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                'heartRate': [72, 75, 71, 73, 74, 70, 72],
                'steps': [8000, 9500, 7200, 11000, 8500, 12000, 8432]
            }
        }
        
        return jsonify(MobileResponse.success_response(
            data=dashboard,
            cache_hint={
                'max_age': 60 if not refresh else 0,
                'etag': f"dash_{datetime.now().strftime('%Y%m%d%H')}"
            }
        ).to_dict())
    
    # ==================== 健康数据查询（移动端优化）====================
    
    @bp.route('/health-data/latest', methods=['GET'])
    @mobile_auth_required
    def get_latest_health_data():
        """
        获取最新健康数据（移动端精简）
        
        Query Parameters:
            types: str (逗号分隔的数据类型，如 heart_rate,blood_pressure)
            limit: int (返回数量，默认10)
        """
        data_types = request.args.get('types', 'heart_rate').split(',')
        limit = min(int(request.args.get('limit', 10)), 50)
        
        # 模拟数据生成
        records = []
        for i in range(limit):
            record = {
                'id': f"rec_{datetime.now().timestamp():.0f}_{i}",
                'time': (datetime.now() - timedelta(minutes=i*30)).isoformat(),
                'metrics': {}
            }
            
            for dtype in data_types[:4]:  # 最多4种类型
                if dtype == 'heart_rate':
                    record['metrics']['hr'] = int(np.random.normal(72, 8))
                elif dtype == 'blood_pressure':
                    record['metrics']['sys'] = int(np.random.normal(120, 12))
                    record['metrics']['dia'] = int(np.random.normal(80, 8))
                elif dtype == 'steps':
                    record['metrics']['steps'] = int(np.random.exponential(3000))
                elif dtype == 'sleep':
                    record['metrics']['duration'] = round(np.random.uniform(6, 9), 1)
                    
            records.append(record)
        
        return jsonify(MobileResponse.success_response(
            data=records,
            cache_hint={'max_age': 30}  # 实时性要求高
        ).to_dict())
    
    @bp.route('/health-data/history', methods=['GET'])
    @mobile_auth_required
    def get_history_paginated():
        """
        分页获取历史健康数据（移动端核心接口）
        
        支持两种分页模式：
          1. 传统分页：page + size
          2. 游标分页：cursor + limit（推荐，性能更好）
        
        Query Parameters:
            page: int (页码，默认1)
            size: int (每页大小，默认20，最大100)
            cursor: str (游标ID，用于下一页)
            start_date: str (开始日期 YYYY-MM-DD)
            end_date: str (结束日期 YYYY-MM-DD)
            data_type: str (数据类型筛选)
        """
        page = int(request.args.get('page', 1))
        size = min(int(request.args.get('size', 20)), 100)
        cursor = request.args.get('cursor')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 模拟总记录数
        total_records = 1258
        items = []
        
        # 生成模拟数据
        start_idx = (page - 1) * size
        for i in range(size):
            idx = start_idx + i
            if idx >= total_records:
                break
                
            items.append({
                'recordId': f"HR_{idx:06d}",
                'collectTime': (datetime.now() - timedelta(hours=idx)).isoformat(),
                'dataType': ['heart_rate', 'blood_pressure', 'steps'][idx % 3],
                'value': round(np.random.uniform(60, 150), 2),
                'unit': ['bpm', 'mmHg', 'count'][idx % 3],
                'isAbnormal': np.random.choice([True, False], p=[0.15, 0.85]),
                'source': 'wearable' if idx % 2 == 0 else 'manual'
            })
        
        response = MobileResponse.paginated_response(
            items=items,
            page=page,
            size=size,
            total=total_records,
            cache_hint={'max_age': 120, 'vary_by': ['data_type']}
        )
        
        # 添加游标信息用于无限滚动
        if len(items) == size:
            response.extra = {
                'next_cursor': f"cursor_{page}_{size}_{items[-1]['recordId']}",
                'has_more': True
            }
        
        return jsonify(response.to_dict())
    
    # ==================== AI分析结果（移动端简化）====================
    
    @bp.route('/ai/risk-assessment', methods=['GET'])
    @mobile_auth_required
    def get_risk_assessment():
        """
        获取AI风险简评（移动端卡片式展示）
        
        Returns:
            200: 风险评估结果（简化版）
        """
        assessment = {
            'overallRisk': {
                'level': 'low',
                'score': 18,
                'maxScore': 100,
                'color': '#52C41A',
                'label': '低风险'
            },
            'riskFactors': [
                {'category': '心血管', 'riskLevel': 'low', 'score': 15, 'icon': '❤️'},
                {'category': '代谢', 'riskLevel': 'medium', 'score': 45, 'icon': '🔥'},
                {'category': '睡眠', 'riskLevel': 'low', 'score': 22, 'icon': '😴'},
                {'category': '运动', 'riskLevel': 'low', 'score': 10, 'icon': '🏃'}
            ],
            'recommendations': [
                '保持当前运动习惯，每周增加1次有氧训练',
                '注意饮食均衡，减少高糖食物摄入',
                '继续保持规律作息时间'
            ],
            'lastAnalysisTime': datetime.now().isoformat(),
            'nextAnalysisDue': (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        return jsonify(MobileResponse.success_response(
            data=assessment,
            cache_hint={'max_age': 3600}  # AI结果可长期缓存
        ).to_dict())
    
    @bp.route('/ai/trend-prediction', methods=['GET'])
    @mobile_auth_required
    def get_trend_prediction():
        """
        获取趋势预测数据（用于图表渲染）
        
        Query Parameters:
            metric: str (预测指标: heart_rate | blood_pressure | weight)
            days: int (预测天数，默认7天)
        """
        metric = request.args.get('metric', 'heart_rate')
        days = min(int(request.args.get('days', 7)), 30)
        
        historical = []
        predicted = []
        
        now = datetime.now()
        for i in range(days * 2):
            date = (now - timedelta(days=(days * 2 - i))).strftime('%Y-%m-%d')
            
            base_value = {
                'heart_rate': 72,
                'blood_pressure_sys': 120,
                'weight': 68.5
            }.get(metric, 70)
            
            value = base_value + np.random.normal(0, base_value * 0.05)
            
            entry = {
                'date': date,
                'value': round(value, 1),
                'type': 'historical' if i < days else 'predicted'
            }
            
            if i < days:
                historical.append(entry)
            else:
                predicted.append(entry)
        
        return jsonify(MobileResponse.success_response(data={
            'metric': metric,
            'unit': {'heart_rate': 'bpm', 'blood_pressure_sys': 'mmHg', 'weight': 'kg'}.get(metric, ''),
            'historical': historical,
            'predicted': predicted,
            'confidence': round(np.random.uniform(0.75, 0.95), 2),
            'modelVersion': 'v2.1-lstm'
        }).to_dict())
    
    # ==================== 离线同步接口 ====================
    
    @bp.route('/sync/pull', methods=['GET'])
    @mobile_auth_required
    def pull_server_changes():
        """
        拉取服务端变更（增量同步）
        
        Headers:
            X-Sync-Token: 上次同步令牌
            X-Last-Sync: 上次同步时间戳
            
        Returns:
            200: 增量数据包
        """
        last_sync_token = request.headers.get('X-Sync-Token')
        last_sync_time = request.headers.get('X-Last-Sync')
        
        # 模拟增量数据
        new_sync_token = OfflineSyncInfo.generate_sync_token(user_id=1)
        
        changes = {
            'updatedRecords': [
                {'id': 'rec_101', 'type': 'health_data', 'updatedAt': datetime.now().isoformat(), 'data': {}},
                {'id': 'alert_005', 'type': 'alert', 'status': 'resolved', 'updatedAt': datetime.now().isoformat()}
            ],
            'newAlerts': [
                {'id': 'alt_new_1', 'level': 'warning', 'title': '血压偏高提醒', 'createdAt': datetime.now().isoformat()}
            ],
            'deletedIds': [],
            'serverTimestamp': datetime.now().isoformat()
        }
        
        sync_info = OfflineSyncInfo(
            last_sync_time=datetime.now().isoformat(),
            pending_count=len(changes['updatedRecords']) + len(changes['newAlerts']),
            conflict_count=0,
            sync_token=new_sync_token
        )
        
        return jsonify(MobileResponse.offline_ready_response(
            data=changes,
            sync_info=sync_info
        ).to_dict())
    
    @bp.route('/sync/push', methods=['POST'])
    @mobile_auth_required
    def push_local_changes():
        """
        推送本地离线数据到服务器
        
        Request Body:
            changes: List[Dict] (变更列表)
                - operation: create | update | delete
                - entityType: health_data | alert_acknowledgment
                - data: Dict
                - localId: str (本地临时ID)
                - clientTimestamp: str
        """
        changes = request.json.get('changes', [])
        
        processed_results = []
        conflicts = []
        
        for change in changes:
            result = {
                'localId': change.get('localId'),
                'operation': change.get('operation'),
                'status': 'success',
                'serverId': f"srv_{hash(change.get('localId', '')) % 100000}"
            }
            
            # 检测冲突（示例：时间戳冲突检测）
            client_ts = change.get('clientTimestamp')
            if client_ts and _has_conflict(change):
                result['status'] = 'conflict'
                conflicts.append(result.copy())
                
            processed_results.append(result)
        
        response = MobileResponse.success_response(
            data={
                'processed': processed_results,
                'conflicts': conflicts,
                'conflictResolutionUrl': '/api/mobile/v2/sync/conflicts' if conflicts else None
            },
            message=f"已处理 {len(processed_results)} 条变更"
        )
        
        if conflicts:
            response.code = ResponseCode.OFFLINE_DATA_CONFLICT.code
            response.message = "部分数据存在冲突，需要解决"
            
        return jsonify(response.to_dict())
    
    # ==================== 设备管理（IoT集成）====================
    
    @bp.route('/devices', methods=['GET'])
    @mobile_auth_required
    def list_connected_devices():
        """列出已连接的智能设备"""
        devices = [
            {
                'deviceId': 'dev_mi_band_001',
                'name': '小米手环8',
                'type': 'fitness_tracker',
                'brand': 'Xiaomi',
                'batteryLevel': 78,
                'lastSync': (datetime.now() - timedelta(minutes=5)).isoformat(),
                'isConnected': True,
                'firmwareVersion': '2.3.1',
                'supportedMetrics': ['heart_rate', 'steps', 'sleep', 'spo2']
            },
            {
                'deviceId': 'dev_bp_monitor_002',
                'name': '欧姆龙血压计',
                'type': 'blood_pressure_monitor',
                'brand': 'Omron',
                'batteryLevel': 92,
                'lastSync': (datetime.now() - timedelta(hours=2)).isoformat(),
                'isConnected': False,
                'firmwareVersion': '1.8.0',
                'supportedMetrics': ['systolic', 'diastolic', 'pulse']
            },
            {
                'deviceId': 'dev_scale_003',
                'name': '华为体脂秤',
                'type': 'smart_scale',
                'brand': 'Huawei',
                'batteryLevel': 65,
                'lastSync': (datetime.now() - timedelta(hours=12)).isoformat(),
                'isConnected': True,
                'firmwareVersion': '3.2.0',
                'supportedMetrics': ['weight', 'body_fat', 'muscle_mass', 'bmi']
            }
        ]
        
        return jsonify(MobileResponse.success_response(
            data=devices,
            cache_hint={'max_age': 60}
        ).to_dict())
    
    @bp.route('/devices/<device_id>/sync', methods=['POST'])
    @mobile_auth_required
    def trigger_device_sync(device_id: str):
        """触发指定设备立即同步数据"""
        return jsonify(MobileResponse.success_response(
            data={
                'deviceId': device_id,
                'syncStatus': 'triggered',
                'estimatedSeconds': 15,
                'message': f'设备 {device_id} 同步任务已触发'
            }
        ).to_dict())


# ==================== 辅助函数 ====================

def _verify_mobile_token(token: str) -> Dict:
    """验证移动端Token（简化实现）"""
    return {
        'user_id': 1,
        'username': 'mobile_user',
        'role': 'user',
        'device_type': request.headers.get('User-Agent', '')[:50]
    }

def _get_greeting() -> str:
    """根据时间段返回问候语"""
    hour = datetime.now().hour
    
    if hour < 6:
        return "夜深了，注意休息哦 🌙"
    elif hour < 12:
        return "早上好！新的一天开始了 ☀️"
    elif hour < 14:
        return "中午好！记得午休一下 🍱"
    elif hour < 18:
        return "下午好！保持活力 💪"
    else:
        return "晚上好！今天辛苦了 🌆"

def _has_conflict(change: Dict) -> bool:
    """检查是否存在数据冲突（模拟）"""
    return np.random.random() < 0.05  # 5%概率模拟冲突


# 全局蓝图实例
_mobile_blueprint = None

def get_mobile_blueprint() -> Blueprint:
    """获取移动端API蓝图"""
    global _mobile_blueprint
    if _mobile_blueprint is None:
        _mobile_blueprint = create_mobile_blueprint()
    return _mobile_blueprint