"""
Data import routes
"""

import pandas as pd
from flask import Blueprint, render_template, request, jsonify # type: ignore
from werkzeug.utils import secure_filename # type: ignore
from models.data_store import data_store
from database.operations import create_experiment
from utils.text_preprocessing import fill_missing_pelatihan
from config import GITHUB_TRAINING_URL, GITHUB_JOBS_URL, GITHUB_REALISASI_URL
import os
import tempfile

data_import_bp = Blueprint('data_import', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@data_import_bp.route('/import')
def import_data():
    """Data import page"""
    return render_template('import.html')

@data_import_bp.route('/api/load-data', methods=['POST'])
def api_load_data():
    """Load data from GitHub or uploaded files"""
    try:
        # Check if it's a file upload (multipart/form-data) or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            data_source = request.form.get('source', 'local')
            load_type = request.form.get('type', 'both')
        else:
            data_source = request.json.get('source', 'github')
            load_type = request.json.get('type', 'both')
        
        if data_source == 'github':
            return load_from_github(load_type)
        elif data_source == 'local':
            return load_from_local(load_type)
        else:
            return jsonify({
                'success': False, 
                'message': f'Unknown data source: {data_source}'
            })
    
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Error loading data: {str(e)}'
        }), 500

def load_from_github(load_type):
    """Load data from GitHub URLs"""
    try:
        df_pelatihan = None
        df_lowongan = None
        df_realisasi = None  # NEW
        
        # Load training data
        if load_type in ['both', 'training']:
            print(f"Loading training data from GitHub...")
            df_pelatihan = pd.read_excel(GITHUB_TRAINING_URL)
            df_pelatihan = fill_missing_pelatihan(df_pelatihan)
            data_store.df_pelatihan = df_pelatihan
            print(f"  ✓ Loaded {len(df_pelatihan)} training programs")
        
        # Load job data
        if load_type in ['both', 'jobs']:
            print(f"Loading job data from GitHub...")
            df_lowongan = pd.read_excel(GITHUB_JOBS_URL)
            
            # Check and add vacancy column
            if 'Perkiraan Lowongan' not in df_lowongan.columns:
                print(f"⚠ Adding default vacancy estimates")
                df_lowongan['Perkiraan Lowongan'] = 1
            
            data_store.df_lowongan = df_lowongan
            print(f"  ✓ Loaded {len(df_lowongan)} job positions")
        
        # NEW: Load realisasi data when 'both'
        if load_type == 'both':
            print(f"Loading realisasi data from GitHub...")
            df_realisasi = pd.read_excel(GITHUB_REALISASI_URL)
            
            # Validate required columns
            required_cols = ['Program Pelatihan', 'Jumlah Peserta', 'Penempatan']
            missing_cols = [col for col in required_cols if col not in df_realisasi.columns]
            
            if not missing_cols:
                # Calculate percentage if not present
                if '% Penempatan' not in df_realisasi.columns:
                    df_realisasi['% Penempatan'] = (
                        df_realisasi['Penempatan'] / df_realisasi['Jumlah Peserta'] * 100
                    ).round(2)
                
                data_store.df_realisasi = df_realisasi
                print(f"  ✓ Loaded {len(df_realisasi)} realisasi records")
            else:
                print(f"  ⚠ Realisasi data missing columns: {missing_cols}")
        
        # Create experiment
        training_count = len(df_pelatihan) if df_pelatihan is not None else data_store.get_training_count()
        job_count = len(df_lowongan) if df_lowongan is not None else data_store.get_job_count()
        realisasi_count = len(df_realisasi) if df_realisasi is not None else data_store.get_realisasi_count()
        
        experiment_id = create_experiment(
            "Data Import Session", 
            f"Loaded from GitHub: {load_type}",
            training_count,
            job_count
        )
        data_store.current_experiment_id = experiment_id
        
        print(f"✓ Data loaded successfully (Experiment ID: {experiment_id})")
        
        return jsonify({
            'success': True,
            'message': 'Data loaded successfully from GitHub',
            'training_count': training_count,
            'job_count': job_count,
            'realisasi_count': realisasi_count  # NEW
        })
    
    except Exception as e:
        print(f"✗ Error loading from GitHub: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error loading from GitHub: {str(e)}'
        }), 500
    
