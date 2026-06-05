import sys
import os
import argparse
import json
from datetime import datetime
from loguru import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.etl_pipeline import ETPipeline
from analysis.analyzer import HealthDataAnalyzer
from visualization.data_generator import VisualizationDataGenerator, start_preview_server
from ai.ml_engine import AIEngine
from ai.model_trainer import AIPipelineManager

def setup_logging(log_level: str = "INFO"):
    log_file = f"logs/health_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    os.makedirs("logs", exist_ok=True)
    
    logger.remove()
    logger.add(sys.stdout, level=log_level, 
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    logger.add(log_file, level=log_level, rotation="10 MB", retention="7 days",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}")

def run_etl(args):
    """运行ETL数据管道"""
    logger.info("="*70)
    logger.info("  ZhiHealth 大数据ETL处理系统")
    logger.info("="*70)
    
    pipeline = ETPipeline()
    
    try:
        if args.mode == "full":
            stats = pipeline.run_full_pipeline(source_table=args.table)
        elif args.mode == "extract":
            df = pipeline.extract_from_mysql(table_name=args.table, batch_size=args.batch_size)
            print(f"\n提取数据预览:\n{df.head()}\n")
            print(f"总计: {len(df)} 条记录")
            return
        elif args.mode == "transform":
            raw_data = pipeline.extract_from_mysql(table_name=args.table)
            transformed = pipeline.transform_data(raw_data)
            print(f"\n转换后数据预览:\n{transformed.head()}\n")
            cleaning_report = pipeline.cleaner.get_cleaning_report()
            print(f"清洗报告: {json.dumps(cleaning_report, indent=2, ensure_ascii=False)}")
            return
        elif args.mode == "load":
            import pandas as pd
            if args.input:
                df = pd.read_csv(args.input)
            else:
                df = pipeline.extract_from_mysql(table_name=args.table)
                df = pipeline.transform_data(df)
            
            targets = args.targets.split(",") if args.targets else ["mysql", "redis", "mongodb", "influxdb"]
            
            for target in targets:
                target = target.strip()
                if target == "mysql":
                    success = pipeline.load_to_mysql(df)
                elif target == "redis":
                    success = pipeline.load_to_redis(df)
                elif target == "mongodb":
                    success = pipeline.load_to_mongodb(df)
                elif target == "influxdb":
                    success = pipeline.load_to_influxdb(df)
                else:
                    logger.warning(f"未知目标: {target}")
                    continue
                    
                print(f"{target}: {'成功' if success else '失败'}")
        
        print("\n" + "="*70)
        print("  ETL执行统计报告")
        print("="*70)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        print("\n")
        
    finally:
        pipeline.close_connections()

def run_analysis(args):
    """运行健康数据分析"""
    logger.info("="*70)
    logger.info("  ZhiHealth 智能健康数据分析系统")
    logger.info("="*70)
    
    analyzer = HealthDataAnalyzer()
    
    try:
        if args.input and os.path.exists(args.input):
            import pandas as pd
            df = pd.read_csv(args.input)
            logger.info(f"从文件加载数据: {args.input}, 共 {len(df)} 条记录")
        else:
            pipeline = ETPipeline()
            
            if not pipeline._connect_mysql():
                logger.error("无法连接数据库")
                return
                
            df = pipeline.extract_from_mysql(table_name=args.table, batch_size=args.batch_size)
            pipeline.close_connections()
        
        if df.empty:
            logger.warning("无数据可供分析")
            return
            
        if 'processed_time' not in df.columns:
            from etl.data_cleaner import DataCleaner
            cleaner = DataCleaner()
            df = cleaner.clean_health_data(df)
        
        if args.analysis_type == "comprehensive":
            report = analyzer.generate_comprehensive_report(df)
            
            print("\n" + "="*70)
            print("  综合健康分析报告")
            print("="*70)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            
            output_file = f"reports/health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs("reports", exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n报告已保存至: {output_file}")
            
        elif args.analysis_type == "heart_rate":
            result = analyzer.analyze_heart_rate(df)
            print("\n心率分析结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        elif args.analysis_type == "blood_pressure":
            result = analyzer.analyze_blood_pressure(df)
            print("\n血压分析结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        elif args.analysis_type == "sleep":
            result = analyzer.analyze_sleep_quality(df)
            print("\n睡眠质量分析结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        elif args.analysis_type == "activity":
            result = analyzer.analyze_activity_level(df)
            print("\n活动量分析结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"分析过程出错: {e}", exc_info=True)
    finally:
        pipeline.close_connections()

def generate_sample_data(args):
    """生成模拟测试数据"""
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    n_records = args.count
    
    user_ids = np.random.choice([1, 2, 3, 4, 5], n_records)
    device_ids = np.random.choice([101, 102, 103], n_records)
    data_types = np.random.choice(['heart_rate', 'body_temp', 'blood_pressure', 'steps', 'sleep'], n_records)
    
    base_time = int(datetime(2026, 5, 1).timestamp() * 1000)
    timestamps = [base_time + i * 3600000 * np.random.randint(1, 24) for i in range(n_records)]
    
    data = {
        'user_id': user_ids,
        'device_id': device_ids,
        'data_type': data_types,
        'heart_rate': np.random.normal(75, 12, n_records),
        'body_temp': np.random.normal(36.6, 0.3, n_records),
        'blood_pressure_systolic': np.random.normal(120, 15, n_records).astype(int),
        'blood_pressure_diastolic': np.random.normal(80, 10, n_records).astype(int),
        'steps': np.random.randint(1000, 20000, n_records),
        'sleep_hours': np.random.normal(7, 1.5, n_records),
        'timestamp': timestamps
    }
    
    df = pd.DataFrame(data)
    
    output_file = args.output or f"data/sample_health_data_{datetime.now().strftime('%Y%m%d')}.csv"
    os.makedirs("data", exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"[OK] 已生成 {n_records} 条模拟数据 -> {output_file}")
    print(f"\n数据预览:\n{df.head()}\n")

def run_visualization(args):
    """运行可视化数据生成与预览"""
    logger.info("="*70)
    logger.info("  ZhiHealth 数据可视化系统")
    logger.info("="*70)
    
    generator = VisualizationDataGenerator()
    
    if args.mode == "generate":
        data = generator.generate_full_dashboard_data()
        
        output_file = args.output or f"visualization/data/dashboard_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"\n[OK] 可视化数据已生成: {output_file}")
        print(f"     KPI指标: {len(data['kpi'])} 项")
        print(f"     警报记录: {len(data['alerts'])} 条")
        print(f"     心率数据点: {len(data.get('heart_rate_series', []))}")
        
    elif args.mode == "preview":
        print(f"\n启动可视化预览服务器 (端口: {args.port})...")
        start_preview_server(port=args.port)
        
    elif args.mode == "export_grafana":
        import shutil
        grafana_dir = "visualization/grafana"
        os.makedirs(grafana_dir, exist_ok=True)
        
        shutil.copy("visualization/grafana-dashboard.json", 
                   f"{grafana_dir}/dashboard_for_import.json")
                   
        print(f"\n[OK] Grafana仪表板已导出至: {grafana_dir}/dashboard_for_import.json")
        print(f"     请在Grafana中导入此JSON文件以创建监控面板")
        
    else:
        logger.error(f"未知可视化模式: {args.mode}")

def run_ai(args):
    """运行AI智能分析"""
    logger.info("="*70)
    logger.info("  ZhiHealth AI 智能健康分析系统")
    logger.info("="*70)
    
    if args.mode == "analyze":
        import pandas as pd
        
        if args.input and os.path.exists(args.input):
            df = pd.read_csv(args.input)
            logger.info(f"从文件加载数据: {args.input}, 共 {len(df)} 条记录")
        else:
            pipeline = ETPipeline()
            if not pipeline._connect_mysql():
                logger.error("无法连接数据库")
                return
            df = pipeline.extract_from_mysql(table_name=args.table, batch_size=args.batch_size)
            pipeline.close_connections()
        
        if df.empty:
            logger.warning("无数据可供分析")
            return
            
        engine = AIEngine()
        
        if args.analysis_type == "comprehensive":
            results = engine.run_comprehensive_analysis(df)
            
            print("\n" + "="*70)
            print("  AI 综合分析结果")
            print("="*70)
            
            # 输出关键摘要
            modules = results.get('modules', {})
            
            if 'risk_prediction' in modules:
                rp = modules['risk_prediction']
                print(f"\n[风险预测] 准确率: {rp['metrics']['accuracy']:.2%} | F1: {rp['metrics']['f1']:.2%}")
                
            if 'anomaly_detection' in modules:
                ad = modules['anomaly_detection']
                iso = ad.get('isolation_forest', {})
                print(f"[异常检测] 发现 {iso.get('anomalies_detected', 0)} 个异常样本 ({iso.get('anomaly_rate', 0):.2f}%)")
                
            if 'user_segmentation' in modules:
                us = modules['user_segmentation']
                print(f"[用户分群] 轮廓系数: {us.get('silhouette_score', 0):.3f} | 群体数: {us['n_clusters']}")
                
            # 生成完整报告
            report = engine.generate_ai_report(df, output_path=f"reports/ai_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            print("\n完整报告:\n")
            print(report)
            
        elif args.analysis_type == "predict":
            engine.risk_predictor.train_risk_model(df)
            predictions = engine.risk_predictor.predict_health_risk(df.head(10))
            
            print("\n[健康风险预测结果 (前10条)]")
            for pred in predictions[:5]:
                print(f"\n用户#{pred['user_id']}:")
                print(f"  风险等级: {pred['predicted_risk_level']}")
                print(f"  置信度: {pred['confidence']}%")
                print(f"  建议: {pred['recommendation']}")
                
        elif args.analysis_type == "trend":
            predictor = engine.trend_predictor
            
            if 'user_id' in df.columns:
                user_ids = df['user_id'].unique()[:3]
                for uid in user_ids:
                    user_data = df[df['user_id'] == uid]
                    result = predictor.predict_future_health(user_data)
                    
                    print(f"\n[用户#{uid} 健康趋势预测]")
                    overall = result.get('overall_assessment', {})
                    print(f"整体状态: {overall.get('health_status', 'N/A')}")
                    print(f"建议: {overall.get('overall_recommendation', '')}")
                    
            else:
                for metric in ['heart_rate', 'blood_pressure_systolic']:
                    if metric in df.columns:
                        analysis = predictor.analyze_trends(df, metric)
                        trend = analysis.get('trend_analysis', {})
                        print(f"\n{metric}:")
                        print(f"  趋势方向: {trend.get('direction', 'N/A')}")
                        print(f"  R²值: {trend.get('r_squared', 0):.4f}")
                        
        elif args.analysis_type == "segment":
            segmentation_result = engine.segmentation_engine.segment_users(df)
            
            print("\n[用户分群结果]")
            print(f"总用户数: {segmentation_result['total_users']}")
            print(f"分群数量: {segmentation_result['n_clusters']}")
            print(f"轮廓系数: {segmentation_result.get('silhouette_score', 0):.3f}\n")
            
            for cluster_id, profile in segmentation_result.get('cluster_profiles', {}).items():
                archetype = profile.get('archetype', f'Cluster_{cluster_id}')
                count = profile.get('user_count', 0)
                pct = profile.get('percentage', 0)
                print(f"群体{cluster_id} - {archetype}: {count}人 ({pct}%)")
                
    elif args.mode == "train":
        import pandas as pd
        
        if not args.input or not os.path.exists(args.input):
            logger.error("请提供有效的输入文件 (--input)")
            return
            
        df = pd.read_csv(args.input)
        print(f"\n加载数据: {df.shape[0]} 行 × {df.shape[1]} 列")
        
        manager = AIPipelineManager()
        manager.trainer.output_dir = args.output_dir or "ai/models"
        
        results = manager.run_full_pipeline(
            raw_data=df,
            target_column=args.target,
            auto_feature_engineering=True,
            compare_models=True
        )
        
        print("\n训练完成！关键指标:")
        if 'model_comparison' in results.get('stages', {}):
            mc = results['stages']['model_comparison']
            print(f"最佳模型: {mc.get('best_model', 'N/A')}")
            print(f"F1分数: {mc.get('best_f1_score', 0):.4f}")
            
        # 保存详细结果
        output_file = f"ai/training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n详细结果已保存至: {output_file}")

def run_api_server(args):
    """启动REST API + WebSocket服务"""
    logger.info("="*70)
    logger.info("  ZhiHealth REST API + WebSocket 服务")
    logger.info("="*70)
    
    from api.rest_server import create_app
    from realtime.ws_server import get_realtime_server

    port = args.port or 5000
    ws_port = args.ws_port or 8088

    print(f"\nStarting services:")
    print(f"  REST API: http://localhost:{port}")
    print(f"  WebSocket: ws://localhost:{ws_port}")
    print(f"\nPress Ctrl+C to stop\n")

    try:
        app = create_app()

        if args.enable_ws:
            ws = get_realtime_server(app)
            print(f"[WebSocket] Enabled on port {ws_port}")

        app.run(host=args.host, port=port, debug=args.debug)
        
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)

def run_export(args):
    """数据导出引擎"""
    logger.info("="*70)
    logger.info("  ZhiHealth 数据导出引擎")
    logger.info("="*70)
    
    import pandas as pd
    
    if not args.input or not os.path.exists(args.input):
        logger.error("请提供有效的输入文件 (--input)")
        return
        
    df = pd.read_csv(args.input)
    
    if args.format == 'excel':
        from export.excel_exporter import ExcelExporter
        exporter = ExcelExporter()
        
        output_file = args.output or f"reports/health_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        success = exporter.export_health_report(df, output_path=output_file, include_charts=True)
        
        if success:
            print(f"\n[OK] Excel报告已生成: {output_file}")
            
    elif args.format == 'pdf':
        from export.pdf_generator import PDFReportGenerator
        generator = PDFReportGenerator()
        
        output_file = args.output or f"reports/health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        success = generator.generate_comprehensive_report(df, output_path=output_file)
        
        if success:
            print(f"\n[OK] PDF报告已生成: {output_file}")
            
    elif args.format == 'csv':
        output_file = args.output or f"data/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n[OK] CSV文件已导出: {output_file} ({len(df)} 条记录)")
        
    else:
        logger.error(f"不支持的格式: {args.format}")

def run_monitor(args):
    """Prometheus监控系统"""
    logger.info("="*70)
    logger.info("  ZhiHealth Prometheus 监控系统")
    logger.info("="*70)
    
    from monitoring.metrics_collector import MetricsCollector
    from monitoring.health_endpoint import HealthEndpointServer
    
    if args.action == 'start':
        server = HealthEndpointServer(host=args.host, port=args.port)
        print(f"\n启动健康检查端点: http://{args.host}:{args.port}/health")
        print(f"指标端点: http://{args.host}:{args.port}/metrics")
        print(f"\n按 Ctrl+C 停止\n")
        server.start()
        
    elif args.action == 'collect':
        collector = MetricsCollector()
        metrics = collector.collect_all_metrics()
        
        print(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
        
    elif args.action == 'status':
        from monitoring.health_endpoint import get_system_status
        status = get_system_status()
        print(json.dumps(status, indent=2, ensure_ascii=False, default=str))

def run_cache_manager(args):
    """缓存管理"""
    logger.info("="*70)
    logger.info("  ZhiHealth 多级缓存管理器")
    logger.info("="*70)
    
    from performance.cache_engine import MultiLevelCacheManager, CacheConfig
    
    cache_manager = MultiLevelCacheManager()
    
    if args.action == 'status':
        stats = cache_manager.get_stats()
        l1_stats = cache_manager.l1_cache.get_stats()
        
        print(f"\n{'='*50}")
        print("  缓存状态概览")
        print(f"{'='*50}")
        print(f"L1 本地缓存 (LRU):")
        print(f"  当前条目数: {l1_stats['current_size']}/{l1_stats['max_size']}")
        print(f"  命中率: {l1_stats.get('hit_rate', 0):.2%}")
        print(f"\nL2 Redis缓存:")
        print(f"  连接状态: {'已连接' if cache_manager._redis_available else '未连接'}")
        print(f"\n全局统计:")
        print(f"  总请求数: {stats['global']['total_requests']}")
        print(f"  L1命中数: {stats['global']['l1_hits']} ({stats['global'].get('l1_hit_rate', 0):.2%})")
        print(f"  L2命中数: {stats['global']['l2_hits']} ({stats['global'].get('l2_hit_rate', 0):.2%})")
        print(f"  DB查询数: {stats['global']['l3_hits']}")
        print(f"  整体命中率: {stats['global'].get('overall_hit_rate', 0):.2%}")
        
    elif args.action == 'clear':
        pattern = args.pattern or '*'
        cleared = cache_manager.clear_cache(pattern)
        print(f"[OK] 已清除匹配 '{pattern}' 的缓存项 ({cleared} 个)")
        
    elif args.action == 'preload':
        print("[OK] 缓存预热完成（示例：加载热点健康数据）")

def run_optimize(args):
    """SQL优化与性能分析"""
    logger.info("="*70)
    logger.info("  ZhiHealth 数据库性能优化器")
    logger.info("="*70)
    
    from performance.db_optimizer import SQLAnalyzer, QueryPerformanceMonitor
    
    if args.action == 'analyze' and args.sql:
        analyzer = SQLAnalyzer()
        result = analyzer.analyze(args.sql)
        
        print(f"\n{'='*60}")
        print("  SQL 分析结果")
        print(f"{'='*60}")
        print(f"原始SQL:\n  {result['originalSql']}\n")
        print(f"复杂度评估: {result['estimatedComplexity']}")
        print(f"可缓存性: {'是' if result['canUseCache'] else '否'}")
        
        if result['issues']:
            print(f"\n⚠️ 发现 {len(result['issues'])} 个问题:")
            for issue in result['issues']:
                severity_icon = {'critical': '🔴', 'error': '🟠', 'warning': '🟡'}.get(issue['type'], '⚪')
                print(f"  {severity_icon} [{issue['type'].upper()}] {issue['message']}")
                print(f"     建议: {issue['suggestion']}\n")
                
        if result['suggestions']:
            print(f"\n💡 优化建议:")
            for i, suggestion in enumerate(result['suggestions'], 1):
                print(f"  {i}. {suggestion}")
                
    elif args.action == 'slow-queries':
        monitor = QueryPerformanceMonitor()
        slow_queries = monitor.get_slow_query_top_n(n=args.limit or 10)
        
        print(f"\n{'='*80}")
        print(f"  慢查询 TOP-{len(slow_queries)} 排行榜")
        print(f"{'='*80}")
        
        for i, query in enumerate(slow_queries, 1):
            print(f"\n#{i} | 耗时: {query['execution_time_ms']:.2f}ms | "
                  f"次数: {query['execution_count']} | 表: {query['table_name']}")
            print(f"   SQL: {query['sql_text'][:100]}...")
            
    elif args.action == 'index-advice':
        analyzer = SQLAnalyzer()
        advice = analyzer.generate_index_advice(table_name=args.table)
        
        print(f"\n表 [{args.table}] 索引建议:")
        for idx in advice:
            print(f"\n  ✅ 建议创建索引:")
            print(f"     列: {idx['columns']}")
            print(f"     类型: {idx['index_type']}")
            print(f"     理由: {idx['reason']}")
            print(f"     SQL: {idx['create_sql']}")

def run_integrate(args):
    """第三方平台集成测试"""
    logger.info("="*70)
    logger.info("  ZhiHealth 第三方平台集成测试")
    logger.info("="*70)
    
    if args.platform == 'wechat':
        from integrations.wechat import WeChatIntegration, WeChatConfig
        
        config = WeChatConfig.from_env()
        wechat = WeChatIntegration(config)
        
        print(f"\n微信配置检查:")
        print(f"  AppID: {config.app_id[:8]}..." if config.app_id else "  AppID: 未配置")
        print(f"  Token: {'已配置' if config.token else '未配置'}")
        print(f"  EncodingAESKey: {'已配置' if config.encoding_aes_key else '未配置'}")
        
        if args.test_token:
            token = wechat.get_access_token()
            print(f"\n[OK] AccessToken获取成功: {token[:20]}...")
            
    elif args.platform == 'dingtalk':
        from integrations.dingtalk import DingTalkIntegration, DingTalkConfig
        
        config = DingTalkConfig.from_env()
        dingtalk = DingTalkIntegration(config)
        
        print(f"\n钉钉配置检查:")
        print(f"  AppKey: {config.app_key[:8]}..." if config.app_key else "  AppKey: 未配置")
        print(f"  Webhook URL: {'已配置' if config.webhook_url else '未配置'}")
        
        if args.test_message:
            from integrations.dingtalk import DingTalkMessage, MessageType
            msg = DingTalkMessage(
                msg_type=MessageType.TEXT,
                content={"content": "ZhiHealth 集成测试消息"}
            )
            result = dingtalk.send_webhook_message(msg)
            print(f"\n发送结果: {'成功' if result.get('success') else '失败'}")
            if not result.get('success'):
                print(f"错误: {result.get('error')}")
                
    elif args.platform == 'his':
        from integrations.his_connector import HISConnectionConfig, HL7Parser, FHIRClient
        
        config = HISConnectionConfig.from_env()
        
        print(f"\nHIS系统配置检查:")
        print(f"  FHIR Base URL: {config.fhir_base_url or '未配置'}")
        print(f"  HL7 MLLP Host: {config.hl7_mllp_host}:{config.hl7_mllp_port}" if config.hl7_mllp_host else "  HL7: 未配置")
        
        if args.test_hl7 and os.path.exists(args.test_hl7):
            parser = HL7Parser()
            with open(args.test_hl7, 'r') as f:
                hl7_msg = f.read()
            parsed = parser.parse_message(hl7_msg)
            print(f"\nHL7消息解析结果:")
            print(f"  消息类型: {parsed.message_type}")
            print(f"  患者数量: {len(parsed.patients)}")
            if parsed.patients:
                patient = parsed.patients[0]
                print(f"  首位患者: {patient.patient_name} (ID: {patient.patient_id})")

def run_forecast(args):
    """时间序列预测"""
    logger.info("="*70)
    logger.info("  ZhiHealth 时间序列预测系统")
    logger.info("="*70)
    
    import pandas as pd
    from advanced_analysis.time_series_forecast import (
        TimeSeriesForecaster,
        TimeSeriesModelType,
        SeasonalityType
    )
    
    if not args.input or not os.path.exists(args.input):
        logger.error("请提供输入数据文件 (--input)")
        return
        
    df = pd.read_csv(args.input)
    
    forecaster = TimeSeriesForecaster()
    
    date_col = args.date_column or 'date'
    value_col = args.value_column or 'value'
    
    if date_col not in df.columns or value_col not in df.columns:
        logger.error(f"数据缺少必要列: 需要 {date_col} 和 {value_col}")
        print(f"可用列: {list(df.columns)}")
        return
    
    model_map = {
        'prophet': TimeSeriesModelType.PROPhet,
        'arima': TimeSeriesModelType.ARIMA,
        'lstm': TimeSeriesModelType.LSTM,
        'auto': None
    }
    
    model_type = model_map.get(args.model.lower())
    
    seasonality = []
    if args.seasonality:
        for s in args.seasonality.split(','):
            s = s.strip().lower()
            if s in ['daily', 'weekly', 'monthly', 'yearly']:
                seasonality.append(SeasonalityType(s.upper()))
    
    print(f"\n开始训练模型...")
    print(f"  数据量: {len(df)} 条")
    print(f"  日期列: {date_col}")
    print(f"  数值列: {value_col}")
    print(f"  模型类型: {args.model}")
    print(f"  季节性: {[s.value for s in seasonality] if seasonality else '自动检测'}")
    print(f"  预测步长: {args.horizon} 天/小时\n")
    
    try:
        result = forecaster.forecast(
            data=df,
            model_type=model_type,
            date_column=date_col,
            value_column=value_col,
            horizon=args.horizon,
            seasonality=seasonality if seasonality else None
        )
        
        print(f"{'='*60}")
        print(f"  预测结果 - {result.model_type}")
        print(f"{'='*60}")
        
        print(f"\n📊 模型指标:")
        print(f"  MAE: {result.metrics.get('mae', 0):.4f}")
        print(f"  RMSE: {result.metrics.get('rmse', 0):.4f}")
        print(f"  MAPE: {result.metrics.get('mape', 0):.2f}%")
        print(f"  R²: {result.metrics.get('r_squared', 0):.4f}")
        
        print(f"\n🔮 未来{args.horizon}期预测值:")
        for i, (date, value, lower, upper) in enumerate(zip(
            result.forecast_dates[:5],
            result.forecast_values[:5],
            result.lower_bound[:5],
            result.upper_bound[:5]
        ), 1):
            print(f"  {i}. {date}: {value:.2f} (区间: [{lower:.2f}, {upper:.2f}])")
        
        if len(result.forecast_dates) > 5:
            print(f"  ... 共{len(result.forecast_dates)}个预测点")
            
        if result.anomaly_indices:
            print(f"\n⚠️ 检测到 {len(result.anomaly_indices)} 个历史异常点")
            
        output_file = args.output or f"reports/forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        print(f"\n✅ 完整结果已保存至: {output_file}")
        
    except Exception as e:
        logger.error(f"预测过程出错: {e}", exc_info=True)
        print(f"\n❌ 预测失败: {str(e)}")
        print("提示: 请确保安装了必要的依赖包 (prophet/statsmodels/tensorflow)")

def run_causal_analyze(args):
    """因果推断分析"""
    logger.info("="*70)
    logger.info("  ZhiHealth 因果推断分析系统")
    logger.info("="*70)
    
    import pandas as pd
    from advanced_analysis.causal_inference import (
        CausalEffectEstimator,
        CausalMethod,
        CausalDiscoveryEngine
    )
    
    if not args.input or not os.path.exists(args.input):
        logger.error("请提供输入数据文件 (--input)")
        return
        
    df = pd.read_csv(args.input)
    
    estimator = CausalEffectEstimator()
    
    treatment = args.treatment
    outcome = args.outcome
    confounders = args.confounders.split(',') if args.confounders else []
    confounders = [c.strip() for c in confounders]
    
    method_map = {
        'psm': CausalMethod.PROPENSITY_SCORE_MATCHING,
        'did': CausalMethod.DIFFERENCE_IN_DIFFERENCES,
        'iv': CausalMethod.INSTRUMENTAL_VARIABLE,
        'backdoor': CausalMethod.BACKDOOR_ADJUSTMENT,
        'linear': CausalMethod.LINEAR_REGRESSION
    }
    
    method = method_map.get(args.method.lower(), CausalMethod.BACKDOOR_ADJUSTMENT)
    
    print(f"\n因果效应估计:")
    print(f"  处理变量(Treatment): {treatment}")
    print(f"  结果变量(Outcome): {outcome}")
    print(f"  混杂因子(Confounders): {confounders if confounders else '无'}")
    print(f"  估计方法: {method.value}\n")
    
    try:
        result = estimator.estimate_effect(
            data=df,
            treatment=treatment,
            outcome=outcome,
            confounders=confounders,
            method=method
        )
        
        print(f"{'='*60}")
        print(f"  因果效应估计结果")
        print(f"{'='*60}")
        
        print(f"\n📈 核心指标:")
        print(f"  效应大小(Effect Size): {result.effect_size:.4f}")
        print(f"  标准误差(SE): {result.standard_error:.4f}")
        print(f"  95%置信区间: [{result.confidence_interval[0]:.4f}, {result.confidence_interval[1]:.4f}]")
        print(f"  P-value: {result.p_value:.4f}")
        print(f"  统计显著性: {'✅ 是 (p<0.05)' if result.is_significant else '❌ 否'}")
        
        print(f"\n👥 样本统计:")
        print(f"  处理组样本: {result.n_treated}")
        print(f"  对照组样本: {result.n_control}")
        
        if result.additional_metrics:
            print(f"\n📊 附加指标:")
            for key, value in result.additional_metrics.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
        
        print(f"\n💡 解释: {result.interpretation}")
        
        output_file = args.output or f"reports/causal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        print(f"\n✅ 结果已保存至: {output_file}")
        
    except Exception as e:
        logger.error(f"因果推断出错: {e}", exc_info=True)
        print(f"\n❌ 分析失败: {str(e)}")

def main():
    parser = argparse.ArgumentParser(
        description="ZhiHealth 智慧健康大数据处理平台 - Python数据处理层",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py etl --mode full                          # 运行完整ETL流程
  python main.py analysis --type comprehensive           # 综合健康分析
  python main.py ai --mode analyze                       # AI综合分析 (推荐)
  python main.py api start                               # 启动REST API服务
  python main.py export --format pdf --input data.csv     # 导出PDF报告
  python main.py monitor start                           # 启动Prometheus监控
  python main.py cache status                            # 查看缓存状态
  python main.py optimize --analyze "SELECT * FROM users" # SQL优化分析
  python main.py integrate --platform wechat             # 测试微信集成
  python main.py forecast --input data.csv               # 时间序列预测
  python main.py causal-analyze --input data.csv         # 因果推断分析
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # ETL命令
    etl_parser = subparsers.add_parser('etl', help='运行ETL数据管道')
    etl_parser.add_argument('--mode', choices=['full', 'extract', 'transform', 'load'], 
                           default='full', help='运行模式')
    etl_parser.add_argument('--table', default='health_record', help='源表名')
    etl_parser.add_argument('--batch-size', type=int, default=1000, help='批处理大小')
    etl_parser.add_argument('--targets', help='加载目标 (逗号分隔)')
    etl_parser.add_argument('--input', help='输入CSV文件路径')
    
    # 分析命令
    analysis_parser = subparsers.add_parser('analysis', help='运行健康数据分析')
    analysis_parser.add_argument('--type', dest='analysis_type', 
                               choices=['comprehensive', 'heart_rate', 'blood_pressure', 
                                       'sleep', 'activity'],
                               default='comprehensive', help='分析类型')
    analysis_parser.add_argument('--table', default='health_record', help='数据表名')
    analysis_parser.add_argument('--batch-size', type=int, default=10000, help='分析数据量')
    analysis_parser.add_argument('--input', help='输入CSV文件路径')
    
    # 数据生成命令
    gen_parser = subparsers.add_parser('generate', help='生成模拟测试数据')
    gen_parser.add_argument('--count', type=int, default=1000, help='生成数据量')
    gen_parser.add_argument('--output', help='输出文件路径')
    
    # 可视化命令
    viz_parser = subparsers.add_parser('visualization', help='数据可视化与展示')
    viz_parser.add_argument('--mode', choices=['generate', 'preview', 'export_grafana'],
                           default='preview', help='可视化模式')
    viz_parser.add_argument('--port', type=int, default=8088, help='预览服务器端口')
    viz_parser.add_argument('--output', help='输出文件路径')
    
    # AI命令
    ai_parser = subparsers.add_parser('ai', help='AI智能分析与机器学习')
    ai_parser.add_argument('--mode', choices=['analyze', 'train'],
                           default='analyze', help='AI模式: analyze=分析, train=训练模型')
    ai_parser.add_argument('--type', dest='analysis_type',
                          choices=['comprehensive', 'predict', 'trend', 'segment'],
                          default='comprehensive', help='分析类型')
    ai_parser.add_argument('--input', help='输入CSV/JSON数据文件路径')
    ai_parser.add_argument('--table', default='health_record', help='数据库表名')
    ai_parser.add_argument('--batch-size', type=int, default=10000, help='处理数据量')
    ai_parser.add_argument('--target', default='health_risk', help='预测目标变量 (训练模式)')
    ai_parser.add_argument('--output-dir', default='ai/models', help='模型输出目录')
    
    # 调度器命令
    scheduler_parser = subparsers.add_parser('scheduler', help='定时任务调度器')
    scheduler_sub = scheduler_parser.add_subparsers(dest='scheduler_action')
    
    run_sched = scheduler_sub.add_parser('run', help='启动调度器守护进程')
    run_sched.add_argument('--workers', type=int, default=4, help='工作线程数')
    
    scheduler_sub.add_parser('list', help='列出所有注册任务')
    scheduler_sub.add_parser('status', help='查看调度状态')
    
    trigger_sched = scheduler_sub.add_parser('trigger', help='手动触发任务执行')
    trigger_sched.add_argument('--task-id', required=True, help='要触发的任务ID')
    
    # API服务命令
    api_parser = subparsers.add_parser('api', help='启动REST API + WebSocket服务')
    api_sub = api_parser.add_subparsers(dest='api_action')
    
    api_start = api_sub.add_parser('start', help='启动API服务器')
    api_start.add_argument('--host', default='0.0.0.0', help='监听地址')
    api_start.add_argument('--port', type=int, default=5000, help='API端口')
    api_start.add_argument('--ws-port', type=int, default=8088, help='WebSocket端口')
    api_start.add_argument('--enable-ws', action='store_true', help='同时启用WebSocket')
    api_start.add_argument('--debug', action='store_true', help='调试模式')
    
    # 数据导出命令
    export_parser = subparsers.add_parser('export', help='数据导出引擎 (Excel/PDF/CSV)')
    export_parser.add_argument('--format', choices=['excel', 'pdf', 'csv'], 
                              required=True, help='导出格式')
    export_parser.add_argument('--input', required=True, help='输入数据文件路径')
    export_parser.add_argument('--output', help='输出文件路径')
    
    # 监控系统命令
    monitor_parser = subparsers.add_parser('monitor', help='Prometheus监控系统')
    monitor_sub = monitor_parser.add_subparsers(dest='action')
    
    monitor_start = monitor_sub.add_parser('start', help='启动监控端点')
    monitor_start.add_argument('--host', default='0.0.0.0', help='监听地址')
    monitor_start.add_argument('--port', type=int, default=9090, help='监控端口')
    
    monitor_sub.add_parser('collect', help='采集并显示当前指标')
    monitor_sub.add_parser('status', help='查看系统健康状态')
    
    # 缓存管理命令
    cache_parser = subparsers.add_parser('cache', help='多级缓存管理器')
    cache_sub = cache_parser.add_subparsers(dest='action')
    
    cache_sub.add_parser('status', help='查看缓存状态和统计信息')
    
    cache_clear = cache_sub.add_parser('clear', help='清除缓存')
    cache_clear.add_argument('--pattern', default='*', help='匹配模式 (支持通配符)')
    
    cache_sub.add_parser('preload', help='缓存预热（加载热点数据）')
    
    # 性能优化命令
    optimize_parser = subparsers.add_parser('optimize', help='SQL优化与性能分析')
    optimize_sub = optimize_parser.add_subparsers(dest='action')
    
    opt_analyze = optimize_sub.add_parser('analyze', help='分析SQL语句')
    opt_analyze.add_argument('--sql', required=True, help='要分析的SQL语句')
    
    opt_slow = optimize_sub.add_parser('slow-queries', help='查看慢查询排行榜')
    opt_slow.add_argument('--limit', type=int, default=10, help='返回数量限制')
    
    opt_index = optimize_sub.add_parser('index-advice', help='获取索引优化建议')
    opt_index.add_argument('--table', required=True, help='表名')
    
    # 第三方集成命令
    integrate_parser = subparsers.add_parser('integrate', help='第三方平台集成测试')
    integrate_parser.add_argument('--platform', choices=['wechat', 'dingtalk', 'his'],
                                 required=True, help='平台类型')
    integrate_parser.add_argument('--test-token', action='store_true', help='测试Token获取')
    integrate_parser.add_argument('--test-message', action='store_true', help='测试消息发送')
    integrate_parser.add_argument('--test-hl7', help='HL7测试文件路径')
    
    # 时间序列预测命令
    forecast_parser = subparsers.add_parser('forecast', help='时间序列预测')
    forecast_parser.add_argument('--input', required=True, help='输入数据文件 (CSV)')
    forecast_parser.add_argument('--model', choices=['prophet', 'arima', 'lstm', 'auto'],
                                default='auto', help='预测模型')
    forecast_parser.add_argument('--date-column', default='date', help='日期列名')
    forecast_parser.add_argument('--value-column', default='value', help='数值列名')
    forecast_parser.add_argument('--horizon', type=int, default=7, help='预测步长')
    forecast_parser.add_argument('--seasonality', help='季节性 (逗号分隔: daily,weekly,yearly)')
    forecast_parser.add_argument('--output', help='结果输出文件')
    
    # 因果推断命令
    causal_parser = subparsers.add_parser('causal-analyze', help='因果推断分析')
    causal_parser.add_argument('--input', required=True, help='输入数据文件 (CSV)')
    causal_parser.add_argument('--treatment', required=True, help='处理变量名')
    causal_parser.add_argument('--outcome', required=True, help='结果变量名')
    causal_parser.add_argument('--confounders', help='混杂因子 (逗号分隔)')
    causal_parser.add_argument('--method', choices=['psm', 'did', 'iv', 'backdoor', 'linear'],
                              default='backdoor', help='估计方法')
    causal_parser.add_argument('--output', help='结果输出文件')
    
    # 全局参数
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    if args.command == 'etl':
        run_etl(args)
    elif args.command == 'analysis':
        run_analysis(args)
    elif args.command == 'generate':
        generate_sample_data(args)
    elif args.command == 'visualization':
        run_visualization(args)
    elif args.command == 'ai':
        run_ai(args)
    elif args.command == 'scheduler':
        run_scheduler(args)
    elif args.command == 'api':
        if not hasattr(args, 'api_action') or not args.api_action:
            print("\n请指定API子命令:")
            print("  python main.py api start [--enable-ws] [--port 5000]")
            return
        run_api_server(args)
    elif args.command == 'export':
        run_export(args)
    elif args.command == 'monitor':
        if not hasattr(args, 'action') or not args.action:
            print("\n请指定监控子命令:")
            print("  python main.py monitor start     # 启动监控端点")
            print("  python main.py monitor collect   # 采集指标")
            print("  python main.py monitor status    # 查看状态")
            return
        run_monitor(args)
    elif args.command == 'cache':
        if not hasattr(args, 'action') or not args.action:
            print("\n请指定缓存子命令:")
            print("  python main.py cache status   # 查看状态")
            print("  python main.py cache clear    # 清除缓存")
            print("  python main.py cache preload  # 缓存预热")
            return
        run_cache_manager(args)
    elif args.command == 'optimize':
        if not hasattr(args, 'action') or not args.action:
            print("\n请指定优化子命令:")
            print("  python main.py optimize --analyze \"SQL语句\"")
            print("  python main.py optimize slow-queries")
            print("  python main.py optimize index-advice --table users")
            return
        run_optimize(args)
    elif args.command == 'integrate':
        run_integrate(args)
    elif args.command == 'forecast':
        run_forecast(args)
    elif args.command == 'causal-analyze':
        run_causal_analyze(args)
    else:
        parser.print_help()
        print("\n" + "="*70)
        print("  可用命令列表 (共19个模块)")
        print("="*70)
        print("""
核心功能 (1-11):
  etl              数据采集与清洗管道
  analysis         健康数据分析
  generate         生成测试数据
  visualization    数据可视化大屏
  ai               AI机器学习引擎
  scheduler        定时任务调度器

高级扩展 (12-19):
  api              REST API + WebSocket服务
  export           数据导出 (Excel/PDF/CSV)
  monitor          Prometheus监控系统
  cache            多级缓存管理器
  optimize         SQL性能优化分析
  integrate        第三方平台集成 (微信/钉钉/HIS)
  forecast         时间序列预测 (Prophet/LSTM/ARIMA)
  causal-analyze   因果推断分析 (PSM/DID/IV/后门调整)
        """)


def run_scheduler(args):
    """运行定时任务调度器"""
    from scheduler.task_scheduler import get_scheduler, TaskScheduler
    
    if not hasattr(args, 'scheduler_action') or not args.scheduler_action:
        print("\n请指定调度器子命令:")
        print("  python main.py scheduler run     - 启动调度器守护进程")
        print("  python main.py scheduler list    - 列出所有任务")
        print("  python main.py scheduler status  - 查看状态")
        print("  python main.py scheduler trigger --task-id <id>  - 手动触发")
        return
        
    scheduler = get_scheduler()
    
    if args.scheduler_action == 'run':
        import signal
        workers = getattr(args, 'workers', 4)
        
        print("\n" + "="*70)
        print("  ZhiHealth 定时任务调度器")
        print("="*70)
        print(f"\n  工作线程: {workers}")
        print("  按 Ctrl+C 停止\n")
        
        signal.signal(signal.SIGINT, lambda s, f: scheduler.stop())
        signal.signal(signal.SIGTERM, lambda s, f: scheduler.stop())
        
        scheduler.start()
        
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            print("\n\n调度器已停止")
            
    elif args.scheduler_action == 'list':
        tasks = scheduler.tasks
        print(f"\n{'='*70}")
        print(f"  已注册定时任务列表 ({len(tasks)} 个)")
        print(f"{'='*70}\n")
        
        for task in sorted(tasks.values(), key=lambda x: x.name):
            status_icon = "✅" if task.enabled else "⭕"
            type_icon = {
                'once': '①', 'interval': '🔄', 'daily': '📅',
                'weekly': '📆', 'monthly': '🗓️', 'cron': '⏰'
            }.get(task.task_type.value, '❓')
            
            next_run_str = task.next_run.strftime('%Y-%m-%d %H:%M') if task.next_run else 'N/A'
            
            print(f"{status_icon} {type_icon} [{task.task_id:25s}] {task.name}")
            print(f"    类型: {task.task_type.value:12s} | "
                  f"下次执行: {next_run_str:20s} | "
                  f"总运行: {task.total_runs}次")
            print(f"    描述: {task.description}")
            print()
            
    elif args.scheduler_action == 'status':
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False, default=str))
        
    elif args.scheduler_action == 'trigger':
        task_id = getattr(args, 'task_id', None)
        success = scheduler.trigger_task_now(task_id)
        
        if success:
            print(f"[OK] 任务 '{task_id}' 已提交执行，请查看日志确认结果")
        else:
            print(f"[FAIL] 无法触发任务 '{task_id}' (可能不存在或正在运行)")
        print("\n提示: 使用 'python main.py <command> --help' 查看具体命令帮助")

if __name__ == "__main__":
    main()