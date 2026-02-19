# services/decision_service.py
from typing import List, Dict, Any, Tuple
import numpy as np
from sqlalchemy.orm import Session
from shared_models import DecisionModel, Alternative, Scenario, Payoff, DecisionResult

class MinimaxRegretService:
    """最小化最大遗憾值决策服务"""
    
    @staticmethod
    def calculate_regret_matrix(payoff_matrix: List[List[float]]) -> np.ndarray:
        """
        计算遗憾矩阵
        
        Args:
            payoff_matrix: 收益矩阵，形状为 [n_alternatives, n_scenarios]
                         行代表备选方案，列代表情景状态
        
        Returns:
            遗憾矩阵
        """
        payoff_array = np.array(payoff_matrix)
        n_alternatives, n_scenarios = payoff_array.shape
        
        # 对每个情景，找出最大收益
        max_per_scenario = np.max(payoff_array, axis=0)
        
        # 计算遗憾值：最大收益 - 当前收益
        regret_matrix = max_per_scenario - payoff_array
        
        return regret_matrix
    
    @staticmethod
    def calculate_max_regrets(regret_matrix: np.ndarray) -> List[float]:
        """
        计算每个方案的最大遗憾值
        
        Args:
            regret_matrix: 遗憾矩阵
            
        Returns:
            每个方案的最大遗憾值列表
        """
        return list(np.max(regret_matrix, axis=1))
    
    @staticmethod
    def find_best_decision(payoff_matrix: List[List[float]], 
                          alternative_names: List[str]) -> Dict[str, Any]:
        """
        执行最小化最大遗憾值决策
        
        Args:
            payoff_matrix: 收益矩阵
            alternative_names: 备选方案名称列表
            
        Returns:
            决策结果字典
        """
        # 计算遗憾矩阵
        regret_matrix = MinimaxRegretService.calculate_regret_matrix(payoff_matrix)
        
        # 计算各方案的最大遗憾值
        max_regrets = MinimaxRegretService.calculate_max_regrets(regret_matrix)
        
        # 找出最小最大遗憾值
        min_max_regret = min(max_regrets)
        best_indices = [i for i, val in enumerate(max_regrets) if val == min_max_regret]
        
        # 构建结果
        result = {
            'regret_matrix': regret_matrix.tolist(),
            'max_regrets': max_regrets,
            'min_max_regret': float(min_max_regret),
            'best_alternatives': [
                {
                    'index': idx,
                    'name': alternative_names[idx],
                    'max_regret': max_regrets[idx]
                }
                for idx in best_indices
            ],
            'payoff_matrix': payoff_matrix
        }
        
        return result
    
    @staticmethod
    def save_decision_result(db: Session, model_id: int, result: Dict[str, Any]) -> DecisionResult:
        """保存决策结果到数据库"""
        best_alt = result['best_alternatives'][0]  # 如果有多个最优，取第一个
        
        decision_result = DecisionResult(
            model_id=model_id,
            regret_matrix=result['regret_matrix'],
            max_regrets=result['max_regrets'],
            best_alternative_id=best_alt['index'] + 1,  # 注意：ID可能不是连续的，需要实际查询
            best_alternative_name=best_alt['name'],
            min_max_regret=result['min_max_regret']
        )
        
        db.session.add(decision_result)
        db.session.commit()
        db.session.refresh(decision_result)
        
        return decision_result
    
    @staticmethod
    def get_model_data(db: Session, model_id: int) -> Tuple[List[str], List[str], List[List[float]]]:
        """获取决策模型的数据"""
        model = db.session.query(DecisionModel).filter(DecisionModel.id == model_id).first()
        if not model:
            return [], [], []
        
        # 获取方案和情景，按order_index排序
        alternatives = db.session.query(Alternative).filter(
            Alternative.model_id == model_id
        ).order_by(Alternative.order_index).all()
        
        scenarios = db.session.query(Scenario).filter(
            Scenario.model_id == model_id
        ).order_by(Scenario.order_index).all()
        
        alt_names = [alt.name for alt in alternatives]
        scen_names = [scen.name for scen in scenarios]
        
        # 构建收益矩阵
        payoff_matrix = [[0.0] * len(scenarios) for _ in range(len(alternatives))]
        
        payoffs = db.session.query(Payoff).filter(Payoff.model_id == model_id).all()
        for payoff in payoffs:
            # 找到对应的索引
            alt_index = next((i for i, alt in enumerate(alternatives) if alt.id == payoff.alternative_id), None)
            scen_index = next((i for i, scen in enumerate(scenarios) if scen.id == payoff.scenario_id), None)
            
            if alt_index is not None and scen_index is not None:
                payoff_matrix[alt_index][scen_index] = payoff.value
        
        return alt_names, scen_names, payoff_matrix