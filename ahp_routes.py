from flask import Blueprint, request, jsonify
import mysql.connector
import json
import numpy as np
from AHP import AHP  # 确保 AHP.py 文件在同一目录或 Python 路径中

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
def save_history():
    try:
        data = request.get_json()
        request_data = data.get('request_data')
        response_data = data.get('response_data')
        alternative_names = request_data.get('alternative_names')
        criteria_names = request_data.get('criteria_names')
        if not request_data or not response_data:
            return jsonify({'error': 'Invalid input data'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        insert_query = "INSERT INTO ahp_history (alternative_names,criteria_names,request_data, response_data) VALUES (%s, %s,%s, %s)"
        print(','.join(alternative_names))
        cursor.execute(insert_query,(','.join(alternative_names),','.join(criteria_names), json.dumps(request_data), json.dumps(response_data)))
        conn.commit()
        
        cursor.close()
        conn.close()

        return jsonify({'message': 'History saved successfully'}), 201
    except Exception as e:
        print("异常信息：", str(e))           # 打印异常信息
        print("异常参数：", e.args)           # 打印异常参数（元组形式）
        return jsonify({'error': str(e)}), 500

@ahp_bp.route('/ahp_history', methods=['GET'])
def find_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ahp_history ORDER BY created_at DESC")
        history = cursor.fetchall()
        
        cursor.close()
        conn.close()

        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@ahp_bp.route('/ahp_delete', methods=['GET'])
def delete_record():
    record_id = request.args.get('id', type=int)
    conn = get_db_connection()
    cursor = conn.cursor()

    # 删除记录
    delete_query = "DELETE FROM ahp_history WHERE id = %s"
    cursor.execute(delete_query, (record_id,))
    conn.commit()

    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Record with id {record_id} deleted'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
