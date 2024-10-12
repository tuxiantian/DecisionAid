from flask import Flask, abort, request, jsonify, Blueprint
from shared_models import Checklist, db, ChecklistDecision, ChecklistAnswer, ChecklistQuestion

checklist_bp = Blueprint('checklist', __name__)

@checklist_bp.route('/checklists', methods=['GET'])
def get_checklists():
    checklists = Checklist.query.filter_by(parent_id=None).all()
    checklist_data = [{'id': checklist.id, 'name': checklist.name, 'description': checklist.description, 'version': checklist.version} for checklist in checklists]
    return jsonify(checklist_data), 200

@checklist_bp.route('/checklists', methods=['POST'])
def create_checklist():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    questions = data.get('questions')
    user_id = data.get('user_id', 1)  # Default user_id to 1 if not provided

    if not name or not questions:
        return jsonify({'error': 'Checklist name and questions are required'}), 400

    checklist = Checklist(user_id=user_id,name=name, description=description, version=1)
    db.session.add(checklist)
    db.session.commit()

    for question_text in questions:
        question = ChecklistQuestion(checklist_id=checklist.id, question=question_text)
        db.session.add(question)

    db.session.commit()
    return jsonify({'message': 'Checklist created successfully', 'checklist_id': checklist.id}), 201

@checklist_bp.route('/checklists/<int:checklist_id>', methods=['GET'])
def get_checklist_details(checklist_id):
    checklist = Checklist.query.get_or_404(checklist_id)
    # Get all versions of the checklist
    versions = Checklist.query.filter_by(parent_id=checklist.parent_id if checklist.parent_id else checklist.id).all()
    questions = ChecklistQuestion.query.filter_by(checklist_id=checklist.id).all()
    questions_data = [{'id': question.id, 'question': question.question} for question in questions]
    return jsonify({'questions': questions_data, 'versions': [{'id': version.id, 'version': version.version} for version in versions]}), 200

@checklist_bp.route('/save_checklist_answers', methods=['POST'])
def save_checklist_answers():
    data = request.get_json()
    checklist_id = data.get('checklist_id')
    decision_name = data.get('decision_name')
    final_decision = data.get('final_decision')
    user_id = data.get('user_id', 1)  # 默认 user_id 为 1
    answers = data.get('answers')

    checklist_decision = ChecklistDecision(
        checklist_id=checklist_id,
        user_id=user_id,
        decision_name=decision_name,
        final_decision=final_decision
    )
    db.session.add(checklist_decision)
    db.session.commit()

    for answer in answers:
        question_id = answer.get('question_id')
        answer_text = answer.get('answer')
        if not question_id or not answer_text:
            return jsonify({'error': 'Invalid answer data'}), 400

        answer_record = ChecklistAnswer(
            checklist_decision_id=checklist_decision.id,
            question_id=question_id,
            answer=answer_text
        )
        db.session.add(answer_record)

    db.session.commit()
    return jsonify({'message': 'Checklist answers saved successfully'}), 200

@checklist_bp.route('/checklist_answers/<int:user_id>', methods=['GET'])
def get_user_checklist_answers(user_id):
    checklist_decisions = ChecklistDecision.query.filter_by(user_id=user_id).all()
    user_answers = []
    for decision in checklist_decisions:
        checklist = Checklist.query.get(decision.checklist_id)
        user_answers.append({
            'decision_id': decision.id,
            'decision_name': decision.decision_name,
            'version': checklist.version,
            'created_at': decision.created_at,
            'final_decision': decision.final_decision
        })
    return jsonify(user_answers), 200

@checklist_bp.route('/checklist_answers/<int:user_id>/details/<int:decision_id>', methods=['GET'])
def get_checklist_decision_details(user_id, decision_id):
    decision = ChecklistDecision.query.get_or_404(decision_id)
    if decision.user_id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403

    answers = ChecklistAnswer.query.filter_by(checklist_decision_id=decision.id).all()
    questions = ChecklistQuestion.query.filter_by(checklist_id=decision.checklist_id).all()
    questions_dict = {question.id: question.question for question in questions}
    answers_data = [{'question': questions_dict[answer.question_id], 'answer': answer.answer} for answer in answers]
    checklist = Checklist.query.get(decision.checklist_id)
    decision_details = {
        'decision_name': decision.decision_name,
        'version': checklist.version,
        'created_at': decision.created_at,
        'final_decision': decision.final_decision,
        'answers': answers_data
    }
    return jsonify(decision_details), 200

@checklist_bp.route('/checklist_answers/<int:id>', methods=['DELETE'])
def delete_checklist_decision(id):
    decision = ChecklistDecision.query.get(id)
    if decision is None:
        abort(404, description="Decision not found")

    try:
        # First, delete all checklist answers associated with the decision
        ChecklistAnswer.query.filter_by(checklist_decision_id=id).delete()
        # Then, delete the checklist decision itself
        db.session.delete(decision)
        db.session.commit()
        return jsonify({'message': 'Decision and associated answers deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500