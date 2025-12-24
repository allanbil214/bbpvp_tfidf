"""
Data import routes
"""

import pandas as pd
from flask import Blueprint, render_template, request, jsonify # type: ignore
from models.data_store import data_store
from database.operations import create_experiment
from utils.text_preprocessing import fill_missing_pelatihan
from config import GITHUB_TRAINING_URL, GITHUB_JOBS_URL

data_import_bp = Blueprint('data_import', __name__)

@data_import_bp.route('/import')
def import_data():
    """Data import page"""
    return render_template('import.html')

@data_import_bp.route('/api/load-data', methods=['POST'])
def api_load_data():
    """Load data from GitHub or uploaded files"""
    try:
        data_source = request.json.get('source', 'github')
        
        if data_source == 'github':
            # Load training data
            df_pelatihan = pd.read_excel(GITHUB_TRAINING_URL, sheet_name="Versi Ringkas Untuk Tesis")
            df_pelatihan = fill_missing_pelatihan(df_pelatihan)
            
            # Load job data
            df_lowongan = pd.read_excel(GITHUB_JOBS_URL, sheet_name="petakan ke KBJI")
            
            # Store in data store
            data_store.df_pelatihan = df_pelatihan
            data_store.df_lowongan = df_lowongan
            
            # Create experiment
            experiment_id = create_experiment(
                "Data Import Session", 
                f"Loaded {len(df_pelatihan)} training programs and {len(df_lowongan)} jobs",
                len(df_pelatihan),
                len(df_lowongan)
            )
            data_store.current_experiment_id = experiment_id
            
            print(f"✓ Data loaded successfully:")
            print(f"  - Training programs: {len(df_pelatihan)}")
            print(f"  - Job positions: {len(df_lowongan)}")
            print(f"  - Experiment ID: {experiment_id}")
            
            return jsonify({
                'success': True,
                'message': 'Data loaded successfully',
                'training_count': len(df_pelatihan),
                'job_count': len(df_lowongan)
            })
        else:
            return jsonify({'success': False, 'message': 'File upload not implemented yet'})
    
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return jsonify({'success': False, 'message': str(e)})