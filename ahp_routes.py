from flask import Blueprint, request, jsonify
import mysql.connector
import json
import numpy as np
from AHP import AHP
import pytz
from shared_models import AHPHistory, db  # 确保 AHP.py 文件在同一目录或 Python 路径中
from flask_login import current_user, login_required

ahp_bp = Blueprint('ahp', __name__)

# 从配置文件加载数据库连接信息
with open('config.json') as config_file:
    config = json.load(config_file)

db_config = config['db_config']

def convert_to_numeric(matrix):
    """ 将字符串矩阵元素转换为数值 """
    def parse_fraction(value):
        if '/' in value:
            numerator, denominator = map(float, value.split('/'))
            return numerator / denominator
        return float(value)

    return [[parse_fraction(value) for value in row] for row in matrix]
# 获取数据库连接
def get_db_connection():
    return mysql.connector.connect(**db_config)

@ahp_bp.route('/ahp_analysis', methods=['POST'])
def ahp_calculation():
    try:
        # 从请求体中解析 JSON 数据
        data = request.get_json()
        criteria_matrix = data.get('criteria_matrix')
        alternative_matrices = data.get('alternative_matrices')
        alternative_names = data.get('alternative_names')  # 获取方案名称列表
        
        # 检查数据有效性
        if not criteria_matrix or not alternative_matrices:
            return jsonify({'error': 'Invalid input data'}), 400

        # 转换矩阵为数值类型
        numeric_criteria_matrix = convert_to_numeric(criteria_matrix)
        numeric_alternative_matrices = [convert_to_numeric(matrix) for matrix in alternative_matrices]

        # 创建 AHP 实例并计算优先权重向量
        ahp_instance = AHP(numeric_criteria_matrix, numeric_alternative_matrices)
        priority_vector = ahp_instance.calculate_priority_vector()
        # 找到最优方案的索引并获取相应名称
        best_choice_index = int(np.argmax(priority_vector))
        best_choice_name = alternative_names[best_choice_index]

        # 返回优先权重向量作为 JSON 格式的响应
        result = {
            'priority_vector': priority_vector.tolist(),
            'best_choice_name': best_choice_name  # 以名称形式返回最优方案
        }
        return jsonify(result)

    except ValueError as ve:
        # 处理一致性检验失败的情况
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ahp_bp.route('/save_history', methods=['POST'])
@login_required
def save_history():
    try:
        data = request.get_json()
        request_data = data.get('request_data')
        response_data = data.get('response_data')
        alternative_names = request_data.get('alternative_names')
        criteria_names = request_data.get('criteria_names')
        best_choice_name = response_data.get('best_choice_name')

        if not request_data or not response_data:
            return jsonify({'error': 'Invalid input data'}), 400

        # 创建 AHPHistory 实例
        history_record = AHPHistory(
            user_id=current_user.id,
            alternative_names=','.join(alternative_names),
            criteria_names=','.join(criteria_names),
            request_data=json.dumps(request_data),
            response_data=json.dumps(response_data),
            best_choice_name=best_choice_name
        )

        # 添加并提交到数据库
        db.session.add(history_record)
        db.session.commit()

        return jsonify({'message': 'History saved successfully'}), 201
    except Exception as e:
        db.session.rollback()  # 回滚事务
        return jsonify({'error': str(e)}), 500

@ahp_bp.route('/ahp_history', methods=['GET'])
@login_required
def find_history():
    try:
        # 查询所有历史记录并按创建时间降序排列
        history_records = AHPHistory.query.filter_by(user_id=current_user.id).order_by(AHPHistory.created_at.desc()).all()
        utc = pytz.utc
        beijing_tz = pytz.timezone('Asia/Shanghai')
        # 将记录转换为 JSON 格式
        history_list = [
            {
                'id': record.id,
                'alternative_names': record.alternative_names,
                'criteria_names': record.criteria_names,
                'request_data': record.request_data,
                'response_data': record.response_data,
                'best_choice_name':record.best_choice_name,
                'created_at': utc.localize(record.created_at).astimezone(beijing_tz).isoformat()
            } for record in history_records
        ]

        return jsonify(history_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@ahp_bp.route('/ahp_delete', methods=['GET'])
@login_required
def delete_record():
    try:
        record_id = request.args.get('id', type=int)
        history_record = AHPHistory.query.get(record_id)

        if not history_record:
            return jsonify({'error': 'Record not found'}), 404
        if not history_record.user_id==current_user.id:
            return jsonify({'error': 'You are not allowed to access this record.'}), 403
        db.session.delete(history_record)
        db.session.commit()

        return jsonify({'success': True, 'message': f'Record with id {record_id} deleted'}), 200
    except Exception as e:
        db.session.rollback()  # 回滚事务
        return jsonify({'error': str(e)}), 500

