import logging
import traceback
from flask import Flask, json, request, jsonify, Blueprint, current_app as app
from sqlalchemy import desc
from shared_models import AnalysisContent, AnalysisData, Article, LogicError,PlatformArticle, db
from datetime import datetime as dt
from flask_login import current_user

logic_errors_bp = Blueprint('logic_errors', __name__)

@logic_errors_bp.route('/api/logic-errors', methods=['GET'])
def get_logic_errors():
    logic_errors = LogicError.query.all()
    return jsonify([
        {
            'id': error.id,
            'name': error.name,
            'term': error.term,
            'description': error.description,
            'example': error.example
        } for error in logic_errors
    ])

@logic_errors_bp.route('/api/save_fact_opinion_analysis', methods=['POST'])
def save_fact_opinion_analysis():
    data = request.get_json()
    content=data.get('content')
    analysis_table=data.get('analysisTable')
    if not content or not analysis_table:
        return jsonify({"status": "error", "message": "Content or analysis data missing"}), 400

    try:
        # 1. 将 content 数据保存到 AnalysisContent 表中
        new_analysis_content = AnalysisContent(user_id=current_user.id, content=content)
        db.session.add(new_analysis_content)
        db.session.flush()  # 保证 new_analysis_content.id 可以被 analysis_data 使用

        # 2. 将每条 analysisTable 数据保存到 AnalysisData 表中
        for item in analysis_table:
            new_analysis_data = AnalysisData(
                analysis_content_id=new_analysis_content.id,
                facts=json.dumps(item.get('facts'), ensure_ascii=False),
                opinion=item.get('opinion'),
                logic_error_id=item.get('error').get('id')
            )
            db.session.add(new_analysis_data)

        # 3. 提交所有数据到数据库
        db.session.commit()

        return jsonify({"status": "success", "message": "数据保存成功"}), 200

    except Exception as e:
        db.session.rollback()  # 如果出错，则回滚事务
        # 获取异常的完整堆栈信息
        error_trace = traceback.format_exc()

        # 使用 app.logger 记录错误信息
        app.logger.error(f"Error in /api/save_fact_opinion_analysis: {e}\n{error_trace}")
        return jsonify({"status": "error", "message": str(e)}), 500

@logic_errors_bp.route('/api/get_paged_analyses', methods=['GET'])
def get_paged_analyses():
    try:
        # 获取查询参数，默认为第一页
        page = request.args.get('page', 1, type=int)
        per_page = 5  # 每页显示 5 条记录

        # 分页查询 AnalysisContent 表
        analyses = AnalysisContent.query.order_by(AnalysisContent.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        # 将查询结果转换为 JSON 格式
        result = []
        for analysis in analyses.items:
            content_summary = analysis.content[:300] + '...' if len(analysis.content) > 300 else analysis.content
            result.append({
                "id": analysis.id,
                "content": content_summary,
                "created_at": analysis.created_at
            })

        # 返回数据，包括总页数、当前页
        return jsonify({
            "status": "success",
            "data": result,
            "total_pages": analyses.pages,
            "current_page": analyses.page
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500    
    
@logic_errors_bp.route('/api/analysis/<int:id>', methods=['GET'])
def get_analysis_detail(id):
    try:
        # 获取 AnalysisContent 对象
        analysis_content = AnalysisContent.query.get(id)
        if not analysis_content:
            return jsonify({"status": "error", "message": "Analysis not found"}), 404

        # 获取关联的 AnalysisData 对象
        analysis_data = AnalysisData.query.filter_by(analysis_content_id=id).all()

        # 构造响应数据
        analysis_detail = {
            "id": analysis_content.id,
            "content": analysis_content.content,
            "created_at": analysis_content.created_at,
            "data": [{
                "facts": json.loads(data.facts),  # 将 JSON 字符串转换回列表
                "opinion": data.opinion,
                "error": data.logic_error.name if data.logic_error else None
            } for data in analysis_data]
        }

        return jsonify({"status": "success", "data": analysis_detail}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500