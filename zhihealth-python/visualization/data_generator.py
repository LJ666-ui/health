"""
ZhiHealth 可视化数据生成与预览工具
用于生成ECharts/Grafana所需的JSON数据格式
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List
import http.server
import socketserver
import threading
import webbrowser

class VisualizationDataGenerator:
    """可视化数据生成器"""
    
    def __init__(self):
        self.users = list(range(1001, 1101))  # 100个用户
        self.devices = list(range(2001, 2101))
        
    def generate_heart_rate_timeseries(self, hours: int = 24) -> List[Dict]:
        """生成心率时间序列数据"""
        data = []
        base_time = datetime.now() - timedelta(hours=hours)
        
        for user_id in self.users[:10]:  # 取前10个用户展示
            base_hr = random.randint(65, 85)
            for i in range(hours * 6):  # 每10分钟一个点
                timestamp = base_time + timedelta(minutes=i * 10)
                hr = max(50, min(150, base_hr + int(random.gauss(0, 8))))
                
                if random.random() < 0.02:  # 2%概率异常
                    hr = random.choice([random.randint(45, 52), random.randint(125, 145)])
                
                data.append({
                    "metric": {"user_id": str(user_id), "device": f"device_{random.choice(self.devices)}"},
                    "values": [int(timestamp.timestamp()), hr]
                })
                
        return data
    
    def generate_blood_pressure_data(self, days: int = 7) -> List[Dict]:
        """生成血压趋势数据"""
        data = []
        base_time = datetime.now() - timedelta(days=days)
        
        for day in range(days):
            date = (base_time + timedelta(days=day)).strftime('%Y-%m-%d')
            
            # 收缩压和舒张压（带日间波动）
            sys_base = random.randint(115, 135)
            dia_base = random.randint(72, 88)
            
            for hour in range(24):
                time_str = f"{date} {hour:02d}:00"
                timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                
                # 模拟昼夜节律（早晨和傍晚偏高）
                hour_factor = 1.0
                if 7 <= hour <= 9 or 17 <= hour <= 19:
                    hour_factor = 1.08
                elif 2 <= hour <= 5:
                    hour_factor = 0.92
                
                systolic = int(sys_base * hour_factor + random.gauss(0, 5))
                diastolic = int(dia_base * hour_factor + random.gauss(0, 4))
                
                systolic = max(90, min(200, systolic))
                diastolic = max(55, min(130, diastolic))
                
                data.append({
                    "time": timestamp.isoformat(),
                    "systolic": systolic,
                    "diastolic": diastolic,
                    "pulse": int(systolic - diastolic) // 3 + 60,
                    "measurement_count": random.randint(50, 200)
                })
                
        return data
    
    def generate_health_distribution(self) -> Dict:
        """生成用户健康等级分布"""
        total_users = len(self.users)
        
        distribution = {
            "A": round(total_users * 0.35),
            "B": round(total_users * 0.28),
            "C": round(total_users * 0.20),
            "D": round(total_users * 0.12),
            "E": total_users - round(total_users * 0.35) - round(total_users * 0.28) - 
                 round(total_users * 0.20) - round(total_users * 0.12)
        }
        
        return distribution
    
    def generate_activity_heatmap(self) -> List[List[int]]:
        """生成活动量热力图数据（按小时 x 星期）"""
        heatmap_data = []
        
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        hours = list(range(24))
        
        for day_idx, day in enumerate(weekdays):
            row = []
            for hour in hours:
                # 工作日 vs 周末模式
                is_weekend = day_idx >= 5
                
                if is_weekend:
                    # 周末：活动高峰在上午10-11点和下午3-5点
                    if 10 <= hour <= 11 or 15 <= hour <= 17:
                        activity = random.randint(800, 1200)
                    elif 8 <= hour <= 20:
                        activity = random.randint(400, 700)
                    else:
                        activity = random.randint(50, 200)
                else:
                    # 工作日：通勤时段活动量高
                    if 7 <= hour <= 9 or 17 <= hour <= 19:
                        activity = random.randint(600, 900)
                    elif 12 <= hour <= 13:  # 午休
                        activity = random.randint(100, 300)
                    elif 9 <= hour <= 17:
                        activity = random.randint(300, 600)
                    else:
                        activity = random.randint(20, 150)
                        
                row.append(activity)
            heatmap_data.append(row)
            
        return {
            "data": heatmap_data,
            "x_labels": [f"{h:02d}:00" for h in hours],
            "y_labels": weekdays
        }
    
    def generate_sleep_quality_radar(self) -> Dict:
        """生成睡眠质量雷达图数据"""
        categories = [
            "深睡时长", "浅睡时长", "REM睡眠",
            "入睡速度", "睡眠连续性", "睡眠效率"
        ]
        
        current_values = [
            round(random.uniform(1.5, 2.8), 1),   # 深睡 (目标: 2.5h)
            round(random.uniform(3.5, 4.8), 1),     # 浅睡 (目标: 4.5h)
            round(random.uniform(1.2, 2.0), 1),     # REM (目标: 1.8h)
            round(random.uniform(3.0, 4.8), 1),     # 入睡速度 (分, 目标: <20min)
            round(random.uniform(3.5, 4.9), 1),     # 连续性 (次/夜, 目标: 0-1)
            round(random.uniform(82, 96), 1)        # 效率 (%)
        ]
        
        ideal_values = [2.5, 4.5, 1.8, 4.5, 4.8, 95]
        
        return {
            "categories": categories,
            "current": current_values,
            "ideal": ideal_values
        }
    
    def generate_kpi_metrics(self) -> Dict:
        """生成KPI指标"""
        return {
            "online_users": {
                "value": random.randint(10000, 15000),
                "trend": round(random.uniform(-5, 15), 1),
                "trend_direction": "up" if random.random() > 0.3 else "down"
            },
            "daily_data_volume": {
                "value": random.randint(800000, 1000000),
                "trend": round(random.uniform(10, 30), 1),
                "trend_direction": "up"
            },
            "avg_heart_rate": {
                "value": random.randint(70, 78),
                "trend": round(random.uniform(-2, 2), 1),
                "trend_direction": "stable"
            },
            "active_alerts": {
                "value": random.randint(30, 80),
                "trend": round(random.uniform(-15, 5), 1),
                "trend_direction": "down" if random.random() > 0.4 else "up"
            },
            "device_online_rate": {
                "value": round(random.uniform(92, 98), 1),
                "status": "normal" if random.random() > 0.2 else "warning"
            },
            "etl_latency": {
                "value": round(random.uniform(500, 2500), 0),
                "unit": "ms"
            },
            "data_quality_score": {
                "value": round(random.uniform(92, 99), 1),
                "status": "excellent" if random.random() > 0.3 else "good"
            }
        }
    
    def generate_alerts(self, count: int = 10) -> List[Dict]:
        """生成实时警报列表"""
        alert_types = [
            {
                "type": "critical",
                "severity": "danger",
                "titles": ["高血压危象检测", "体温异常升高", "心率危急值"],
                "color": "#ff4757"
            },
            {
                "type": "warning",
                "severity": "warning",
                "titles": ["心率持续偏高", "血压上升趋势", "活动量骤降"],
                "color": "#ffa502"
            },
            {
                "type": "info",
                "severity": "info",
                "titles": ["设备离线提醒", "数据延迟警告", "用户未上传数据"],
                "color": "#00d4ff"
            }
        ]
        
        alerts = []
        for i in range(count):
            alert_type = random.choice(alert_types)
            user_id = random.choice(self.users)
            title = random.choice(alert_type["titles"])
            
            minutes_ago = random.randint(0, 60)
            time_desc = "刚刚" if minutes_ago < 5 else f"{minutes_ago}分钟前"
            
            alerts.append({
                "id": i + 1,
                "type": alert_type["type"],
                "severity": alert_type["severity"],
                "title": f"用户#{user_id} {title}",
                "time": time_desc,
                "color": alert_type["color"]
            })
            
        alerts.sort(key=lambda x: ["critical", "warning", "info"].index(x["type"]))
        
        return alerts
    
    def generate_full_dashboard_data(self) -> Dict:
        """生成完整的仪表板数据包"""
        return {
            "generated_at": datetime.now().isoformat(),
            "kpi": self.generate_kpi_metrics(),
            "heart_rate_series": self.generate_heart_rate_timeseries(),
            "blood_pressure_trend": self.generate_blood_pressure_data(),
            "health_distribution": self.generate_health_distribution(),
            "activity_heatmap": self.generate_activity_heatmap(),
            "sleep_radar": self.generate_sleep_quality_radar(),
            "alerts": self.generate_alerts()
        }


def start_preview_server(port: int = 8088, directory: str = None):
    """启动本地预览服务器"""
    directory = directory or os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(directory, 'visualization'))
    
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n{'='*60}")
        print(f"  ZhiHealth 可视化大屏预览服务器")
        print(f"{'='*60}")
        print(f"\n  访问地址: http://localhost:{port}")
        print(f"  按 Ctrl+C 停止服务器\n")
        
        try:
            webbrowser.open(f'http://localhost:{port}')
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n服务器已停止")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ZhiHealth 数据可视化工具')
    subparsers = parser.add_subparsers(dest='command')
    
    # 生成数据命令
    gen_parser = subparsers.add_parser('generate', help='生成可视化数据')
    gen_parser.add_argument('--output', default='visualization/data/dashboard_data.json',
                          help='输出文件路径')
    gen_parser.add_argument('--format', choices=['json', 'pretty'], default='json',
                          help='输出格式')
    
    # 预览命令
    preview_parser = subparsers.add_parser('preview', help='启动本地预览服务器')
    preview_parser.add_argument('--port', type=int, default=8088, help='端口号')
    
    args = parser.parse_args()
    
    generator = VisualizationDataGenerator()
    
    if args.command == 'generate':
        data = generator.generate_full_dashboard_data()
        
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.format == 'pretty':
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, default=str)
                
        print(f"[OK] 可视化数据已生成: {args.output}")
        print(f"     KPI指标: {len(data['kpi'])} 项")
        print(f"     警报记录: {len(data['alerts'])} 条")
        
    elif args.command == 'preview':
        start_preview_server(port=args.port)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()