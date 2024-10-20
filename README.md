# DecisionAid
要将 React 前端和 Python 后端（例如 Flask 或 Django）打包在一起，并在其他人笔记本上方便运行，通常需要将前后端都打包到一个项目中，并提供简单的部署方法。具体步骤如下：

### 方案概览

1. **将 React 构建输出与 Python 后端集成**。
2. **使用一个虚拟环境管理 Python 依赖**。
3. **使用一个简单的脚本自动启动前后端**。
4. **生成一个完整的压缩包，其他人可以解压并运行**。

### 详细步骤

#### 1. 构建 React 前端

React 是一个前端框架，编译后生成静态文件，可以将其部署到任何 HTTP 服务器上。

1. **构建 React 应用**：

   在 React 项目目录下运行以下命令来构建生产版本：

   ```bash
   npm run build
   ```

   这个命令会在 `build/` 文件夹中生成静态文件，你可以将这些文件部署到你的 Python 后端中。

2. **将构建的静态文件复制到 Python 项目**：

   假设你的 Python 项目使用 Flask 或 Django 作为后端框架，将生成的 `build/` 目录内容复制到 Flask 或 Django 项目的静态文件目录中，通常可以直接提供这些文件作为前端内容。

#### 2. 在 Python 后端集成 React 构建内容

如果你使用 Flask 或 Django，你可以配置静态文件目录，确保前端内容通过 Python 后端提供。

- **Flask 示例：**

  将 React 的 `build/` 文件夹内容复制到 Flask 的 `static/` 或者 `templates/` 目录中，然后通过 Flask 提供这些静态文件。

  ```python
  from flask import Flask, render_template

  app = Flask(__name__, static_folder='build/static', template_folder='build')

  @app.route('/')
  def index():
      return render_template('index.html')

  if __name__ == '__main__':
      app.run(debug=True)
  ```

- **Django 示例：**

  将 React 的 `build/` 文件夹内容复制到 Django 的静态文件夹中（如 `static/`），并在 `urls.py` 中配置 URL 路径。

  ```python
  from django.shortcuts import render

  def index(request):
      return render(request, 'index.html')
  ```

#### 3. 创建虚拟环境并安装依赖

1. **创建 Python 虚拟环境**：

   在项目的根目录下运行以下命令来创建虚拟环境：

   ```bash
   python -m venv venv
   ```

2. **激活虚拟环境**：

   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux 或 macOS:
     ```bash
     source venv/bin/activate
     ```

3. **安装 Python 后端依赖**：

   在虚拟环境中安装项目的依赖，比如 Flask 或 Django：

   ```bash
   pip install flask  # 或者 Django 等其他依赖
   ```

4. **生成 `requirements.txt`**：

   将项目的 Python 依赖记录到 `requirements.txt` 文件中：

   ```bash
   pip freeze > requirements.txt
   ```

   这个文件可以用于其他用户在他们的环境中安装相同的依赖。

#### 4. 打包项目

现在你的项目有了 React 构建的静态文件和 Python 后端，你可以将整个项目打包为一个压缩文件：

1. **整理目录结构**：
   
   你的项目文件夹应该包含以下内容：

   ```
   my_project/
   ├── build/               # React 构建输出
   ├── venv/                # Python 虚拟环境（可不包含，推荐其他人创建）
   ├── app.py               # Python 后端代码（如 Flask 项目入口）
   ├── requirements.txt     # Python 依赖
   ├── run.sh               # 启动脚本（适用于 Unix 系统）
   └── run.bat              # 启动脚本（适用于 Windows 系统）
   ```

2. **创建启动脚本**：

   - **Windows（run.bat）**：
     ```batch
     @echo off
     REM 激活虚拟环境
     call venv\Scripts\activate
     REM 运行 Python 服务
     python app.py
     ```

   - **Linux/macOS（run.sh）**：
     ```bash
     #!/bin/bash
     # 激活虚拟环境
     source venv/bin/activate
     # 运行 Python 服务
     python app.py
     ```

3. **打包项目**：

   将整个项目文件夹（不包括虚拟环境）压缩成一个 `.zip` 文件，便于发送给他人。为了减少文件大小，可以在压缩前删除 `venv/` 文件夹。

#### 5. 部署并运行项目

当别人拿到这个项目时，他们可以按照以下步骤运行它：

1. **解压缩项目**。

2. **安装依赖**：

   - 进入项目目录并创建虚拟环境：
     ```bash
     python -m venv venv
     ```

   - 激活虚拟环境：
     - Windows:
       ```bash
       venv\Scripts\activate
       ```
     - Linux 或 macOS:
       ```bash
       source venv/bin/activate
       ```

   - 安装依赖：
     ```bash
     pip install -r requirements.txt
     ```

3. **运行项目**：

   - Windows:
     ```bash
     run.bat
     ```

   - Linux/macOS:
     ```bash
     ./run.sh
     ```

   这将自动激活虚拟环境并启动 Python 服务，React 前端通过 Python 后端提供。

