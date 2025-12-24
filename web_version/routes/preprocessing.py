"""
Preprocessing routes
"""

from flask import Blueprint, render_template, request, jsonify # type: ignore
from models.data_store import data_store
from database.operations import save_preprocessing_sample
from utils.text_preprocessing import (
    normalize_text, remove_stopwords, tokenize_text, 
    stem_tokens, preprocess_dataframe
)
from config import TOTAL_SAVED_SAMPLE

preprocessing_bp = Blueprint('preprocessing', __name__)

@preprocessing_bp.route('/preprocessing')
def preprocessing():
    """Preprocessing page"""
    return render_template('preprocessing.html',
                         has_training=data_store.has_training_data(),
                         has_jobs=data_store.has_job_data(),
                         training_count=data_store.get_training_count(),
                         job_count=data_store.get_job_count())

@preprocessing_bp.route('/api/preprocess-step', methods=['POST'])
def api_preprocess_step():
    """Show specific preprocessing step"""
    try:
        dataset = request.json.get('dataset')
        row_idx = int(request.json.get('row_idx', 0))
        step = int(request.json.get('step', 0))
        
        # Get data
        if dataset == 'training':
            df = data_store.df_pelatihan
            if df is None:
                return jsonify({'success': False, 'message': 'Training data not loaded'})
            text_col = 'PROGRAM PELATIHAN'
        else:
            df = data_store.df_lowongan
            if df is None:
                return jsonify({'success': False, 'message': 'Job data not loaded'})
            text_col = 'Nama Jabatan'
        
        if row_idx >= len(df):
            return jsonify({'success': False, 'message': 'Row index out of range'})
        
        row = df.iloc[row_idx]
        
        # Create combined text
        if dataset == 'training':
            original = f"{row['Tujuan/Kompetensi']}"
        else:
            original = f"{row.get('Deskripsi KBJI', '')}"
        
        result = {'success': True, 'record_name': row[text_col]}
        
        if step == 0:  # Original
            result['output'] = original
        elif step == 1:  # Normalization
            normalized = normalize_text(original)
            result['output'] = normalized
        elif step == 2:  # Stopword Removal
            normalized = normalize_text(original)
            no_stopwords = remove_stopwords(normalized)
            result['output'] = no_stopwords
        elif step == 3:  # Tokenization
            normalized = normalize_text(original)
            no_stopwords = remove_stopwords(normalized)
            tokens = tokenize_text(no_stopwords)
            result['output'] = tokens
            result['token_count'] = len(tokens)
        elif step == 4:  # Stemming
            normalized = normalize_text(original)
            no_stopwords = remove_stopwords(normalized)
            tokens = tokenize_text(no_stopwords)
            stemmed_tokens = stem_tokens(tokens)
            result['output'] = stemmed_tokens
            result['original_tokens'] = tokens
            result['token_count'] = len(stemmed_tokens)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@preprocessing_bp.route('/api/process-all', methods=['POST'])
def api_process_all():
    """Process all data"""
    try:
        experiment_id = data_store.current_experiment_id
        
        # Process training data
        if data_store.df_pelatihan is not None:
            df = preprocess_dataframe(data_store.df_pelatihan, 'training')
            data_store.df_pelatihan = df
            
            # Save samples
            if experiment_id:
                for idx in range(min(TOTAL_SAVED_SAMPLE, len(df))):
                    save_preprocessing_sample(experiment_id, 'training', idx, df.iloc[idx])
        
        # Process job data
        if data_store.df_lowongan is not None:
            df = preprocess_dataframe(data_store.df_lowongan, 'job')
            data_store.df_lowongan = df
            
            # Save samples
            if experiment_id:
                for idx in range(min(TOTAL_SAVED_SAMPLE, len(df))):
                    save_preprocessing_sample(experiment_id, 'job', idx, df.iloc[idx])
        
        print("✓ All data processed successfully")
        return jsonify({'success': True, 'message': 'All data processed successfully'})
    
    except Exception as e:
        print(f"✗ Error processing data: {e}")
        return jsonify({'success': False, 'message': str(e)})