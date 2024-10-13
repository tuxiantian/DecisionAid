from datetime import datetime
from datetime import datetime as dt

from flask import Flask, abort, request, jsonify, Blueprint
from shared_models import TodoItem, db

todolist_bp = Blueprint('todolist', __name__)

# 创建待办事项
@todolist_bp.route('/todos', methods=['POST'])
def create_todo():
    data = request.get_json()

    # 解析 start_time 和 end_time 为 datetime 对象
    try:
        start_time = datetime.strptime(data['start_time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = datetime.strptime(data['end_time'], "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    todo = TodoItem(
        name=data['name'],
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
def get_todos():
    todos = TodoItem.query.all()
    todos_data = []
    for todo in todos:
        todos_data.append({
            'id': todo.id,
            'name': todo.name,
            'type': todo.type,
            'status': todo.status,
            'importance': todo.importance,
            'urgency': todo.urgency,
            'start_time': todo.start_time,
            'end_time': todo.end_time,
            'updated_at':todo.updated_at
        })
    return jsonify(todos_data), 200

@todolist_bp.route('/todos/<int:id>', methods=['PUT'])
def update_todo_status(id):
    data = request.get_json()
    status = data.get('status')

    if status != 'completed':
        return jsonify({'error': 'Invalid status value'}), 400

    todo = TodoItem.query.get(id)
    if not todo:
        return jsonify({'error': 'Todo not found'}), 404

    todo.status = status
    todo.updated_at = dt.utcnow()
    db.session.commit()

    return jsonify({'message': 'Todo status updated successfully'}), 200

@todolist_bp.route('/todos/<int:id>', methods=['DELETE'])
def delete_todo(id):
    todo = TodoItem.query.get(id)
    if not todo:
        return jsonify({'error': 'Todo not found'}), 404

    try:
        db.session.delete(todo)
        db.session.commit()
        return jsonify({'message': 'Todo deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the todo'}), 500