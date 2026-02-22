# services/pdf_service.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import os
from datetime import datetime
import io

class PDFService:
    def __init__(self):
        # 注册中文字体
        self.register_chinese_fonts()
        
    def register_chinese_fonts(self):
        """注册中文字体"""
        try:
            # 方法1：使用系统自带的中文字体（Windows）
            font_paths = [
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
                'C:/Windows/Fonts/simsun.ttc',  # 宋体
                'C:/Windows/Fonts/simkai.ttf',  # 楷体
                'C:/Windows/Fonts/msyh.ttf',    # 微软雅黑
            ]
            
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_name = os.path.basename(font_path).split('.')[0]
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    # 注册中文字体
                    addMapping(font_name, 0, 0, font_name)  # 常规
                    addMapping(font_name, 0, 1, font_name)  # 粗体
                    addMapping(font_name, 1, 0, font_name)  # 斜体
                    addMapping(font_name, 1, 1, font_name)  # 粗斜体
                    self.font_name = font_name
                    print(f"字体注册成功: {font_name}")
                    font_registered = True
                    break
            
            if not font_registered:
                # 方法2：使用默认字体
                self.font_name = 'Helvetica'
                print("使用默认字体 Helvetica")
                
        except Exception as e:
            print(f"字体注册失败: {e}")
            self.font_name = 'Helvetica'
    
    def generate_decision_report(self, model_data, output_path=None):
        """生成完整决策分析报告PDF"""
        buffer = io.BytesIO()
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        
        # 存储PDF内容
        story = []
        
        # 获取样式
        styles = getSampleStyleSheet()
        
        # 创建中文字体样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=self.font_name,
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            alignment=1,  # 居中
            spaceAfter=30,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=self.font_name,
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            spaceBefore=12,
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
        )
        
        # 标题
        story.append(Paragraph("最小化最大遗憾值决策分析报告", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # 模型基本信息
        story.append(Paragraph(f"模型名称：{model_data['name']}", normal_style))
        story.append(Paragraph(f"创建时间：{model_data['created_at']}", normal_style))
        if model_data.get('description'):
            story.append(Paragraph(f"模型描述：{model_data['description']}", normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # 方案和情景信息
        story.append(Paragraph("方案与情景", heading_style))
        
        # 方案列表
        alt_text = "备选方案："
        for i, alt in enumerate(model_data['alternatives']):
            alt_text += f" {i+1}.{alt['name']}"
            if i < len(model_data['alternatives']) - 1:
                alt_text += "；"
        story.append(Paragraph(alt_text, normal_style))
        
        # 情景列表
        scen_text = "情景状态："
        for i, scen in enumerate(model_data['scenarios']):
            scen_text += f" {i+1}.{scen['name']}"
            if scen.get('probability'):
                scen_text += f"(概率:{scen['probability']})"
            if i < len(model_data['scenarios']) - 1:
                scen_text += "；"
        story.append(Paragraph(scen_text, normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # 收益矩阵
        story.append(Paragraph("收益矩阵", heading_style))
        
        # 准备收益矩阵数据
        payoff_data = [['方案 \\ 情景'] + [s['name'] for s in model_data['scenarios']]]
        for i, alt in enumerate(model_data['alternatives']):
            row = [alt['name']]
            for j in range(len(model_data['scenarios'])):
                value = model_data['payoff_matrix'][i][j]
                row.append(f"{value:.2f}")
            payoff_data.append(row)
        
        # 创建收益矩阵表格
        payoff_table = Table(payoff_data)
        payoff_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('FONTWEIGHT', (0, 0), (-1, 0), 'BOLD'),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8f9fa')),
            ('FONTWEIGHT', (0, 1), (0, -1), 'BOLD'),
        ]))
        story.append(payoff_table)
        story.append(Spacer(1, 0.3*inch))
        
        # 如果有分析结果
        if model_data.get('result'):
            story.append(Paragraph("分析结果", heading_style))
            story.append(Paragraph(f"分析时间：{model_data['result']['created_at']}", normal_style))
            story.append(Spacer(1, 0.1*inch))
            
            # 遗憾矩阵
            story.append(Paragraph("遗憾矩阵", heading_style))
            
            # 准备遗憾矩阵数据
            regret_data = [['方案 \\ 情景'] + [s['name'] for s in model_data['scenarios']] + ['最大遗憾值']]
            for i, alt in enumerate(model_data['alternatives']):
                row = [alt['name']]
                for j in range(len(model_data['scenarios'])):
                    value = model_data['result']['regret_matrix'][i][j]
                    row.append(f"{value:.2f}")
                row.append(f"{model_data['result']['max_regrets'][i]:.2f}")
                regret_data.append(row)
            
            # 创建遗憾矩阵表格
            regret_table = Table(regret_data)
            
            # 表格样式
            table_style = [
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('FONTWEIGHT', (0, 0), (-1, 0), 'BOLD'),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8f9fa')),
                ('FONTWEIGHT', (0, 1), (0, -1), 'BOLD'),
            ]
            
            # 高亮最优方案
            best_alt_index = model_data['result'].get('best_alternative_id')
            if best_alt_index is not None:
                best_row = best_alt_index
                table_style.extend([
                    ('BACKGROUND', (0, best_row), (-2, best_row), colors.HexColor('#d4edda')),
                    ('TEXTCOLOR', (0, best_row), (-2, best_row), colors.HexColor('#155724')),
                ])
            
            regret_table.setStyle(TableStyle(table_style))
            story.append(regret_table)
            story.append(Spacer(1, 0.3*inch))
            
            # 决策建议卡片
            story.append(Paragraph("决策建议", heading_style))
            
            # 创建一个带背景色的表格作为决策卡片
            decision_data = [
                [''],
                [f"建议选择：{model_data['result']['best_alternative_name']}"],
                [f"最小最大遗憾值：{model_data['result']['min_max_regret']:.2f}"]
            ]
            
            decision_table = Table(decision_data, colWidths=[doc.width - 100])
            decision_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('FONTSIZE', (0, 1), (0, 1), 14),
                ('FONTSIZE', (0, 2), (0, 2), 12),
                ('TOPPADDING', (0, 1), (0, 1), 12),
                ('BOTTOMPADDING', (0, 1), (0, 1), 12),
                ('TOPPADDING', (0, 2), (0, 2), 8),
                ('BOTTOMPADDING', (0, 2), (0, 2), 12),
            ]))
            story.append(decision_table)
        
        # 构建PDF
        doc.build(story)
        
        # 获取PDF字节流
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            return output_path
        
        return pdf_bytes
    
    def generate_simple_report(self, model_data):
        """生成简洁版报告（修复中文乱码）"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # 获取样式
        styles = getSampleStyleSheet()
        
        # 创建所有需要的样式，都使用中文字体
        title_style = ParagraphStyle(
            'SimpleTitle',
            parent=styles['Title'],
            fontName=self.font_name,
            fontSize=18,
            alignment=1,  # 居中
            spaceAfter=20,
        )
        
        heading_style = ParagraphStyle(
            'SimpleHeading',
            parent=styles['Heading2'],
            fontName=self.font_name,
            fontSize=14,
            spaceAfter=10,
            spaceBefore=10,
        )
        
        normal_style = ParagraphStyle(
            'SimpleNormal',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            spaceAfter=6,
        )
        
        # 标题
        story.append(Paragraph(f"决策报告：{model_data['name']}", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        if model_data.get('result'):
            # 遗憾矩阵标题
            story.append(Paragraph("遗憾矩阵", heading_style))
            
            # 准备遗憾矩阵数据
            regret_data = [['方案'] + [s['name'] for s in model_data['scenarios']] + ['最大遗憾']]
            for i, alt in enumerate(model_data['alternatives']):
                row = [alt['name']]
                for j in range(len(model_data['scenarios'])):
                    value = model_data['result']['regret_matrix'][i][j]
                    row.append(f"{value:.2f}")
                row.append(f"{model_data['result']['max_regrets'][i]:.2f}")
                regret_data.append(row)
            
            # 创建遗憾矩阵表格 - 确保表格也使用中文字体
            regret_table = Table(regret_data)
            regret_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),  # 所有单元格都使用中文字体
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('FONTWEIGHT', (0, 0), (-1, 0), 'BOLD'),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8f9fa')),
                ('FONTWEIGHT', (0, 1), (0, -1), 'BOLD'),
            ]))
            story.append(regret_table)
            story.append(Spacer(1, 0.2*inch))
            
            # 决策结果 - 使用带中文字体的样式
            story.append(Paragraph("决策结果", heading_style))
            
            # 创建结果卡片
            result_data = [
                [f"推荐方案：{model_data['result']['best_alternative_name']}"],
                [f"最小最大遗憾值：{model_data['result']['min_max_regret']:.2f}"]
            ]
            
            result_table = Table(result_data, colWidths=[doc.width - 100])
            result_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#27ae60')),
                ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#34495e')),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(result_table)
        
        # 构建PDF
        doc.build(story)
        return buffer.getvalue()