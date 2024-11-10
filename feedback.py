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

    feedback = Feedback(
        user_id=user_id,
        description=description,
        contact_info=contact_info,
        created_at=datetime.utcnow()
    )
    db.session.add(feedback)
    db.session.commit()

    return jsonify({"message": "反馈已提交"}), 201

@feedback_bp.route('/api/admin/feedback/<int:id>/respond', methods=['POST'])
def respond_to_feedback(id):
    feedback = Feedback.query.get(id)
    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    response = request.json.get('response')
    feedback.response = response
    feedback.responded_at = datetime.utcnow()
    feedback.status = "已回复"
    db.session.commit()

    return jsonify({"message": "回复已保存"}), 200
