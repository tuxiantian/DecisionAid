from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from shared_models import Feedback,db

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    user_id = current_user.id
    description = data.get('description')
    contact_info = data.get('contact_info')
    attachments = data.get('attachments', [])  # 接收文件URL数组
    if not description:
        return jsonify({'error': 'Description is required'}), 400
    
    feedback = Feedback(
        user_id=user_id,
        description=description,
        attachments=attachments,
        contact_info=contact_info,
        created_at=datetime.utcnow()
    )
    db.session.add(feedback)
    db.session.commit()

    return jsonify({"message": "反馈已提交",
            'feedback_id': feedback.id}), 200

@feedback_bp.route('/api/my_feedback', methods=['GET'])
@login_required  # 确保用户已登录
def get_user_feedback():
    # 获取查询参数，默认为第一页
    page = request.args.get('page', 1, type=int)
    per_page = 5  # 每页显示 5 条记录
    user_id = current_user.id  # 获取当前登录用户的ID
    feedbacks = Feedback.query.filter_by(user_id=user_id).order_by(Feedback.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    feedback_data = [{
        "id": fb.id,
        "description": fb.description,
        "attachments": fb.attachments,
        "response": fb.response,
        "status": fb.status,
        "created_at": fb.created_at,
        "responded_at": fb.responded_at
    } for fb in feedbacks]

    return jsonify({
            "status": "success",
            "data": feedback_data,
            "total_pages": feedbacks.pages,
            "current_page": feedbacks.page
        }), 200