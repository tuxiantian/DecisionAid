import json
from flask import Flask, request, jsonify, Blueprint
from sqlalchemy import desc
from shared_models import BalancedDecision, db
from datetime import datetime as dt
from flask_login import current_user

balanced_decision_bp = Blueprint('balanced_decision', __name__)

@balanced_decision_bp.route('/api/save_decision', methods=['POST'])
def save_decision():
    data = request.get_json()

    # 从请求数据中提取各项信息
    decision_name = data.get('decisionName')
    conditions = data.get('conditions')
    comparisons = data.get('comparisons')
    groups = data.get('groups')
    decision_result = data.get('decisionResult')

    # 将数据保存到数据库
    try:
        new_decision = BalancedDecision(
            user_id=current_user.id,
            decision_name=decision_name,
            conditions=json.dumps(conditions),
            comparisons=json.dumps(comparisons),
            groups=json.dumps(groups),
            result=decision_result
        )
        db.session.add(new_decision)
        db.session.commit()

        return jsonify({"message": "Decision saved successfully!"}), 200
    except Exception as e:
        db.session.rollback()  # 回滚事务以防止数据库不一致
        print("Error saving decision:", str(e))
        return jsonify({"message": "Failed to save decision."}), 500
    
# 获取所有决策数据的API接口
@balanced_decision_bp.route('/api/get_decisions', methods=['GET'])
def get_decisions():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    decisions = BalancedDecision.query.filter_by(user_id=current_user.id).order_by(desc(BalancedDecision.created_at)).paginate(page=page, per_page=page_size, error_out=False)
    decisions_list = [
        {
            'id': decision.id,
            'decision_name': decision.decision_name,
            'result': decision.result,
            'created_at': decision.created_at
        } for decision in decisions
    ]
    return jsonify({
        'decisions_list': decisions_list,
        'total_pages': decisions.pages,
        'current_page': decisions.page,
        'total_items': decisions.total
    }), 200

# 获取单个决策详情的API接口
@balanced_decision_bp.route('/api/get_decision/<int:id>', methods=['GET'])
def get_decision(id):
    decision = BalancedDecision.query.get(id)
    if decision is None:
        return jsonify({"message": "Decision not found"}), 404

    if not decision.user_id==current_user.id:
        return jsonify({"message": "You are not allowed to access this Decision"}), 403
    decision_details = {
        'id': decision.id,
        'decision_name': decision.decision_name,
        'conditions': json.loads(decision.conditions),
        'comparisons': json.loads(decision.comparisons),
        'groups': json.loads(decision.groups),
        'result': decision.result,
        'created_at': decision.created_at
    }
    print(jsonify(decision_details) )
    return jsonify(decision_details)    