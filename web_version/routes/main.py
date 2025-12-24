"""
Main routes (index, database)
"""

from flask import Blueprint, render_template, jsonify # type: ignore
from database.connection import test_db_connection
from config import DB_CONFIG

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@main_bp.route('/database')
def database():
    """Database configuration page"""
    return render_template('database.html', db_config=DB_CONFIG)

@main_bp.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    """Test database connection"""
    success, message = test_db_connection()
    return jsonify({'success': success, 'message': message})