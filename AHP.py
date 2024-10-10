import numpy as np

class AHP:
    def __init__(self, criteria_matrix, alternatives_matrices):
        """
        :param criteria_matrix: 成对比较准则的矩阵
        :param alternatives_matrices: 各个准则下的备选方案成对比较矩阵的列表
        """
        self.criteria_matrix = np.array(criteria_matrix)
        self.alternatives_matrices = [np.array(matrix) for matrix in alternatives_matrices]

    def normalize_matrix(self, matrix):
        """归一化成对比较矩阵"""
        column_sum = np.sum(matrix, axis=0)
        return matrix / column_sum

    def calculate_weights(self, normalized_matrix):
        """计算权重向量"""
        return np.mean(normalized_matrix, axis=1)

    def check_consistency(self, matrix):
        """进行一致性检验"""
        n = matrix.shape[0]
        eigenvalues, _ = np.linalg.eig(matrix)
        max_eigenvalue = np.max(eigenvalues)
        CI = (max_eigenvalue - n) / (n - 1)
        
        # RI 随矩阵大小而变化，这里列出常用 RI 值
        RI_dict = {1: 0, 2: 0, 3: 0.58, 4: 0.9, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
        RI = RI_dict.get(n, 1.45)  # 如果n超出范围，默认RI=1.45
        CR = CI / RI if RI != 0 else 0
        
        return CR < 0.1, CR  # 返回是否满足一致性以及一致性比率CR

    def calculate_priority_vector(self):
        """计算最终优先权重向量"""
        # Step 1: 计算准则的权重
        criteria_normalized = self.normalize_matrix(self.criteria_matrix)
        criteria_weights = self.calculate_weights(criteria_normalized)
        

        # Step 2: 检查准则的一致性
        is_consistent, CR = self.check_consistency(self.criteria_matrix)
        if not is_consistent:
            raise ValueError(f"准则矩阵的一致性比率为 {CR}，未通过一致性检验！")

        # Step 3: 计算每个准则下备选方案的权重，并加权求和
        alternative_weights = []
        for index,matrix in enumerate(self.alternatives_matrices):
            normalized_matrix = self.normalize_matrix(matrix)
            weights = self.calculate_weights(normalized_matrix)

            # 检查每个备选方案矩阵的一致性
            is_consistent, CR = self.check_consistency(matrix)
            if not is_consistent:
                raise ValueError(f"备选方案矩阵{index + 1}的一致性比率为 {CR}，未通过一致性检验！")

            alternative_weights.append(weights)

        # 将各个准则权重与备选方案权重相乘，得到最终优先级
        priority_vector = np.dot(criteria_weights, alternative_weights)
        return priority_vector

# 示例：应用 AHP 方法
if __name__ == "__main__":
    # 示例准则成对比较矩阵
    criteria_matrix = [
        [1, 1/3, 3],
        [3, 1, 5],
        [1/3, 1/5, 1]
    ]

    # 示例备选方案的成对比较矩阵（分别对应三个准则）
    alternative_matrices = [
        [
            [1, 2, 5],
            [1/2, 1, 3],
            [1/5, 1/3, 1]
        ],
        [
            [1, 1/4, 3],
            [4, 1, 7],
            [1/3, 1/7, 1]
        ],
        [
            [1, 5, 1/3],
            [1/5, 1, 1/7],
            [3, 7, 1]
        ]
    ]

    # 创建AHP实例并计算优先权重向量
    ahp = AHP(criteria_matrix, alternative_matrices)
    priority_vector = ahp.calculate_priority_vector()

    # 输出最终结果
    print("优先权重向量:", priority_vector)
    print("最佳选择是选项", np.argmax(priority_vector) + 1)