from flask import Flask, request, jsonify, Blueprint
from shared_models import DecisionModel,Alternative,Scenario,Payoff,DecisionResult, db
from services.decision_service import MinimaxRegretService

mininmax_regret_bp = Blueprint('mininmax_regret', __name__)

# 获取所有决策模型列表
@mininmax_regret_bp.route('/api/models', methods=['GET'])
def get_all_models():
    """获取所有决策模型列表"""
    db_session = db.session
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    # 获取所有模型，按创建时间倒序排列
    paginated_models = db_session.query(DecisionModel).order_by(DecisionModel.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    models = paginated_models.items
    result = []
    for model in models:
        # 获取每个模型的方案和情景数量
        alternatives_count = db_session.query(Alternative).filter(Alternative.model_id == model.id).count()
        scenarios_count = db_session.query(Scenario).filter(Scenario.model_id == model.id).count()
        
        # 检查是否有分析结果
        has_result = db_session.query(DecisionResult).filter(DecisionResult.model_id == model.id).first() is not None
        
        result.append({
            'id': model.id,
            'name': model.name,
            'description': model.description,
            'created_at': model.created_at.isoformat() if model.created_at else None,
            'updated_at': model.updated_at.isoformat() if model.updated_at else None,
            'alternatives_count': alternatives_count,
            'scenarios_count': scenarios_count,
            'has_result': has_result
        })
    
    return jsonify({
        'models': result,
        'total_pages': paginated_models.pages,
        'current_page': paginated_models.page,
        'total_items': paginated_models.total
    })

# 获取单个模型的详细信息（包含所有数据）
@mininmax_regret_bp.route('/api/models/<int:model_id>/detail', methods=['GET'])
def get_model_detail(model_id):
    """获取决策模型的完整详细信息"""
    db_session = db.session
    
    # 获取模型基本信息
    model = db_session.query(DecisionModel).filter(DecisionModel.id == model_id).first()
    if not model:
        return jsonify({'error': 'Model not found'}), 404
    
    # 获取方案
    alternatives = db_session.query(Alternative).filter(
        Alternative.model_id == model_id
    ).order_by(Alternative.order_index).all()
    
    # 获取情景
    scenarios = db_session.query(Scenario).filter(
        Scenario.model_id == model_id
    ).order_by(Scenario.order_index).all()
    
    # 获取收益矩阵
    payoff_matrix = []
    for alt in alternatives:
        row = []
        for scen in scenarios:
            payoff = db_session.query(Payoff).filter(
                Payoff.model_id == model_id,
                Payoff.alternative_id == alt.id,
                Payoff.scenario_id == scen.id
            ).first()
            row.append(payoff.value if payoff else 0)
        payoff_matrix.append(row)
    
    # 获取决策结果
    result = db_session.query(DecisionResult).filter(DecisionResult.model_id == model_id).first()
    
    # 构建返回数据
    response_data = {
        'id': model.id,
        'name': model.name,
        'description': model.description,
        'created_at': model.created_at.isoformat() if model.created_at else None,
        'updated_at': model.updated_at.isoformat() if model.updated_at else None,
        'alternatives': [
            {
                'id': alt.id,
                'name': alt.name,
                'description': alt.description,
                'order_index': alt.order_index
            } for alt in alternatives
        ],
        'scenarios': [
            {
                'id': scen.id,
                'name': scen.name,
                'description': scen.description,
                'probability': scen.probability,
                'order_index': scen.order_index
            } for scen in scenarios
        ],
        'payoff_matrix': payoff_matrix
    }
    
    # 如果有结果，添加到响应中
    if result:
        # 获取最佳方案的名称
        best_alternative = db_session.query(Alternative).filter(
            Alternative.id == result.best_alternative_id
        ).first()
        
        response_data['result'] = {
            'id': result.id,
            'regret_matrix': result.regret_matrix,
            'max_regrets': result.max_regrets,
            'best_alternative_id': result.best_alternative_id,
            'best_alternative_name': best_alternative.name if best_alternative else result.best_alternative_name,
            'min_max_regret': result.min_max_regret,
            'created_at': result.created_at.isoformat() if result.created_at else None
        }
    
    return jsonify(response_data)

# 删除决策模型
@mininmax_regret_bp.route('/api/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """删除决策模型及其所有相关数据"""
    db_session = db.session
    
    model = db_session.query(DecisionModel).filter(DecisionModel.id == model_id).first()
    if not model:
        return jsonify({'error': 'Model not found'}), 404
    
    try:
        db_session.delete(model)
        db_session.commit()
        return jsonify({'message': 'Model deleted successfully'}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    
@mininmax_regret_bp.route('/api/models', methods=['POST'])
def create_model():
    """创建新的决策模型"""
    data = request.json
    
    model = DecisionModel(
        name=data['name'],
        description=data.get('description', '')
    )
    db.session.add(model)
    db.session.commit()
    db.session.refresh(model)
    
    return jsonify({
        'id': model.id,
        'name': model.name,
        'description': model.description,
        'created_at': model.created_at.isoformat()
    }), 201

@mininmax_regret_bp.route('/api/models/<int:model_id>', methods=['GET'])
def get_model(model_id):
    """获取决策模型详情"""
    model = db.session.query(DecisionModel).filter(DecisionModel.id == model_id).first()
    
    if not model:
        return jsonify({'error': 'Model not found'}), 404
    
    alternatives = db.session.query(Alternative).filter(Alternative.model_id == model_id).all()
    scenarios = db.session.query(Scenario).filter(Scenario.model_id == model_id).all()
    
    return jsonify({
        'id': model.id,
        'name': model.name,
        'description': model.description,
        'alternatives': [{'id': a.id, 'name': a.name} for a in alternatives],
        'scenarios': [{'id': s.id, 'name': s.name} for s in scenarios],
        'created_at': model.created_at.isoformat()
    })

@mininmax_regret_bp.route('/api/models/<int:model_id>/alternatives', methods=['POST'])
def add_alternative(model_id):
    """添加备选方案"""
    data = request.json
    
    # 获取当前最大order_index
    max_order = db.session.query(Alternative).filter(
        Alternative.model_id == model_id
    ).count()
    
    alternative = Alternative(
        model_id=model_id,
        name=data['name'],
        description=data.get('description', ''),
        order_index=max_order
    )
    db.session.add(alternative)
    db.session.commit()
    db.session.refresh(alternative)
    
    return jsonify({
        'id': alternative.id,
        'name': alternative.name,
        'description': alternative.description
    }), 201

@mininmax_regret_bp.route('/api/models/<int:model_id>/scenarios', methods=['POST'])
def add_scenario(model_id):
    """添加情景状态"""
    data = request.json
    
    max_order = db.session.query(Scenario).filter(
        Scenario.model_id == model_id
    ).count()
    
    scenario = Scenario(
        model_id=model_id,
        name=data['name'],
        description=data.get('description', ''),
        probability=data.get('probability'),
        order_index=max_order
    )
    db.session.add(scenario)
    db.session.commit()
    db.session.refresh(scenario)
    
    return jsonify({
        'id': scenario.id,
        'name': scenario.name,
        'description': scenario.description,
        'probability': scenario.probability
    }), 201

@mininmax_regret_bp.route('/api/models/<int:model_id>/payoffs', methods=['POST'])
def update_payoffs(model_id):
    """批量更新收益值"""
    data = request.json  # 期望格式：[[val11, val12, ...], [val21, val22, ...]]
    
    # 获取所有方案和情景
    alternatives = db.session.query(Alternative).filter(Alternative.model_id == model_id).all()
    scenarios = db.session.query(Scenario).filter(Scenario.model_id == model_id).all()
    
    # 验证数据维度
    if len(data) != len(alternatives) or any(len(row) != len(scenarios) for row in data):
        return jsonify({'error': 'Invalid payoff matrix dimensions'}), 400
    
    # 删除旧的收益数据
    db.session.query(Payoff).filter(Payoff.model_id == model_id).delete()
    
    # 添加新的收益数据
    for i, alt in enumerate(alternatives):
        for j, scen in enumerate(scenarios):
            payoff = Payoff(
                model_id=model_id,
                alternative_id=alt.id,
                scenario_id=scen.id,
                value=data[i][j]
            )
            db.session.add(payoff)
    
    db.session.commit()
    
    return jsonify({'message': 'Payoffs updated successfully'}), 200

@mininmax_regret_bp.route('/api/models/<int:model_id>/analyze', methods=['POST'])
def analyze_model(model_id):
    """执行最小化最大遗憾值分析"""
    
    # 获取模型数据
    alt_names, scen_names, payoff_matrix = MinimaxRegretService.get_model_data(db, model_id)
    
    if not alt_names or not scen_names:
        return jsonify({'error': 'Model has no alternatives or scenarios'}), 400
    
    # 执行分析
    result = MinimaxRegretService.find_best_decision(payoff_matrix, alt_names)
    
    # 保存结果
    MinimaxRegretService.save_decision_result(db, model_id, result)
    
    # 添加情景名称到结果
    result['scenario_names'] = scen_names
    
    return jsonify(result)

@mininmax_regret_bp.route('/api/models/<int:model_id>/results', methods=['GET'])
def get_results(model_id):
    """获取决策结果"""
    
    model = db.session.query(DecisionModel).filter(DecisionModel.id == model_id).first()
    if not model:
        return jsonify({'error': 'Model not found'}), 404
    
    result = db.session.query(DecisionResult).filter(DecisionResult.model_id == model_id).first()
    
    if not result:
        return jsonify({'message': 'No results yet'}), 404
    
    return jsonify({
        'regret_matrix': result.regret_matrix,
        'max_regrets': result.max_regrets,
        'best_alternative': {
            'id': result.best_alternative_id,
            'name': result.best_alternative_name
        },
        'min_max_regret': result.min_max_regret,
        'created_at': result.created_at.isoformat()
    })