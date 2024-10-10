-- test.ahp_history definition

CREATE TABLE `ahp_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `request_data` json NOT NULL,
  `response_data` json NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `criteria_names` varchar(200) DEFAULT NULL,
  `alternative_names` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--示例数据
INSERT INTO test.ahp_history
(id, request_data, response_data, created_at, criteria_names, alternative_names)
VALUES(3, '{"criteria_names": ["景色", "吃住", "价格"], "criteria_matrix": [["1", "1/3", "3"], ["3", "1", "5"], ["1/3", "1/5", "1"]], "alternative_names": ["北京", "南京", "杭州"], "alternative_matrices": [[["1", "2", "5"], ["1/2", "1", "3"], ["1/5", "1/3", "1"]], [["1", "1/4", "3"], ["4", "1", "7"], ["1/3", "1/7", "1"]], [["1", "5", "1/3"], ["1/5", "1", "1/7"], ["3", "7", "1"]]]}', '{"priority_vector": [0.3164966052987531, 0.532616811758014, 0.15088658294323287], "best_choice_name": "南京"}', '2024-10-04 23:33:57', '景色,吃住,价格', '北京,南京,杭州');