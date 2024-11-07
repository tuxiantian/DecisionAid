from flask import Flask, request, jsonify, Blueprint
from sqlalchemy import desc
from shared_models import Article, LogicError,PlatformArticle, db
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