### 总结

通过这些步骤，你可以将 React 前端和 Python 后端打包成一个项目，别人可以方便地运行它。创建虚拟环境并提供简单的启动脚本，可以确保项目在其他人的机器上能轻松运行。


根据你使用的 Python 包，`requirements.txt` 文件应该包括你所使用的库及其版本信息。为了生成正确的 `requirements.txt`，你可以手动创建这个文件并添加你所需要的库，或者你可以通过安装好依赖后用 `pip freeze` 自动生成。

### 手动创建 `requirements.txt`

根据你提供的库，基本的 `requirements.txt` 文件内容可以像这样：

```
Flask==2.1.1
Flask-Cors==3.0.10
mysql-connector-python==8.0.27
numpy==1.21.2
```

如果你希望手动创建 `requirements.txt`，你可以选择一个适合的版本或者省略版本号。

- **Flask** 是一个常用的 Python Web 框架。
- **Flask-CORS** 用于处理跨域请求。
- **mysql-connector-python** 用于连接 MySQL 数据库。
- **numpy** 是用于科学计算的库。
  
### 自动生成 `requirements.txt`

1. **安装所有依赖**：

   如果你没有安装这些依赖，可以在虚拟环境中通过 `pip` 安装它们：

   ```bash
   pip install Flask Flask-Cors mysql-connector-python numpy
   ```

2. **生成 `requirements.txt` 文件**：

   安装完所有依赖后，运行以下命令来生成 `requirements.txt` 文件：

   ```bash
   pip freeze > requirements.txt
   ```

   这将根据你当前虚拟环境中的安装情况生成一个 `requirements.txt` 文件，内容会类似如下：

   ```
   Flask==2.1.1
   Flask-Cors==3.0.10
   mysql-connector-python==8.0.27
   numpy==1.21.2
   ```

### 安装依赖

当你或其他人在项目中使用这个 `requirements.txt` 文件时，只需要运行以下命令来安装这些依赖：

```bash
pip install -r requirements.txt
```

### 总结

你可以选择手动编辑 `requirements.txt` 文件并填写必要的依赖，或者通过 `pip freeze` 命令自动生成文件。生成的文件可以帮助其他人或自己在新的环境中快速安装所有依赖。

```
PS C:\Users\tuxia\Documents\python\ahp> venv\Scripts\activate
venv\Scripts\activate : 无法加载文件 C:\Users\tuxia\Documents\python\ahp\venv\Scripts\Activate.ps1，因为在此系统上禁止
运行脚本。有关详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符: 1
+ venv\Scripts\activate
+ ~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) []，PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```
你遇到的是 Windows PowerShell 的执行策略问题，这阻止了脚本（例如 `activate.ps1`）的运行。Windows 默认的 PowerShell 执行策略限制了未签名的脚本运行。

你可以通过更改 PowerShell 的执行策略来解决这个问题。

### 解决方案：更改 PowerShell 的执行策略

1. **以管理员身份运行 PowerShell**：
   - 在 Windows 开始菜单中搜索 "PowerShell"，右键单击 "Windows PowerShell"，然后选择 "以管理员身份运行"。

2. **查看当前的执行策略**：
   在 PowerShell 中运行以下命令以查看当前的执行策略：

   ```powershell
   Get-ExecutionPolicy
   ```

   如果输出的是 `Restricted`，表示未允许任何脚本运行。

3. **临时或永久修改执行策略**：

   - **临时修改**（只在当前会话有效，重启 PowerShell 会恢复默认）：
     
     ```powershell
     Set-ExecutionPolicy Bypass -Scope Process
     ```

   - **永久修改**（适用于当前用户）：
     
     ```powershell
     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
     ```

   解释：
   - `Bypass`：允许所有脚本运行，但仅在当前会话中有效。
   - `RemoteSigned`：本地脚本可以运行，远程下载的脚本必须经过签名。

4. **验证执行策略更改**：
   再次运行 `Get-ExecutionPolicy` 以确认新的执行策略已生效。

5. **激活虚拟环境**：
   现在，你可以在 PowerShell 中运行以下命令来激活 Python 虚拟环境：

   ```powershell
   venv\Scripts\Activate
   ```

### 安全提醒
- 在修改执行策略时，`RemoteSigned` 是较为安全的选择，允许本地脚本运行，但对从互联网下载的脚本需要经过签名验证。
- 使用 `Bypass` 是临时性的，适合短期需要运行未签名的脚本时使用。

### 总结

通过更改 PowerShell 的执行策略，你可以解决激活 Python 虚拟环境时的脚本阻止问题。
生成mermaid图片需要node环境，需要安装mermaid-cli包
```
npm install -g @mermaid-js/mermaid-cli
```
'/generate-mermaid'中需要指定mermaid-cli的安装路径
```
mmdc_path = r'C:\Users\tuxia\AppData\Roaming\npm\mmdc.cmd'
```