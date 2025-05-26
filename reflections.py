from flask import Flask, request, jsonify, Blueprint
from sqlalchemy import desc
from shared_models import Inspiration,Reflection, db
from datetime import datetime as dt
from flask_login import current_user, login_required
from sqlalchemy import func
reflections_bp = Blueprint('reflections', __name__)

@reflections_bp.route('/api/my-reflections', methods=['GET'])
@login_required
def get_my_reflections():
    """
    获取用户的所有感想（分页）
    每个启发只返回最新的一条感想
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 2, type=int)
    
    # 获取每个启发的最新感想
    subquery = db.session.query(
        Reflection.inspiration_id,
        func.max(Reflection.updated_at).label('max_updated_at')
    ).filter(
        Reflection.user_id == current_user.id
    ).group_by(
        Reflection.inspiration_id
    ).subquery()
    
    # 主查询：获取最新感想及其对应的启发内容
    query = db.session.query(Reflection, Inspiration)\
        .join(Inspiration, Reflection.inspiration_id == Inspiration.id)\
        .join(subquery,
             (Reflection.inspiration_id == subquery.c.inspiration_id) &
             (Reflection.updated_at == subquery.c.max_updated_at))\
        .filter(Reflection.user_id == current_user.id)\
        .order_by(Reflection.updated_at.desc())
    
    # 分页
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # 获取总启发数（用户写过感想的）
    total_inspirations = db.session.query(
        func.count(db.distinct(Reflection.inspiration_id))
    ).filter(
        Reflection.user_id == current_user.id
    ).scalar()
    
    data = {
        'reflections': [{
            'id': r.id,
            'content': r.content,
            'created_at': r.created_at.isoformat(),
            'updated_at': r.updated_at.isoformat(),
            'inspiration': {
                'id': i.id,
                'type': i.type,
                'content': i.content,
                'created_at': i.created_at.isoformat()
            }
        } for r, i in paginated.items],
        'total': total_inspirations,
        'pages': paginated.pages,
        'current_page': page
    }
    return jsonify(data)

@reflections_bp.route('/api/my-reflections/random', methods=['GET'])
@login_required
def get_random_reflections():
    """
    获取用户的随机感想（每个启发最新的一条）
    """
    # 获取用户写过感想的启发ID列表
    inspiration_ids = db.session.query(
        db.distinct(Reflection.inspiration_id))\
        .filter(Reflection.user_id == current_user.id)\
        .all()
    
    if not inspiration_ids:
        return jsonify({'reflections': []})
    
    # 随机选择2个启发
    random_ids = db.session.query(
        Reflection.inspiration_id)\
        .filter(Reflection.user_id == current_user.id)\
        .distinct()\
        .order_by(func.random())\
        .limit(2)\
        .all()
    
    # 获取这些启发的最新感想
    reflections = []
    for insp_id in random_ids:
        reflection = Reflection.query\
            .filter_by(
                inspiration_id=insp_id[0],
                user_id=current_user.id)\
            .order_by(Reflection.updated_at.desc())\
            .first()
        
        if reflection:
            inspiration = Inspiration.query.get(insp_id[0])
            reflections.append({
                'id': reflection.id,
                'content': reflection.content,
                'created_at': reflection.created_at.isoformat(),
                'updated_at': reflection.updated_at.isoformat(),
                'inspiration': {
                    'id': inspiration.id,
                    'type': inspiration.type,
                    'content': inspiration.content,
                    'created_at': inspiration.created_at.isoformat()
                }
            })
    
    return jsonify({'reflections': reflections})