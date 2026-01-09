"""
BBPVP Job Matching System - Flask Web Application
Main application entry point
"""

from flask import Flask # type: ignore
from config import SECRET_KEY, MAX_CONTENT_LENGTH

# Import blueprints
from routes.main import main_bp
from routes.data_import import data_import_bp
from routes.view_data import view_data_bp
from routes.preprocessing import preprocessing_bp
from routes.tfidf import tfidf_bp
from routes.jaccard import jaccard_bp
from routes.comparison import comparison_bp
from routes.recommendations import recommendations_bp
from routes.analysis import analysis_bp
from routes.settings import settings_bp

def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(data_import_bp)
    app.register_blueprint(view_data_bp) 
    app.register_blueprint(preprocessing_bp)
    app.register_blueprint(tfidf_bp)
    app.register_blueprint(jaccard_bp)
    app.register_blueprint(comparison_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(settings_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)