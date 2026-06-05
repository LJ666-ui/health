import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from loguru import logger
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class HealthDataAnalyzer:
    def __init__(self):
        self.scaler = StandardScaler()
        self.analysis_results = {}

    def analyze_heart_rate(self, df: pd.DataFrame) -> Dict:
        if 'heart_rate' not in df.columns or df['heart_rate'].isna().all():
            return {"error": "无心率数据"}
            
        hr_data = df['heart_rate'].dropna()
        
        result = {
            "basic_stats": {
                "mean": round(hr_data.mean(), 2),
                "median": round(hr_data.median(), 2),
                "std": round(hr_data.std(), 2),
                "min": float(hr_data.min()),
                "max": float(hr_data.max())
            },
            "health_assessment": self._assess_heart_health(hr_data),
            "trend_analysis": self._analyze_trend(hr_data),
            "anomaly_detection": self._detect_anomalies(df, ['heart_rate'])
        }
        
        logger.info(f"心率分析完成: {result['basic_stats']}")
        return result

    def analyze_blood_pressure(self, df: pd.DataFrame) -> Dict:
        if 'blood_pressure_systolic' not in df.columns or 'blood_pressure_diastolic' not in df.columns:
            return {"error": "无血压数据"}
            
        sys_data = df['blood_pressure_systolic'].dropna()
        dia_data = df['blood_pressure_diastolic'].dropna()
        
        result = {
            "systolic_stats": {
                "mean": round(sys_data.mean(), 2),
                "median": round(sys_data.median(), 2),
                "std": round(sys_data.std(), 2)
            },
            "diastolic_stats": {
                "mean": round(dia_data.mean(), 2),
                "median": round(dia_data.median(), 2),
                "std": round(dia_data.std(), 2)
            },
            "classification": self._classify_blood_pressure(
                sys_data.mean(), dia_data.mean()
            ),
            "risk_assessment": self._assess_bp_risk(
                sys_data.mean(), dia_data.mean()
            ),
            "anomaly_detection": self._detect_anomalies(
                df, ['blood_pressure_systolic', 'blood_pressure_diastolic']
            )
        }
        
        logger.info(f"血压分析完成: 收缩压={result['systolic_stats']['mean']}, 舒张压={result['diastolic_stats']['mean']}")
        return result

    def analyze_sleep_quality(self, df: pd.DataFrame) -> Dict:
        if 'sleep_hours' not in df.columns or df['sleep_hours'].isna().all():
            return {"error": "无睡眠数据"}
            
        sleep_data = df['sleep_hours'].dropna()
        
        result = {
            "basic_stats": {
                "avg_sleep_hours": round(sleep_data.mean(), 2),
                "median_sleep": round(sleep_data.median(), 2),
                "std": round(sleep_data.std(), 2)
            },
            "sleep_quality_score": self._calculate_sleep_quality(sleep_data),
            "sleep_pattern": self._analyze_sleep_pattern(sleep_data),
            "recommendations": self._generate_sleep_recommendations(sleep_data.mean())
        }
        
        logger.info(f"睡眠分析完成: 平均睡眠={result['basic_stats']['avg_sleep_hours']}小时")
        return result

    def analyze_activity_level(self, df: pd.DataFrame) -> Dict:
        if 'steps' not in df.columns or df['steps'].isna().all():
            return {"error": "无步数数据"}
            
        steps_data = df['steps'].dropna()
        
        result = {
            "basic_stats": {
                "total_steps": int(steps_data.sum()),
                "avg_daily_steps": round(steps_data.mean(), 2),
                "max_steps": int(steps_data.max()),
                "min_steps": int(steps_data.min())
            },
            "activity_level": self._classify_activity(steps_data.mean()),
            "weekly_trend": self._calculate_weekly_trend(df),
            "goal_achievement": self._check_step_goal(steps_data, goal=10000)
        }
        
        logger.info(f"活动量分析完成: 日均步数={result['basic_stats']['avg_daily_steps']}")
        return result

    def _assess_heart_health(self, hr_series: pd.Series) -> Dict:
        avg_hr = hr_series.mean()
        
        if avg_hr < 60:
            status = "偏低"
            risk = "低"
            description = "心率偏低，可能是运动员或心动过缓"
        elif avg_hr <= 100:
            status = "正常"
            risk = "正常"
            description = "心率在正常范围内"
        else:
            status = "偏高"
            risk = "中高"
            description = "心率偏高，建议关注心脏健康"
            
        return {
            "status": status,
            "risk_level": risk,
            "avg_heart_rate": round(avg_hr, 2),
            "description": description
        }

    def _analyze_trend(self, data: pd.Series) -> Dict:
        if len(data) < 3:
            return {"trend": "insufficient_data", "direction": "unknown"}
            
        recent = data.tail(7).mean() if len(data) >= 7 else data.tail(len(data)).mean()
        earlier = data.head(max(1, len(data)-7)).mean() if len(data) > 7 else data.head(1).mean()
        
        change_percent = ((recent - earlier) / earlier * 100) if earlier != 0 else 0
        
        if change_percent > 5:
            trend = "上升"
            direction = "increasing"
        elif change_percent < -5:
            trend = "下降"
            direction = "decreasing"
        else:
            trend = "稳定"
            direction = "stable"
            
        return {
            "trend": trend,
            "direction": direction,
            "change_percent": round(change_percent, 2)
        }

    def _detect_anomalies(self, df: pd.DataFrame, columns: List[str]) -> Dict:
        available_cols = [col for col in columns if col in df.columns]
        
        if not available_cols:
            return {"anomalies_found": 0, "details": []}
            
        clean_data = df[available_cols].dropna()
        
        if len(clean_data) < 10:
            return {"anomalies_found": 0, "details": [], "note": "数据不足，跳过异常检测"}
            
        try:
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            predictions = iso_forest.fit_predict(clean_data)
            
            anomaly_indices = np.where(predictions == -1)[0]
            anomalies = []
            
            for idx in anomaly_indices[:10]:
                anomaly_record = clean_data.iloc[idx].to_dict()
                anomalies.append({
                    "index": int(idx),
                    "values": {k: round(v, 2) if isinstance(v, (int, float)) else v 
                              for k, v in anomaly_record.items()}
                })
                
            return {
                "anomalies_found": len(anomaly_indices),
                "anomaly_rate": f"{len(anomaly_indices)/len(clean_data)*100:.2f}%",
                "sample_anomalies": anomalies
            }
            
        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return {"anomalies_found": 0, "error": str(e)}

    def _classify_blood_pressure(self, systolic: float, diastolic: float) -> Dict:
        if systolic < 120 and diastolic < 80:
            category = "正常血压"
            level = 1
        elif systolic < 130 and diastolic < 80:
            category = "血压升高"
            level = 2
        elif systolic < 140 or diastolic < 90:
            category = "高血压一期"
            level = 3
        elif systolic < 180 or diastolic < 120:
            category = "高血压二期"
            level = 4
        else:
            category = "高血压危象"
            level = 5
            
        return {
            "category": category,
            "level": level,
            "systolic": round(systolic, 2),
            "diastolic": round(diastolic, 2)
        }

    def _assess_bp_risk(self, systolic: float, diastolic: float) -> Dict:
        risk_factors = []
        risk_score = 0
        
        if systolic >= 140:
            risk_factors.append("收缩压偏高")
            risk_score += 2
        if diastolic >= 90:
            risk_factors.append("舒张压偏高")
            risk_score += 2
        if systolic - diastolic > 60:
            risk_factors.append("脉压差过大")
            risk_score += 1
            
        if risk_score == 0:
            risk_level = "低风险"
        elif risk_score <= 2:
            risk_level = "中等风险"
        elif risk_score <= 4:
            risk_level = "高风险"
        else:
            risk_level = "极高风险"
            
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "recommendation": self._get_bp_recommendation(risk_level)
        }

    def _get_bp_recommendation(self, risk_level: str) -> str:
        recommendations = {
            "低风险": "保持健康生活方式，定期监测血压",
            "中等风险": "注意饮食，减少盐分摄入，增加运动",
            "高风险": "建议咨询医生，可能需要药物治疗",
            "极高风险": "请立即就医，需要专业医疗干预"
        }
        return recommendations.get(risk_level, "请咨询医生")

    def _calculate_sleep_quality(self, sleep_data: pd.Series) -> Dict:
        avg_sleep = sleep_data.mean()
        
        if 7 <= avg_sleep <= 9:
            score = 95
            quality = "优秀"
        elif 6.5 <= avg_sleep < 7 or 9 < avg_sleep <= 10:
            score = 80
            quality = "良好"
        elif 6 <= avg_sleep < 6.5 or 10 < avg_sleep <= 11:
            score = 65
            quality = "一般"
        else:
            score = 40
            quality = "较差"
            
        consistency = 100 - (sleep_data.std() / avg_sleep * 100) if avg_sleep > 0 else 0
        consistency = max(0, min(100, consistency))
        
        final_score = (score + consistency) / 2
        
        return {
            "score": round(final_score, 1),
            "quality_level": quality,
            "consistency_score": round(consistency, 1),
            "description": self._get_sleep_description(quality)
        }

    def _get_sleep_description(self, quality: str) -> str:
        descriptions = {
            "优秀": "睡眠质量非常好，保持规律作息",
            "良好": "睡眠质量较好，可适当优化睡眠习惯",
            "一般": "睡眠质量一般，建议改善睡眠环境",
            "较差": "睡眠质量较差，强烈建议调整作息并咨询医生"
        }
        return descriptions.get(quality, "未知")

    def _analyze_sleep_pattern(self, sleep_data: pd.Series) -> Dict:
        weekend_avg = sleep_data[sleep_data.index % 7 >= 5].mean() if len(sleep_data) > 7 else sleep_data.mean()
        weekday_avg = sleep_data[sleep_data.index % 7 < 5].mean() if len(sleep_data) > 7 else sleep_data.mean()
        
        diff = abs(weekend_avg - weekday_avg)
        
        if diff < 0.5:
            pattern = "规律"
        elif diff < 1.5:
            pattern = "轻微波动"
        else:
            pattern = "不规律"
            
        return {
            "pattern": pattern,
            "weekday_avg": round(weekday_avg, 2),
            "weekend_avg": round(weekend_avg, 2),
            "difference": round(diff, 2)
        }

    def _generate_sleep_recommendations(self, avg_sleep: float) -> List[str]:
        recommendations = []
        
        if avg_sleep < 6:
            recommendations.append("严重睡眠不足，建议每晚保证7-9小时睡眠")
            recommendations.append("避免睡前使用电子设备")
            recommendations.append("建立固定的作息时间")
        elif avg_sleep < 7:
            recommendations.append("轻度睡眠不足，建议适当延长睡眠时间")
            recommendations.append("尝试放松技巧如冥想或深呼吸")
        elif avg_sleep > 10:
            recommendations.append("睡眠时间过长，可能影响精神状态")
            recommendations.append("建议设置固定起床时间")
        else:
            recommendations.append("睡眠时间合理，继续保持良好习惯")
            
        return recommendations

    def _classify_activity(self, avg_steps: float) -> Dict:
        if avg_steps < 5000:
            level = "久坐少动"
            health_impact = "不良"
        elif avg_steps < 7500:
            level = "轻度活跃"
            health_impact = "一般"
        elif avg_steps < 10000:
            level = "中度活跃"
            health_impact = "良好"
        else:
            level = "高度活跃"
            health_impact = "优秀"
            
        return {
            "level": level,
            "health_impact": health_impact,
            "avg_daily_steps": round(avg_steps, 2)
        }

    def _calculate_weekly_trend(self, df: pd.DataFrame) -> Dict:
        if 'timestamp' not in df.columns or 'steps' not in df.columns:
            return {"trend": "insufficient_data"}
            
        try:
            df_copy = df.copy()
            df_copy['date'] = pd.to_datetime(df_copy['timestamp'], unit='ms')
            daily_steps = df_copy.groupby(df_copy['date'].dt.date)['steps'].mean()
            
            if len(daily_steps) >= 7:
                recent_week = daily_steps.tail(7)
                prev_week = daily_steps.iloc[-14:-7] if len(daily_steps) >= 14 else daily_steps.head(min(7, len(daily_steps)))
                
                change = ((recent_week.mean() - prev_week.mean()) / prev_week.mean() * 100) \
                    if prev_week.mean() != 0 else 0
                    
                return {
                    "trend": "上升" if change > 5 else ("下降" if change < -5 else "稳定"),
                    "change_percent": round(change, 2),
                    "recent_week_avg": round(recent_week.mean(), 2)
                }
            else:
                return {"trend": "insufficient_data", "message": "数据不足一周"}
                
        except Exception as e:
            logger.error(f"周趋势计算失败: {e}")
            return {"trend": "error", "message": str(e)}

    def _check_step_goal(self, steps_data: pd.Series, goal: int = 10000) -> Dict:
        achieved_days = (steps_data >= goal).sum()
        total_days = len(steps_data)
        achievement_rate = (achieved_days / total_days * 100) if total_days > 0 else 0
        
        return {
            "goal": goal,
            "achieved_days": int(achieved_days),
            "achievement_rate": round(achievement_rate, 2),
            "status": "excellent" if achievement_rate >= 80 else 
                       ("good" if achievement_rate >= 60 else "needs_improvement")
        }

    def generate_comprehensive_report(self, df: pd.DataFrame) -> Dict:
        report = {
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_summary": {
                "total_records": len(df),
                "date_range": self._get_date_range(df),
                "unique_users": df['user_id'].nunique() if 'user_id' in df.columns else 0
            },
            "analysis": {
                "heart_rate": self.analyze_heart_rate(df),
                "blood_pressure": self.analyze_blood_pressure(df),
                "sleep_quality": self.analyze_sleep_quality(df),
                "activity_level": self.analyze_activity_level(df)
            },
            "overall_health_score": self._calculate_overall_score(df),
            "recommendations": self._generate_overall_recommendations(df)
        }
        
        self.analysis_results = report
        logger.info("综合健康分析报告生成完成")
        return report

    def _get_date_range(self, df: pd.DataFrame) -> Dict:
        if 'timestamp' not in df.columns:
            return {"start": "N/A", "end": "N/A"}
            
        timestamps = pd.to_datetime(df['timestamp'], unit='ms')
        return {
            "start": timestamps.min().strftime('%Y-%m-%d') if not timestamps.empty else "N/A",
            "end": timestamps.max().strftime('%Y-%m-%d') if not timestamps.empty else "N/A"
        }

    def _calculate_overall_score(self, df: pd.DataFrame) -> Dict:
        scores = []
        
        hr_result = self.analyze_heart_rate(df)
        if "health_assessment" in hr_result:
            hr_score = 100 if hr_result["health_assessment"]["risk_level"] == "正常" else \
                      70 if hr_result["health_assessment"]["risk_level"] == "低" else 40
            scores.append(("heart_rate", hr_score))
            
        bp_result = self.analyze_blood_pressure(df)
        if "risk_assessment" in bp_result:
            bp_scores = {"低风险": 90, "中等风险": 70, "高风险": 50, "极高风险": 30}
            bp_score = bp_scores.get(bp_result["risk_assessment"]["risk_level"], 50)
            scores.append(("blood_pressure", bp_score))
            
        sleep_result = self.analyze_sleep_quality(df)
        if "sleep_quality_score" in sleep_result:
            scores.append(("sleep_quality", sleep_result["sleep_quality_score"]["score"]))
            
        activity_result = self.analyze_activity_level(df)
        if "activity_level" in activity_result:
            activity_scores = {"久坐少动": 30, "轻度活跃": 50, "中度活跃": 75, "高度活跃": 95}
            activity_score = activity_scores.get(activity_result["activity_level"]["level"], 50)
            scores.append(("activity_level", activity_score))
            
        if scores:
            overall = sum(score for _, score in scores) / len(scores)
        else:
            overall = 50
            
        return {
            "overall_score": round(overall, 1),
            "component_scores": dict(scores),
            "grade": "A" if overall >= 85 else ("B" if overall >= 70 else ("C" if overall >= 55 else "D"))
        }

    def _generate_overall_recommendations(self, df: pd.DataFrame) -> List[str]:
        recommendations = []
        
        hr_result = self.analyze_heart_rate(df)
        if "health_assessment" in hr_result and hr_result["health_assessment"]["risk_level"] != "正常":
            recommendations.append("关注心率变化，建议定期进行心电图检查")
            
        bp_result = self.analyze_blood_pressure(df)
        if "risk_assessment" in bp_result and bp_result["risk_assessment"]["risk_level"] != "低风险":
            recommendations.append(bp_result["risk_assessment"]["recommendation"])
            
        sleep_result = self.analyze_sleep_quality(df)
        if "recommendations" in sleep_result:
            recommendations.extend(sleep_result["recommendations"][:2])
            
        activity_result = self.analyze_activity_level(df)
        if "activity_level" in activity_result and activity_result["activity_level"]["level"] in ["久坐少动", "轻度活跃"]:
            recommendations.append("增加日常活动量，目标每天至少8000步")
            
        if not recommendations:
            recommendations.append("整体健康状况良好，继续保持健康的生活方式")
            
        return recommendations