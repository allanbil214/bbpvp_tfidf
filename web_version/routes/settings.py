"""
Settings routes
"""

from flask import Blueprint, render_template, request, jsonify # type: ignore
from models.data_store import data_store
from config import DEFAULT_MATCH_THRESHOLDS

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', 
                         thresholds=data_store.match_thresholds)

@settings_bp.route('/api/get-settings', methods=['GET'])
def api_get_settings():
    """Get current settings"""
    return jsonify({
        'success': True,
        'thresholds': data_store.match_thresholds
    })

@settings_bp.route('/api/save-settings', methods=['POST'])
def api_save_settings():
    """Save settings"""
    try:
        data = request.json
        thresholds = data.get('thresholds')
        
        # Validate thresholds
        if not all(key in thresholds for key in ['excellent', 'very_good', 'good', 'fair']):
            return jsonify({'success': False, 'message': 'Missing threshold values'})
        
        # Validate order (excellent > very_good > good > fair)
        if not (thresholds['excellent'] > thresholds['very_good'] > 
                thresholds['good'] > thresholds['fair'] >= 0):
            return jsonify({'success': False, 
                          'message': 'Thresholds must be in descending order: Excellent > Very Good > Good > Fair ≥ 0'})
        
        # Validate range (0-1)
        if not all(0 <= v <= 1 for v in thresholds.values()):
            return jsonify({'success': False, 
                          'message': 'All thresholds must be between 0 and 1'})
        
        # Save settings
        data_store.match_thresholds = thresholds
        
        print(f"✓ Settings saved: {thresholds}")
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully',
            'thresholds': thresholds
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@settings_bp.route('/api/reset-settings', methods=['POST'])
def api_reset_settings():
    """Reset settings to defaults"""
    try:
        data_store.match_thresholds = DEFAULT_MATCH_THRESHOLDS.copy()
        
        print("✓ Settings reset to defaults")
        
        return jsonify({
            'success': True,
            'message': 'Settings reset to defaults',
            'thresholds': data_store.match_thresholds
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})