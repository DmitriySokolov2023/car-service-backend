from flask import Flask
from flask_cors import CORS
from app.api.form_motivations import motivation_bp
from app.api.form_visiting import visiting_bp, visiting_save_bp
from app.api.search_main import search_bp
from app.api.system_house import house_bp
from app.api.system_house_admin import house_admin_bp
from app.api.form_training.form_training_ovz import form_training_ovz
from app.api.form_training.form_training_fb import form_training_fb
from app.api.form_training.form_training_mc import form_training_mc
from app.api.form_training.form_training_sko import form_training_sko
from app.api.events.organization import organizations_bp
from app.api.events.olympiads import olympiads_bp
from app.api.main_get import main_get_bp
from app.api.main_get_for_custom_ui import main_get_custom_bp
from app.api.main_form_survey import main_form_survey_bp
from app.api.form_social_state import main_social_status_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(motivation_bp, url_prefix="/api")
    app.register_blueprint(visiting_bp, url_prefix="/api/form-visiting")
    app.register_blueprint(visiting_save_bp, url_prefix="/api")
    app.register_blueprint(search_bp, url_prefix="/api")
    app.register_blueprint(house_bp, url_prefix="/api")
    app.register_blueprint(house_admin_bp, url_prefix="/api")
    app.register_blueprint(form_training_ovz, url_prefix="/api/form-training-ovz")
    app.register_blueprint(form_training_fb, url_prefix="/api/form-training-fb")
    app.register_blueprint(form_training_mc, url_prefix="/api/form-training-mc")
    app.register_blueprint(form_training_sko, url_prefix="/api/form-training-sko")
    app.register_blueprint(organizations_bp, url_prefix="/api/organizations")
    app.register_blueprint(olympiads_bp, url_prefix="/api/olympiads")
    app.register_blueprint(main_get_bp, url_prefix="/api/main")
    app.register_blueprint(main_get_custom_bp, url_prefix="/api/main/custom")
    app.register_blueprint(main_form_survey_bp, url_prefix="/api/main/form/survey")
    app.register_blueprint(main_social_status_bp, url_prefix="/api/social-status")
    return app