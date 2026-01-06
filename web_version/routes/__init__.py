# routes/__init__.py
"""
Routes package
"""
from routes.main import main_bp
from routes.data_import import data_import_bp
from routes.view_data import view_data_bp  
from routes.preprocessing import preprocessing_bp
from routes.tfidf import tfidf_bp
from routes.recommendations import recommendations_bp
from routes.settings import settings_bp

__all__ = [
    'main_bp',
    'data_import_bp',
    'view_data_bp',  
    'preprocessing_bp',
    'tfidf_bp',
    'recommendations_bp',
    'settings_bp'
]