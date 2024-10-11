from datetime import datetime as dt
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Checklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    parent_id = db.Column(db.Integer, db.ForeignKey('checklist.id'), nullable=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=dt.utcnow)

class ChecklistQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklist.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)

class ChecklistAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checklist_decision_id = db.Column(db.Integer, db.ForeignKey('checklist_decision.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('checklist_question.id'), nullable=False)
    answer = db.Column(db.Text, nullable=False)

class ChecklistDecision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklist.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    decision_name = db.Column(db.String(100), nullable=False)
    final_decision = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=dt.utcnow)

# Database Model
class Decision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    decision_name = db.Column(db.String(100), nullable=False)
    final_decision = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=dt.utcnow)
    answers = db.relationship('Answer', backref='decision', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    decision_id = db.Column(db.Integer, db.ForeignKey('decision.id'), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)