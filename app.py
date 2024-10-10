from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Response
from flask_cors import CORS
import pymysql
import json

pymysql.install_as_MySQLdb()

app = Flask(__name__, static_folder='build/static', template_folder='build')
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:123456@localhost/decisions_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Model
class Decision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    decision_name = db.Column(db.String(100), nullable=False)
    final_decision = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.relationship('Answer', backref='decision', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    decision_id = db.Column(db.Integer, db.ForeignKey('decision.id'), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)

@app.route('/')
def index():
    return render_template('index.html')
    
# API Endpoint for paginated list of decisions
@app.route('/decisions', methods=['GET'])
def get_decisions():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    decisions = Decision.query.order_by(Decision.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    decisions_list = [{
        'id': decision.id,
        'user_id': decision.user_id,
        'decision_name': decision.decision_name,
        'final_decision':decision.final_decision,
        'created_at': decision.created_at
    } for decision in decisions.items]

    return jsonify({
        'total': decisions.total,
        'pages': decisions.pages,
        'current_page': decisions.page,
        'decisions': decisions_list
    }), 200

@app.route('/delete_decision/<int:decision_id>', methods=['DELETE'])
def delete_decision(decision_id):
    decision = Decision.query.get_or_404(decision_id)
    # Delete all related answers
    Answer.query.filter_by(decision_id=decision.id).delete()
    # Delete the decision itself
    db.session.delete(decision)
    db.session.commit()
    return jsonify({'message': 'Decision and related answers deleted successfully'}), 200

# API Endpoint to save decision data
@app.route('/save_decision', methods=['POST'])
def save_decision():
    data = request.get_json()
    user_id = data.get('user_id')
    decision_name = data.get('decision_name')
    answers = data.get('answers')
    final_decision = data.get('final_decision')


    decision = Decision(user_id=user_id, decision_name=decision_name, final_decision=final_decision)
    db.session.add(decision)
    db.session.commit()

    module_mapping = {
        0: "面临决断",
        1: "面临决断",
        2: "理解事情",
        3: "理解事情",
        4: "理解事情",
        5: "理解事情",
        6: "认识自己",
        7: "认识自己",
        8: "认识自己",
        9: "认识自己",
        10: "做出决断",
        11: "做出决断",
        12: "做出决断"
    }

    for index, ans in enumerate(answers):
        module = module_mapping.get(index, "未知模块")
        answer_entry = Answer(decision_id=decision.id, module=module, question=ans['question'], answer=ans['answer'])
        db.session.add(answer_entry)

    db.session.commit()
    return jsonify({'message': 'Decision saved successfully'}), 200

# API Endpoint to get decision data
@app.route('/get_decision/<int:decision_id>', methods=['GET'])
def get_decision(decision_id):
    decision = Decision.query.get_or_404(decision_id)
    answers = Answer.query.filter_by(decision_id=decision_id).all()
    
    answer_list = [{'module': a.module, 'question': a.question, 'answer': a.answer} for a in answers]
    decision_data = {
        'decision_name': decision.decision_name,
        'created_at': decision.created_at,
        'answers': answer_list
    }
    return jsonify(decision_data), 200

# API Endpoint for getting detailed decision
@app.route('/decision_details/<int:decision_id>', methods=['GET'])
def get_decision_details(decision_id):
    decision = Decision.query.get_or_404(decision_id)
    answers = Answer.query.filter_by(decision_id=decision_id).all()
    # Group answers into modules
    modules = {
        "面临决断": [],
        "理解事情": [],
        "认识自己": [],
        "做出决断": []
    }
    
    for answer in answers:
        modules[answer.module].append({'question': answer.question, 'answer': answer.answer})
    
    decision_data = {
        'decision_name': decision.decision_name,
        'created_at': decision.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'modules': modules
    }
    response_data = json.dumps(decision_data, ensure_ascii=False)
    return Response(response_data, content_type='application/json; charset=utf-8')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
