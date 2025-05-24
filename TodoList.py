from datetime import datetime
from datetime import datetime as dt

from flask import Flask, abort, request, jsonify, Blueprint
from shared_models import TodoItem, db
from flask_login import current_user, login_required
from utils import check_todo_permission


todolist_bp = Blueprint('todolist', __name__)

# 创建待办事项
@todolist_bp.route('/todos', methods=['POST'])
@login_required
def create_todo():
    data = request.get_json()

    # 解析 start_time 和 end_time 为 datetime 对象
    try:
        start_time = datetime.strptime(data['start_time'], "%Y/%m/%d %H:%M:%S")
        end_time = datetime.strptime(data['end_time'], "%Y/%m/%d %H:%M:%S")
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    todo = TodoItem(
        name=data['name'],
        user_id=current_user.id,
        start_time=start_time,
        end_time=end_time,
        type=data['type'],
        importance=data['importance'],
        urgency=data['urgency'],
        status=data['status']
    )
    db.session.add(todo)
    db.session.commit()

    return jsonify({
        'id': todo.id,
        'name': todo.name,
        'start_time': todo.start_time.isoformat(),
        'end_time': todo.end_time.isoformat(),
        'type': todo.type,
        'importance': todo.importance,
        'urgency': todo.urgency,
        'status': todo.status
    }), 201

# 获取待办事项列表
@todolist_bp.route('/todos', methods=['GET'])
@login_required
def get_todos():
    now = dt.utcnow()
    expired_todos = TodoItem.query.filter(TodoItem.end_time < now, TodoItem.status != 'ended',TodoItem.user_id == current_user.id).all()
    for todo in expired_todos:
        todo.status = 'ended'
    db.session.commit()  # 更新数据库
    db.session.flush()
    # 获取北京时区
    todos = TodoItem.query.filter(TodoItem.user_id == current_user.id).all()
    todos_data = []
    for todo in todos:
        todos_data.append({
            'id': todo.id,
            'name': todo.name,
            'type': todo.type,
            'status': todo.status,
            'importance': todo.importance,
            'urgency': todo.urgency,
            'start_time': todo.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': todo.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at':todo.updated_at
        })
    return jsonify(todos_data), 200

@todolist_bp.route('/todos/<int:id>', methods=['PUT'])
@check_todo_permission
@login_required
def update_todo_status(id, todo):
    data = request.get_json()
    status = data.get('status')

    if status != 'completed':
        return jsonify({'error': 'Invalid status value'}), 400

    todo.status = status
    todo.updated_at = dt.utcnow()
    db.session.commit()

    return jsonify({'message': 'Todo status updated successfully'}), 200

@todolist_bp.route('/todos/<int:id>', methods=['DELETE'])
@check_todo_permission
@login_required
def delete_todo(id, todo):
    try:
        db.session.delete(todo)
        db.session.commit()
        return jsonify({'message': 'Todo deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the todo'}), 500
    
@todolist_bp.route('/todos/completed', methods=['GET'])
@login_required
def get_completed_todos():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    start_time = request.args.get('start_time', None)
    end_time = request.args.get('end_time', None)
    
    # 基础查询：已完成且属于当前用户的待办事项
    completed_todos_query = TodoItem.query.filter_by(
        status='completed',
        user_id=current_user.id
    )
    
    # 添加时间范围过滤条件
    if start_time:
        try:
            start_time = datetime.fromisoformat(start_time)
            completed_todos_query = completed_todos_query.filter(
                TodoItem.updated_at >= start_time
            )
        except ValueError:
            return jsonify({'error': 'Invalid start_time format'}), 400
    
    if end_time:
        try:
            end_time = datetime.fromisoformat(end_time)
            completed_todos_query = completed_todos_query.filter(
                TodoItem.updated_at <= end_time
            )
        except ValueError:
            return jsonify({'error': 'Invalid end_time format'}), 400
    
    # 按更新时间倒序排列
    completed_todos_query = completed_todos_query.order_by(TodoItem.updated_at.desc())
    
    # 实现分页
    pagination = completed_todos_query.paginate(
        page=page,
        per_page=page_size,
        error_out=False
    )

    results = [{
        'id': todo.id,
        'name': todo.name,
        'start_time': todo.start_time,
        'end_time': todo.end_time,
        'importance': todo.importance,
        'urgency': todo.urgency,
        'updated_at': todo.updated_at
    } for todo in pagination.items]

    return jsonify({
        'todos': results,
        'total_pages': pagination.pages,
        'current_page': pagination.page
    }), 200

@todolist_bp.route('/todos/ended', methods=['GET'])
@login_required
def get_ended_todos():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    start_time = request.args.get('start_time', None)
    end_time = request.args.get('end_time', None)
    
    # 基础查询：已结束且属于当前用户的待办事项
    ended_todos_query = TodoItem.query.filter_by(
        status='ended',
        user_id=current_user.id
    )
    
    # 添加时间范围过滤条件
    if start_time:
        try:
            start_time = datetime.fromisoformat(start_time)
            ended_todos_query = ended_todos_query.filter(
                TodoItem.updated_at >= start_time
            )
        except ValueError:
            return jsonify({'error': 'Invalid start_time format'}), 400
    
    if end_time:
        try:
            end_time = datetime.fromisoformat(end_time)
            ended_todos_query = ended_todos_query.filter(
                TodoItem.updated_at <= end_time
            )
        except ValueError:
            return jsonify({'error': 'Invalid end_time format'}), 400
    
    # 按更新时间倒序排列
    ended_todos_query = ended_todos_query.order_by(TodoItem.updated_at.desc())
    
    # 实现分页
    pagination = ended_todos_query.paginate(
        page=page,
        per_page=page_size,
        error_out=False
    )

    results = [{
        'id': todo.id,
        'name': todo.name,
        'start_time': todo.start_time,
        'end_time': todo.end_time,
        'importance': todo.importance,
        'urgency': todo.urgency,
        'updated_at': todo.updated_at
    } for todo in pagination.items]

    return jsonify({
        'todos': results,
        'total_pages': pagination.pages,
        'current_page': pagination.page
    }), 200