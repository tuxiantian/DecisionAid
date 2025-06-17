from flask import Flask, request, jsonify, Blueprint
from sqlalchemy import desc
from shared_models import Inspiration,Reflection, db
from datetime import datetime as dt
from flask_login import current_user, login_required
from sqlalchemy import func
inspiration_bp = Blueprint('inspiration', __name__)

@inspiration_bp.route('/api/inspirations/random', methods=['GET'])
def get_random_inspirations():
    """随机获取2条启发内容"""
    try:
        # 使用SQLAlchemy的func.random() (MySQL是RAND(), PostgreSQL是random())
        random_inspirations = Inspiration.query.order_by(
            func.rand()  # MySQL使用func.rand()，PostgreSQL使用func.random()
        ).limit(2).all()
        
        result = [{
            'id': item.id,
            'type': item.type,
            'content': item.content,
            'description': item.description,
            'created_at': item.created_at.isoformat()
        } for item in random_inspirations]
        
        return jsonify({
            'inspirations': result,
            'count': len(result)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inspiration_bp.route('/api/inspirations', methods=['GET'])
def get_inspirations():
    """获取启发内容列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 2, type=int)
    search = request.args.get('search')
    query = Inspiration.query
    if search:
        query = query.filter(db.or_(
                Inspiration.content.ilike(f"%{search}%"),
                Inspiration.description.ilike(f"%{search}%")
            ))
    pagination = query.order_by(
        Inspiration.updated_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    inspirations = [{
        'id': item.id,
        'type': item.type,
        'content': item.content,
        'description': item.description,
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
    """获取某个启发内容的所有感想（按更新时间降序排列）"""
    inspiration = Inspiration.query.get_or_404(id)
    
    # 使用 Python 排序（适用于少量数据）
    sorted_reflections = sorted(
        inspiration.reflections,
        key=lambda r: r.updated_at,
        reverse=True  # 降序
    )
    
    reflections = [{
        'id': r.id,
        'type':r.type,
        'content': r.content,
        'created_at': r.created_at.isoformat(),
        'updated_at': r.updated_at.isoformat()
    } for r in sorted_reflections]
    
    return jsonify({
        'inspiration_id': id,
        'reflections': reflections,
        'count': len(reflections)
    })

@inspiration_bp.route('/api/reflections', methods=['POST'])
@login_required
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
        user_id=current_user.id,
        type=data['type'],
        content=data['content'],
        inspiration_id=data['inspiration_id']
    )
    
    db.session.add(reflection)
    db.session.commit()
    
    return jsonify({
        'id': reflection.id,
        'type':reflection.type,
        'user_id': current_user.id,
        'content': reflection.content,
        'inspiration_id': reflection.inspiration_id,
        'created_at': reflection.created_at.isoformat(),
        'updated_at': reflection.updated_at.isoformat()
    }), 201

@inspiration_bp.route('/api/reflections/<int:id>', methods=['PUT'])
@login_required
def update_reflection(id):
    """更新感想内容"""
    reflection = Reflection.query.get_or_404(id)
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'error': 'Content is required'}), 400
    
    reflection.content = data['content']
    reflection.type = data['type']
    db.session.commit()
    
    return jsonify({
        'id': reflection.id,
        'type': reflection.type,
        'content': reflection.content,
        'updated_at': reflection.updated_at.isoformat()
    })

@inspiration_bp.route('/api/reflections/<int:id>', methods=['DELETE'])
@login_required
def delete_reflection(id):
    """删除感想"""
    reflection = Reflection.query.get_or_404(id)
    
    db.session.delete(reflection)
    db.session.commit()
    
    return jsonify({'message': 'Reflection deleted successfully'})