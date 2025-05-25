from flask import Flask, request, jsonify, Blueprint
from sqlalchemy import desc
from shared_models import Inspiration,Reflection, db
from datetime import datetime as dt
from flask_login import current_user, login_required

inspiration_bp = Blueprint('inspiration', __name__)

@inspiration_bp.route('/api/inspirations', methods=['GET'])
def get_inspirations():
    """获取启发内容列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 2, type=int)
    
    pagination = Inspiration.query.order_by(
        Inspiration.updated_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    inspirations = [{
        'id': item.id,
        'type': item.type,
        'content': item.content,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat()
    } for item in pagination.items]
    
    return jsonify({
        'inspirations': inspirations,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@inspiration_bp.route('/api/inspirations/<int:id>/reflections', methods=['GET'])
def get_reflections(id):
    """获取某个启发内容的所有感想"""
    inspiration = Inspiration.query.get_or_404(id)
    
    reflections = [{
        'id': r.id,
        'content': r.content,
        'created_at': r.created_at.isoformat(),
        'updated_at': r.updated_at.isoformat()
    } for r in inspiration.reflections]
    
    return jsonify({
        'inspiration_id': id,
        'reflections': reflections,
        'count': len(reflections)
    })

@inspiration_bp.route('/api/reflections', methods=['POST'])
def create_reflection():
    """创建新的感想"""
    data = request.get_json()
    
    if not data or not data.get('content') or not data.get('inspiration_id'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # 检查启发内容是否存在
    inspiration = Inspiration.query.get(data['inspiration_id'])
    if not inspiration:
        return jsonify({'error': 'Inspiration not found'}), 404
    
    reflection = Reflection(
        content=data['content'],
        inspiration_id=data['inspiration_id']
    )
    
    db.session.add(reflection)
    db.session.commit()
    
    return jsonify({
        'id': reflection.id,
        'content': reflection.content,
        'inspiration_id': reflection.inspiration_id,
        'created_at': reflection.created_at.isoformat()
    }), 201

@inspiration_bp.route('/api/reflections/<int:id>', methods=['PUT'])
def update_reflection(id):
    """更新感想内容"""
    reflection = Reflection.query.get_or_404(id)
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'error': 'Content is required'}), 400
    
    reflection.content = data['content']
    db.session.commit()
    
    return jsonify({
        'id': reflection.id,
        'content': reflection.content,
        'updated_at': reflection.updated_at.isoformat()
    })

@inspiration_bp.route('/api/reflections/<int:id>', methods=['DELETE'])
def delete_reflection(id):
    """删除感想"""
    reflection = Reflection.query.get_or_404(id)
    
    db.session.delete(reflection)
    db.session.commit()
    
    return jsonify({'message': 'Reflection deleted successfully'})