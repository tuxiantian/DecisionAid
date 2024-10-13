from datetime import datetime as dt
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(255), nullable=False)
    tags = db.Column(db.String(255), nullable=True)
    keywords = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=dt.utcnow)
    updated_at = db.Column(db.DateTime, default=dt.utcnow, onupdate=dt.utcnow)


class TodoItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.Enum('today', 'this_week', 'this_month', 'custom'), nullable=False)
    status = db.Column(db.Enum('not_started', 'in_progress', 'completed', 'ended'), default='not_started')
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    importance = db.Column(db.Boolean, default=False)
    urgency = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=dt.utcnow)
    updated_at = db.Column(db.DateTime, default=dt.utcnow, onupdate=dt.utcnow)

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
    referenced_articles = db.Column(db.String(255), nullable=True)  # 引用的文章ID，以逗号分隔
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

# Review 数据模型
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    decision_id = db.Column(db.Integer, db.ForeignKey('checklist_decision.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    referenced_articles = db.Column(db.String(255))  # 保存引用的文章 ID，多个用逗号分隔
    created_at = db.Column(db.DateTime, default=dt.utcnow)

