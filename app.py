import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required # type: ignore
from flask_cors import CORS
from ahp_routes import ahp_bp
from ChecklistDecision import checklist_bp
from TodoList import todolist_bp
from article import article_bp
from minio_utils import minio_bp
from BalancedDecision import balanced_decision_bp
from mermaid_utils import mermaid_bp
from logic_errors import logic_errors_bp
from feedback import feedback_bp
from inspirations import inspiration_bp
from reflections import reflections_bp
import pymysql
from shared_models import User,FreezeRecord, db
from datetime import datetime as dt, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
pymysql.install_as_MySQLdb()

app = Flask(__name__, static_folder='build', template_folder='build')
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:3000"}})
app.config.update(
    SESSION_COOKIE_SECURE=False,  # 开发环境可以设为False，生产环境应为True
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',  # 或者 'None' 如果使用跨站
    PERMANENT_SESSION_LIFETIME=timedelta(days=1)  # 会话有效期
)
# 初始化 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong" 

app.config.from_pyfile('config.py')
db.init_app(app)
app.register_blueprint(ahp_bp)
app.register_blueprint(checklist_bp)
app.register_blueprint(todolist_bp)
app.register_blueprint(article_bp)
app.register_blueprint(minio_bp)
app.register_blueprint(balanced_decision_bp)
app.register_blueprint(mermaid_bp)
app.register_blueprint(logic_errors_bp)
app.register_blueprint(feedback_bp)
app.register_blueprint(inspiration_bp)
app.register_blueprint(reflections_bp)


# 加载 RSA 私钥
def load_private_key():
    with open("private_key.pem", "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )
    return private_key

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder + '/static', path)

@app.route('/images/<path:path>')
def image_files(path):
    return send_from_directory(app.static_folder + '/images', path)

# 捕获所有前端路由，将其指向 index.html
@app.route('/<path:path>')
def serve_react_app(path):
    return send_from_directory(app.static_folder, 'index.html')

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

# 自定义未登录时的响应
@login_manager.unauthorized_handler
def unauthorized():
    # 返回 JSON 响应，通知前端用户未登录
    return jsonify({'error': 'Unauthorized', 'message': 'Please log in to access this resource.'}), 401

@app.route('/login', methods=['POST'])
def login():
    # 获取 JSON 数据
    data = request.get_json()
    username = data.get('username')
    encrypted_password = data.get('password')
    # 加载私钥
    private_key = load_private_key()

    # 解密密码
    try:
        private_key = load_private_key()
        password = private_key.decrypt(
            base64.b64decode(encrypted_password),
            padding.PKCS1v15()
        ).decode('utf-8')
    except Exception as e:
        return jsonify({'message': '解密失败', 'error': str(e)}), 400

    # 查询用户
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': '用户不存在'}), 401
    # 检查账户冻结状态
    if user.is_frozen:
        if user.frozen_until is None:  # 永久冻结
            return jsonify({
                'message': '账户已被永久冻结',
                'is_frozen': True,
                'frozen_until': None,
                'reason': get_latest_freeze_reason(user.id)  # 获取最新冻结原因
            }), 403
        elif user.frozen_until > dt.utcnow():  # 临时冻结未到期
            return jsonify({
                'message': f'账户已被冻结，解冻时间: {user.frozen_until.strftime("%Y-%m-%d %H:%M:%S")}',
                'is_frozen': True,
                'frozen_until': user.frozen_until.isoformat(),
                'reason': get_latest_freeze_reason(user.id)
            }), 403
        else:  # 冻结已过期但标记未清除
            user.is_frozen = False
            user.frozen_until = None
            db.session.commit()
    # 验证用户和密码
    if user and user.check_password(password):
        login_user(user)  # 登录用户
        print({'message': 'Login successful', 'user_id': user.id,'username':username,
            'is_frozen': False})
        return jsonify({'message': 'Login successful', 'user_id': user.id,'username':username,
            'is_frozen': False}), 200

    # 登录失败
    return jsonify({'message': '用户名或密码错误'}), 401

def get_latest_freeze_reason(user_id):
    """获取用户最新的冻结原因"""
    record = FreezeRecord.query.filter_by(
        user_id=user_id, 
        action='freeze'
    ).order_by(FreezeRecord.created_at.desc()).first()
    return record.reason if record else '未知原因'

@app.route('/logout', methods=['POST'])
def logout():
    logout_user()  # 使用 Flask-Login 的 logout_user() 退出用户
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    avatar_url = data.get('avatar_url', None)  # 可选头像字段

    # 检查必填字段
    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required.'}), 400

    # 检查是否有重复用户
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'Username or email already exists.'}), 400

    # 创建新用户
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        avatar_url=avatar_url
    )

    # 添加到数据库
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully.'}), 201


# 使用 current_user 的示例
@app.route('/profile')
@login_required
def profile():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
