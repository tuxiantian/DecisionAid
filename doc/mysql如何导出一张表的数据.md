要导出 MySQL 数据库中某一张表的数据，你可以使用多种工具和方法，比如 `mysqldump` 命令是最常用的工具之一。下面我将详细介绍几种常用的方法来导出单张表的数据：

### 方法 1：使用 `mysqldump` 导出单张表
`mysqldump` 是 MySQL 自带的实用程序，用于导出数据库的结构和数据。你可以使用它来导出整个数据库、特定的表或特定的数据。以下是导出单张表的基本方法：

#### 命令格式：
```sh
mysqldump -u 用户名 -p 数据库名 表名 > 导出文件名.sql
```

#### 示例：
假设你有一个数据库 `decisions_db`，其中包含一张名为 `article` 的表，你想导出这张表的数据和结构到一个 SQL 文件中。

```sh
mysqldump -u root -p decisions_db article > article_dump.sql
```

- **`-u root`**：指定数据库用户名为 `root`。
- **`-p`**：提示你输入密码。你可以直接在命令中输入密码，但这样做有一定的安全隐患。例如：`-p123456`（不建议这样做）。
- **`decisions_db`**：数据库的名称。
- **`article`**：需要导出的表的名称。
- **`> article_dump.sql`**：将输出重定向到一个文件 `article_dump.sql` 中，该文件中包含表的结构和数据。

#### 只导出数据（不包含表结构）：
如果你只想导出表的数据，而不包含表的结构，可以使用 `--no-create-info` 选项：

```sh
mysqldump -u root -p --no-create-info decisions_db article > article_data_only.sql
```

#### 只导出表结构（不包含数据）：
如果你只想导出表的结构，而不导出数据，可以使用 `--no-data` 选项：

```sh
mysqldump -u root -p --no-data decisions_db article > article_structure_only.sql
```

### 方法 2：使用 MySQL 客户端的 `SELECT INTO OUTFILE`
`SELECT INTO OUTFILE` 可以将表的数据导出为一个文本文件，比如 CSV 文件。

#### 命令格式：
```sql
SELECT * FROM 表名 INTO OUTFILE '文件路径' 
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"' 
LINES TERMINATED BY '\n';
```

#### 示例：
假设你有一个表 `article`，你想将其导出为一个 CSV 文件：

```sql
SELECT * FROM article INTO OUTFILE '/path/to/article_data.csv' 
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"' 
LINES TERMINATED BY '\n';
```

- **`'/path/to/article_data.csv'`**：指定输出文件的路径，注意 MySQL 服务器必须对这个路径具有写权限。
- **`FIELDS TERMINATED BY ','`**：字段之间用逗号分隔。
- **`ENCLOSED BY '"'`**：每个字段的内容用双引号括起来。
- **`LINES TERMINATED BY '\n'`**：每一行用换行符分隔。

**注意事项**：
- **文件路径**必须是服务器能访问的路径，因为这个命令是由 MySQL 服务器执行的，不是客户端执行的。
- 你可能需要**写权限**来创建这个文件，通常可以使用 `sudo` 访问数据库存储的文件目录。
- 这个方法会直接写到服务器文件系统中，所以一般在远程服务器环境下，需要确保服务器的路径是可以访问的。

### 方法 3：使用图形化工具导出（如 MySQL Workbench）
如果你使用的是图形化工具，比如 **MySQL Workbench**，也可以很方便地导出表的数据。

1. **打开 MySQL Workbench** 并连接到你的数据库实例。
2. **选择数据库和表**。
3. 右键点击你要导出的表，选择 **"Table Data Export Wizard"** 或 **"Copy to Clipboard"**，你可以选择将表的数据导出为 SQL、CSV 或其他格式。
4. 按向导选择导出的路径、文件类型等，最后完成导出。

### 方法 4：直接导出为 CSV（使用 `SELECT` 语句）
你也可以使用 MySQL 客户端程序，将查询的结果导出到一个 CSV 文件中。

#### 示例：
```sql
SELECT * FROM article
INTO OUTFILE '/var/lib/mysql-files/article_export.csv'
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n';
```

这里的 `INTO OUTFILE` 方式适用于服务器本地，因为 MySQL 会在服务器上执行文件写入，所以 `/var/lib/mysql-files/` 必须是 MySQL 用户可以访问和写入的目录。

### 方法 5：通过 Python 脚本导出数据（适用于程序化控制导出）
如果你有一些编程基础，Python 也可以用来导出 MySQL 表的数据。下面是一个简单的 Python 脚本示例：

```python
import mysql.connector
import csv

# 连接 MySQL 数据库
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='123456',
    database='decisions_db'
)

cursor = conn.cursor()

# 执行查询并导出数据
query = "SELECT * FROM article"
cursor.execute(query)

# 将数据写入 CSV 文件
with open('article_export.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # 写入表头
    writer.writerow([i[0] for i in cursor.description])
    # 写入表数据
    for row in cursor.fetchall():
        writer.writerow(row)

# 关闭连接
cursor.close()
conn.close()
```

- 这个脚本通过 `mysql.connector` 模块连接数据库，执行 `SELECT` 查询并将结果写入 CSV 文件。
- 可以修改连接参数、查询语句或文件名以适应自己的需求。

### 总结
1. **`mysqldump`**：最常用的方法，可以导出单表的结构和数据到 SQL 文件。
2. **`SELECT INTO OUTFILE`**：可以将数据导出为文本文件（如 CSV），直接写入服务器文件系统。
3. **MySQL Workbench**：图形化工具，可以方便地导出单张表的数据。
4. **Python 脚本**：适用于程序化导出，控制更灵活，适合需要定制化的数据导出场景。

根据你实际的需求和环境，可以选择最适合的方法进行导出。如果你只是为了数据备份和迁移，使用 `mysqldump` 是最为常见和推荐的方式；如果你需要将数据导出为 CSV 格式，使用 `SELECT INTO OUTFILE` 或 Python 脚本是不错的选择。