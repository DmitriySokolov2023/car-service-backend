from flask import Flask
from flask_cors import CORS
from app.api.auth.auth import auth_bp
from app.api.employees.employees import employees_bp
from app.api.role.role import role_bp
from app.api.services.services import services_bp
from app.api.parts.parts import parts_bp
from app.api.clients.clients import clients_bp
from app.api.cars.cars import cars_bp
from app.api.orders.orders import orders_bp
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(role_bp, url_prefix="/api/role")
    app.register_blueprint(services_bp, url_prefix="/api/services")
    app.register_blueprint(parts_bp, url_prefix="/api/parts")
    app.register_blueprint(clients_bp, url_prefix="/api/clients")
    app.register_blueprint(cars_bp, url_prefix="/api/cars")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    return app