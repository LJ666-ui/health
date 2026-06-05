"""
PDF 报告生成器
使用 ReportLab 生成专业的健康分析报告
支持：用户健康档案、月度体检报告、异常事件清单
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd
from loguru import logger


class PDFReportGenerator:
    """PDF报告生成引擎"""
    
    def __init__(self):
        self.styles = self._create_custom_styles()
        self.page_size = A4
    
    def _create_custom_styles(self) -> dict:
        """创建自定义样式"""
        styles = getSampleStyleSheet()
        
        # 标题样式
        styles.add(ParagraphStyle(
            name='MainTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1F4E79'),
            alignment=TA_CENTER,
            spaceAfter=20,
            spaceBefore=10
        ))
        
        # 副标题
        styles.add(ParagraphStyle(
            name='SubTitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        
        # 章节标题
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2F5496'),
            spaceBefore=20,
            spaceAfter=12,
            borderPadding=(5, 5, 5, 5),
            leftIndent=0
        ))
        
        # 小节标题
        styles.add(ParagraphStyle(
            name='SubSectionTitle',
            parent=styles['Heading3'],
            fontSize=13,
            textColor=colors.HexColor('#4472C4'),
            spaceBefore=15,
            spaceAfter=8
        ))
        
        # 正文内容
        styles.add(ParagraphStyle(
            name='BodyText',
            parent=styles['Normal'],
            fontSize=10.5,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceBefore=4,
            spaceAfter=8,
            firstLineIndent=0
        ))
        
        # 警告/重要提示文本
        styles.add(ParagraphStyle(
            name='WarningText',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#CC0000'),
            backColor=colors.HexColor('#FFF2CC'),
            borderColor=colors.HexColor('#FFD966'),
            borderWidth=1,
            borderPadding=8,
            spaceBefore=10,
            spaceAfter=10
        ))
        
        # 表格表头样式
        styles.add(ParagraphStyle(
            name='TableHeader',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        return styles
    
    def generate_health_profile_report(self,
                                      user_info: Dict,
                                      health_data: pd.DataFrame,
                                      ai_analysis: Optional[Dict] = None,
                                      output_path: Optional[str] = None) -> Union[str, BytesIO]:
        """
        生成用户健康档案PDF
        
        包含：
          - 封面页（基本信息）
          - 健康数据概览表格
          - AI分析摘要
          - 健康建议列表
          - 异常事件记录
        """
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer if not output_path else output_path,
            pagesize=self.page_size,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # ===== 封面 =====
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("ZhiHealth 智慧健康平台", self.styles['MainTitle']))
        story.append(Paragraph("个人健康档案报告", self.styles['SubTitle']))
        story.append(HRFlowable(width="80%", thickness=2, color=colors.HexColor('#2F5496')))
        story.append(Spacer(1, 0.5*inch))
        
        # 用户基本信息卡片
        user_table_data = [
            ['姓名', user_info.get('real_name', '未知'), '性别', 
             {'男': 'Male', '女': 'Female'}.get(user_info.get('gender', ''), 'Unknown')],
            ['年龄', str(user_info.get('age', 'N/A')), '手机号', 
             self._mask_phone(str(user_info.get('phone', '')))],
            ['档案编号', f"ZHP-{datetime.now().strftime('%Y%m%d')}-{user_info.get('user_id', '0000')}"],
            ['生成日期', datetime.now().strftime('%Y年%m月%d日 %H:%M')],
        ]
        
        user_table = Table(user_table_data, colWidths=[2*cm, 4*cm, 2*cm, 4*cm])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E7E6E6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(user_table)
        
        story.append(PageBreak())
        
        # ===== 健康数据概览 =====
        story.append(Paragraph("📊 健康数据统计概览", self.styles['SectionTitle']))
        
        if not health_data.empty:
            stats = health_data.describe()
            
            overview_data = [
                ['指标名称', '平均值', '最小值', '最大值', '标准差'],
            ]
            
            key_metrics = {
                'heart_rate': '心率(bpm)',
                'blood_pressure_systolic': '收缩压(mmHg)',
                'blood_pressure_diastolic': '舒张压(mmHg)',
                'body_temp': '体温(°C)',
                'steps': '日均步数',
                'sleep_hours': '睡眠时长(h)',
            }
            
            for eng_name, cn_name in key_metrics.items():
                if eng_name in stats.columns:
                    row = [
                        cn_name,
                        f"{stats.loc['mean', eng_name]:.1f}",
                        f"{stats.loc['min', eng_name]:.1f}",
                        f"{stats.loc['max', eng_name]:.1f}",
                        f"{stats.loc['std', eng_name]:.1f}"
                    ]
                    overview_data.append(row)
            
            overview_table = Table(overview_data, colWidths=[3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
            overview_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2F5496')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            ]))
            story.append(overview_table)
        
        story.append(Spacer(1, 0.3*inch))
        
        # ===== AI分析摘要 =====
        if ai_analysis:
            story.append(Paragraph("🤖 AI智能分析结果", self.styles['SectionTitle']))
            
            modules = ai_analysis.get('modules', {})
            
            for mod_name, mod_result in modules.items():
                title_map = {
                    'risk_prediction': '🔴 风险预测评估',
                    'anomaly_detection': '⚠️ 异常检测结果',
                    'user_segmentation': '👥 用户群体画像',
                    'trend_analysis': '📈 健康趋势分析'
                }
                
                story.append(Paragraph(
                    title_map.get(mod_name, mod_name.replace('_', ' ').title()),
                    self.styles['SubSectionTitle']
                ))
                
                # 提取关键信息
                metrics = mod_result.get('metrics', {})
                
                summary_text = ""
                if 'accuracy' in metrics:
                    summary_text += f"模型准确率: <b>{metrics['accuracy']:.1%}</b><br/>"
                if 'risk_distribution' in metrics:
                    dist = metrics['risk_distribution']
                    summary_text += f"风险分布: 低风险{dist.get('low', 0)}人 | "
                    summary_text += f"中风险{dist.get('medium', 0)}人 | "
                    summary_text += f"高风险{dist.get('high', 0)}人<br/>"
                if 'anomaly_count' in metrics:
                    summary_text += f"检测到 <b>{metrics['anomaly_count']}</b> 个异常数据点<br/>"
                    
                if summary_text:
                    story.append(Paragraph(summary_text, self.styles['BodyText']))
                
                # 建议
                recommendations = mod_result.get('recommendations', [])
                if recommendations:
                    story.append(Paragraph("<b>💡 健康建议:</b>", self.styles['BodyText']))
                    for rec in recommendations[:5]:
                        story.append(Paragraph(f"• {rec}", self.styles['BodyText']))
        
        story.append(PageBreak())
        
        # ===== 异常事件记录 =====
        abnormal_records = health_data[health_data.get('is_abnormal', 0) == 1]
        
        if not abnormal_records.empty:
            story.append(Paragraph("🚨 异常数据记录详情", self.styles['SectionTitle']))
            story.append(Paragraph(
                "以下数据被系统标记为异常，建议关注并咨询医生:",
                self.styles['WarningText']
            ))
            
            abnorm_df = abnormal_records.head(20)[['collect_time', 'data_type', 
                                                   'heart_rate', 'body_temp', 
                                                   'is_abnormal']].copy()
            abnorm_df['collect_time'] = abnorm_df['collect_time'].astype(str).str[:19]
            
            abnorm_data = [['时间', '类型', '心率', '体温', '状态']]
            for _, row in abnorm_df.iterrows():
                abnorm_data.append([
                    str(row['collect_time']),
                    str(row['data_type']),
                    f"{row['heart_rate']:.0f}" if pd.notna(row['heart_rate']) else '-',
                    f"{row['body_temp']:.1f}°C" if pd.notna(row['body_temp']) else '-',
                    '⚠️ 异常'
                ])
            
            abnorm_table = Table(abnorm_data, colWidths=[4*cm, 2.5*cm, 2*cm, 2.5*cm, 2*cm])
            abnorm_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFF2CC')),
            ]))
            story.append(abnorm_table)
        
        # ===== 页脚声明 =====
        story.append(Spacer(1, 1*inch))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Paragraph(
            "<i>本报告由 ZhiHealth AI 系统自动生成，仅供参考，不构成医疗诊断建议。"
            "如有健康问题请及时就医。</i>",
            ParagraphStyle(name='Footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))
        
        # 构建文档
        doc.build(story)
        
        if output_path:
            logger.info(f"PDF健康档案已生成: {output_path}")
            return output_path
        else:
            buffer.seek(0)
            return buffer
    
    def generate_monthly_summary(self,
                                monthly_stats: Dict,
                                output_path: Optional[str] = None) -> Union[str, BytesIO]:
        """
        生成月度健康汇总报告
        
        包含：
          - 月度KPI指标
          - 周/日趋势对比
          - 目标达成情况
          - 下月建议
        """
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer if not output_path else output_path,
            pagesize=self.page_size
        )
        
        story = []
        
        # 标题
        story.append(Paragraph(
            f"📋 月度健康监测报告",
            self.styles['MainTitle']
        ))
        story.append(Paragraph(
            f"统计周期: {monthly_stats.get('period', '本月')}",
            self.styles['SubTitle']
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2F5496')))
        story.append(Spacer(1, 0.3*inch))
        
        # KPI卡片区域
        kpis = monthly_stats.get('kpis', [])
        if kpis:
            story.append(Paragraph("📊 关键绩效指标 (KPIs)", self.styles['SectionTitle']))
            
            kpi_data = [['指标名称', '当前值', '目标值', '达成率', '状态']]
            
            for kpi in kpis[:10]:
                target = kpi.get('target', 100)
                actual = kpi.get('value', 0)
                achievement = (actual / target * 100) if target > 0 else 0
                
                status_icon = "✅" if achievement >= 90 else ("⚠️" if achievement >= 70 else "❌")
                
                kpi_data.append([
                    kpi.get('name', ''),
                    str(actual),
                    str(target),
                    f"{achievement:.1f}%",
                    status_icon
                ])
            
            kpi_table = Table(kpi_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 1.5*cm])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2F5496')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
            ]))
            story.append(kpi_table)
        
        # 趋势分析
        trends = monthly_stats.get('trends', {})
        if trends:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("📈 趋势分析", self.styles['SectionTitle']))
            
            for metric, trend_info in trends.items():
                direction = trend_info.get('direction', 'stable')
                icon = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}.get(direction, '')
                
                story.append(Paragraph(
                    f"{icon} {metric}: {direction} "
                    f"(变化率: {trend_info.get('change_rate', 0):+.1f}%)",
                    self.styles['BodyText']
                ))
        
        # 建议
        suggestions = monthly_stats.get('suggestions', [])
        if suggestions:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("💡 下月改善建议", self.styles['SectionTitle']))
            
            for idx, suggestion in enumerate(suggestions, 1):
                story.append(Paragraph(
                    f"<b>{idx}.</b> {suggestion}",
                    self.styles['BodyText']
                ))
        
        # 构建
        doc.build(story)
        
        if output_path:
            return output_path
        else:
            buffer.seek(0)
            return buffer
    
    def _mask_phone(self, phone: str) -> str:
        """手机号脱敏"""
        if len(phone) >= 7:
            return phone[:3] + '****' + phone[-4:]
        return '*' * len(phone)


# 全局实例
_pdf_generator: Optional[PDFReportGenerator] = None

def get_pdf_generator() -> PDFReportGenerator:
    """获取全局PDF生成器实例"""
    global _pdf_generator
    if _pdf_generator is None:
        _pdf_generator = PDFReportGenerator()
    return _pdf_generator