def load_from_local(load_type):
    """Load data from uploaded files (training, jobs, realisasi)"""
    try:
        df_pelatihan = None
        df_lowongan = None
        df_realisasi = None

        # === TRAINING ===
        if load_type in ['both', 'training']:
            if 'training_file' not in request.files:
                return jsonify({
                    'success': False,
                    'message': 'Training file not found in upload'
                }), 400

            training_file = request.files['training_file']

            if training_file.filename == '':
                return jsonify({
                    'success': False,
                    'message': 'No training file selected'
                }), 400

            if not allowed_file(training_file.filename):
                return jsonify({
                    'success': False,
                    'message': 'Training file must be .xlsx or .xls format'
                }), 400

            print(f"Processing training file: {training_file.filename}")
            df_pelatihan = process_training_file(training_file)
            data_store.df_pelatihan = df_pelatihan
            print(f"  ✓ Loaded {len(df_pelatihan)} training programs")

        # === JOBS ===
        if load_type in ['both', 'jobs']:
            if 'job_file' not in request.files:
                return jsonify({
                    'success': False,
                    'message': 'Job file not found in upload'
                }), 400

            job_file = request.files['job_file']

            if job_file.filename == '':
                return jsonify({
                    'success': False,
                    'message': 'No job file selected'
                }), 400

            if not allowed_file(job_file.filename):
                return jsonify({
                    'success': False,
                    'message': 'Job file must be .xlsx or .xls format'
                }), 400

            print(f"Processing job file: {job_file.filename}")
            df_lowongan = process_job_file(job_file)

            # Ensure vacancy column exists (same as GitHub logic)
            if 'Perkiraan Lowongan' not in df_lowongan.columns:
                df_lowongan['Perkiraan Lowongan'] = 1

            data_store.df_lowongan = df_lowongan
            print(f"  ✓ Loaded {len(df_lowongan)} job positions")

        # === REALISASI (NEW – parity with GitHub) ===
        if load_type == 'both':
            if 'realisasi_file' not in request.files:
                return jsonify({
                    'success': False,
                    'message': 'Realisasi file not found in upload'
                }), 400

            realisasi_file = request.files['realisasi_file']

            if realisasi_file.filename == '':
                return jsonify({
                    'success': False,
                    'message': 'No realisasi file selected'
                }), 400

            if not allowed_file(realisasi_file.filename):
                return jsonify({
                    'success': False,
                    'message': 'Realisasi file must be .xlsx or .xls format'
                }), 400

            print(f"Processing realisasi file: {realisasi_file.filename}")
            df_realisasi = pd.read_excel(realisasi_file)

            required_cols = ['Program Pelatihan', 'Jumlah Peserta', 'Penempatan']
            missing_cols = [c for c in required_cols if c not in df_realisasi.columns]

            if missing_cols:
                return jsonify({
                    'success': False,
                    'message': f'Missing columns in realisasi file: {", ".join(missing_cols)}'
                }), 400

            if '% Penempatan' not in df_realisasi.columns:
                df_realisasi['% Penempatan'] = (
                    df_realisasi['Penempatan'] / df_realisasi['Jumlah Peserta'] * 100
                ).round(2)

            data_store.df_realisasi = df_realisasi
            print(f"  ✓ Loaded {len(df_realisasi)} realisasi records")

        # === EXPERIMENT ===
        training_count = len(df_pelatihan) if df_pelatihan is not None else data_store.get_training_count()
        job_count = len(df_lowongan) if df_lowongan is not None else data_store.get_job_count()
        realisasi_count = len(df_realisasi) if df_realisasi is not None else data_store.get_realisasi_count()

        experiment_id = create_experiment(
            "Data Import Session",
            f"Loaded from local files: {load_type}",
            training_count,
            job_count
        )

        data_store.current_experiment_id = experiment_id

        print(f"✓ Data loaded successfully (Experiment ID: {experiment_id})")

        return jsonify({
            'success': True,
            'message': 'Data loaded successfully from local files',
            'training_count': training_count,
            'job_count': job_count,
            'realisasi_count': realisasi_count
        })

    except Exception as e:
        print(f"✗ Error loading from local files: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error loading from local files: {str(e)}'
        }), 500

