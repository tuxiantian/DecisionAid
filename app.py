from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from ahp_routes import ahp_bp
from ChecklistDecision import checklist_bp
from TodoList import todolist_bp
from article import article_bp
from minio_utils import minio_bp
from BalancedDecisionMaker import balanced_decision_bp
from mermaid_utils import mermaid_bp
import pymysql
from shared_models import db

pymysql.install_as_MySQLdb()

app = Flask(__name__, static_folder='build', template_folder='build')
CORS(app)
app.config.from_pyfile('config.py')
db.init_app(app)
app.register_blueprint(ahp_bp)
app.register_blueprint(checklist_bp)
app.register_blueprint(todolist_bp)
app.register_blueprint(article_bp)
app.register_blueprint(minio_bp)
app.register_blueprint(balanced_decision_bp)
app.register_blueprint(mermaid_bp)

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder + '/static', path)

@app.route('/images/<path:path>')
def image_files(path):
    return send_from_directory(app.static_folder + '/images', path)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
