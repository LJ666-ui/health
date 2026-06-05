"""
ZhiHealth Hive数据仓库调度与管理系统
支持ETL流程自动化、数据质量监控、元数据管理
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger

class HiveWarehouseManager:
    def __init__(self, hive_conf: Dict = None):
        self.hive_conf = hive_conf or {
            "hive_url": "jdbc:hive2://localhost:10000",
            "hive_user": "hive",
            "warehouse_path": "/user/hive/warehouse/zhihealth_warehouse",
            "hdfs_namenode": "hdfs://localhost:9000"
        }
        
        self.etl_scripts = {
            "ddl": "hive/ddl/warehouse_schema.sql",
            "etl": "hive/etl/etl_transform.sql",
            "analysis": "hive/analysis/analysis_queries.sql"
        }
        
    def execute_hive_query(self, query: str, database: str = None) -> Dict:
        """执行Hive HQL查询"""
        try:
            cmd = ["hive", "-e", query]
            
            if database:
                cmd.extend(["--database", database])
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "rows_affected": self._parse_row_count(result.stdout)
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Query execution timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_script_file(self, script_path: str, variables: Dict = None) -> Dict:
        """执行Hive SQL脚本文件"""
        if not os.path.exists(script_path):
            return {"success": False, "error": f"Script file not found: {script_path}"}
            
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if variables:
            for key, value in variables.items():
                content = content.replace(f'${{{key}}}', str(value))
                
        return self.execute_hive_query(content, database="zhihealth_warehouse")
    
    def initialize_warehouse(self) -> Dict:
        """初始化数据仓库（创建所有表结构）"""
        logger.info("开始初始化Hive数据仓库...")
        
        result = self.execute_script_file(self.etl_scripts["ddl"])
        
        if result["success"]:
            logger.info("数据仓库初始化成功！")
        else:
            logger.error(f"数据仓库初始化失败: {result.get('error', 'Unknown error')}")
            
        return result
    
    def run_etl_pipeline(self, batch_date: str = None) -> Dict:
        """运行ETL数据处理管道"""
        batch_date = batch_date or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"开始执行ETL流程，批次日期: {batch_date}")
        
        etl_result = self.execute_script_file(
            self.etl_scripts["etl"],
            {"batch_date": batch_date}
        )
        
        if etl_result["success"]:
            logger.info(f"ETL流程执行完成，处理日期: {batch_date}")
            return {
                **etl_result,
                "batch_date": batch_date,
                "execution_time": datetime.now().isoformat()
            }
        else:
            logger.error(f"ETL流程执行失败: {etl_result.get('error')}")
            return etl_result
    
    def check_data_quality(self, table_name: str, partition: str = None) -> Dict:
        """检查数据质量"""
        quality_checks = {
            "row_count": f"SELECT COUNT(*) as total_rows FROM {table_name}",
            "null_check": f"""
                SELECT 
                    SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_users,
                    SUM(CASE WHEN device_id IS NULL THEN 1 ELSE 0 END) as null_devices
                FROM {table_name}
                WHERE {f"dt='{partition}'" if partition else "1=1"}
            """,
            "duplicate_check": f"""
                SELECT COUNT(*) - COUNT(DISTINCT CONCAT(user_id, '_', timestamp)) as duplicates 
                FROM {table_name}
                WHERE {f"dt='{partition}'" if partition else "1=1"}
            """
        }
        
        results = {}
        for check_name, query in quality_checks.items():
            result = self.execute_hive_query(query)
            results[check_name] = result
            
        return results
    
    def get_table_metadata(self, table_name: str) -> Dict:
        """获取表元数据信息"""
        queries = {
            "table_info": f"DESCRIBE FORMATTED {table_name}",
            "partition_info": f"SHOW PARTITIONS {table_name}",
            "row_count": f"SELECT COUNT(*) as count FROM {table_name}",
            "sample_data": f"SELECT * FROM {table_name} LIMIT 5"
        }
        
        metadata = {}
        for info_type, query in queries.items():
            result = self.execute_hive_query(query)
            metadata[info_type] = result
            
        return metadata
    
    def generate_partition_list(self, days_back: int = 30) -> List[str]:
        """生成分区列表（用于批量处理）"""
        partitions = []
        base_date = datetime.now()
        
        for i in range(days_back):
            date = base_date - timedelta(days=i+1)
            partitions.append(date.strftime('%Y-%m-%d'))
            
        return partitions
    
    def run_incremental_etl(self, start_date: str, end_date: str = None) -> List[Dict]:
        """运行增量ETL处理（支持日期范围）"""
        end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        results = []
        current_date = start_dt
        
        while current_date <= end_dt:
            batch_date = current_date.strftime('%Y-%m-%d')
            result = self.run_etl_pipeline(batch_date)
            result["date"] = batch_date
            results.append(result)
            
            current_date += timedelta(days=1)
            
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"增量ETL完成: {success_count}/{len(results)} 天处理成功")
        
        return results
    
    def export_to_hdfs(self, table_name: str, output_path: str, format_type: str = "orc") -> Dict:
        """导出表数据到HDFS"""
        query = f"""
        INSERT OVERWRITE DIRECTORY '{output_path}'
        ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
        SELECT * FROM {table_name}
        """
        
        return self.execute_hive_query(query)

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ZhiHealth Hive数仓管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 初始化数仓
    init_parser = subparsers.add_parser('init', help='初始化数据仓库')
    
    # 运行ETL
    etl_parser = subparsers.add_parser('etl', help='运行ETL流程')
    etl_parser.add_argument('--date', help='批次日期(YYYY-MM-DD)')
    etl_parser.add_argument('--start', help='开始日期(增量模式)')
    etl_parser.add_argument('--end', help='结束日期(增量模式)')
    
    # 数据质量检查
    qc_parser = subparsers.add_parser('quality', help='数据质量检查')
    qc_parser.add_argument('--table', required=True, help='表名')
    qc_parser.add_argument('--partition', help='分区值')
    
    # 元数据查看
    meta_parser = subparsers.add_parser('meta', help='查看表元数据')
    meta_parser.add_argument('--table', required=True, help='表名')
    
    args = parser.parse_args()
    
    manager = HiveWarehouseManager()
    
    if args.command == 'init':
        result = manager.initialize_warehouse()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.command == 'etl':
        if args.start and args.end:
            results = manager.run_incremental_etl(args.start, args.end)
        elif args.date:
            result = manager.run_etl_pipeline(args.date)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            result = manager.run_etl_pipeline()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    elif args.command == 'quality':
        result = manager.check_data_quality(args.table, args.partition)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.command == 'meta':
        result = manager.get_table_metadata(args.table)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()