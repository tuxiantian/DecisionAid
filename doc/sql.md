修改字段的枚举值
```
ALTER TABLE decisions_db.todo_item 
MODIFY COLUMN `type` enum('today','tomorrow','this_week','this_month','one_week','one_month','custom') 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_0900_ai_ci 
NOT NULL;

```