def process_training_file(file):
    """Process uploaded training file"""
    try:
        # Read Excel file directly from file stream
        df = pd.read_excel(file) #, sheet_name="Versi Ringkas Untuk Tesis")
        
        # Validate required columns
        required_columns = ['PROGRAM PELATIHAN', 'Tujuan/Kompetensi'] #, 'Deskripsi Program']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(
                f"Training file is missing required columns: {', '.join(missing_columns)}"
            )
        
        # Apply preprocessing
        df = fill_missing_pelatihan(df)
        
        return df
    
    except ValueError as ve:
        raise ve
    except Exception as e:
        raise Exception(f"Error processing training file: {str(e)}")

def process_job_file(file):
    """Process uploaded job file"""
    try:
        # Read Excel file directly from file stream
        df = pd.read_excel(file) #, sheet_name="petakan ke KBJI")
        
        # Validate required columns
        required_columns = ['Nama Jabatan', 'Deskripsi KBJI', 'Kompetensi']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(
                f"Job file is missing required columns: {', '.join(missing_columns)}"
            )
        
        return df
    
    except ValueError as ve:
        raise ve
    except Exception as e:
        raise Exception(f"Error processing job file: {str(e)}")
    
@data_import_bp.route('/api/load-realisasi', methods=['POST'])
def api_load_realisasi():
    """Load realisasi penempatan data"""
    try:
        data_source = request.json.get('source', 'github')
        
        if data_source == 'github':
            return load_realisasi_from_github()
        elif data_source == 'local':
            return load_realisasi_from_local()
        else:
            return jsonify({
                'success': False,
                'message': f'Unknown data source: {data_source}'
            })
    except Exception as e:
        print(f"✗ Error loading realisasi: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error loading realisasi: {str(e)}'
        }), 500

def load_realisasi_from_github():
    """Load realisasi data from GitHub"""
    try:
        print(f"Loading realisasi data from GitHub...")
        df_realisasi = pd.read_excel(GITHUB_REALISASI_URL)
        
        # Validate required columns
        required_cols = ['Program Pelatihan', 'Jumlah Peserta', 'Penempatan']
        missing_cols = [col for col in required_cols if col not in df_realisasi.columns]
        
        if missing_cols:
            return jsonify({
                'success': False,
                'message': f'Missing required columns: {", ".join(missing_cols)}'
            }), 400
        
        # Calculate percentage if not present
        if '% Penempatan' not in df_realisasi.columns:
            df_realisasi['% Penempatan'] = (
                df_realisasi['Penempatan'] / df_realisasi['Jumlah Peserta'] * 100
            ).round(2)
        
        data_store.df_realisasi = df_realisasi
        print(f"✓ Loaded {len(df_realisasi)} realisasi records")
        
        return jsonify({
            'success': True,
            'message': 'Realisasi data loaded successfully from GitHub',
            'realisasi_count': len(df_realisasi)
        })
    
    except Exception as e:
        print(f"✗ Error loading realisasi from GitHub: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error loading from GitHub: {str(e)}'
        }), 500

def load_realisasi_from_local():
    """Load realisasi from uploaded file"""
    try:
        if 'realisasi_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Realisasi file not found in upload'
            }), 400
        
        realisasi_file = request.files['realisasi_file']
        
        if realisasi_file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No realisasi file selected'
            }), 400
        
        if not allowed_file(realisasi_file.filename):
            return jsonify({
                'success': False,
                'message': 'File must be .xlsx or .xls format'
            }), 400
        
        print(f"Processing realisasi file: {realisasi_file.filename}")
        df_realisasi = pd.read_excel(realisasi_file)
        
        # Validate and calculate
        required_cols = ['Program Pelatihan', 'Jumlah Peserta', 'Penempatan']
        missing_cols = [col for col in required_cols if col not in df_realisasi.columns]
        
        if missing_cols:
            return jsonify({
                'success': False,
                'message': f'Missing columns: {", ".join(missing_cols)}'
            }), 400
        
        if '% Penempatan' not in df_realisasi.columns:
            df_realisasi['% Penempatan'] = (
                df_realisasi['Penempatan'] / df_realisasi['Jumlah Peserta'] * 100
            ).round(2)
        
        data_store.df_realisasi = df_realisasi
        print(f"✓ Loaded {len(df_realisasi)} realisasi records")
        
        return jsonify({
            'success': True,
            'message': 'Realisasi data loaded successfully',
            'realisasi_count': len(df_realisasi)
        })
    
    except Exception as e:
        print(f"✗ Error loading realisasi: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500