from flask import Flask
from flask_cors import CORS
from app.api.auth.auth import auth_bp
from app.api.employees.employees import employees_bp
from app.api.role.role import role_bp
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(role_bp, url_prefix="/api/role")
    return app