"""
TF-IDF and similarity calculation routes
"""

from flask import Blueprint, render_template, request, jsonify # type: ignore
from models.data_store import data_store
from database.operations import save_similarity_matrix, save_tfidf_samples
from utils.similarity import calculate_similarity_matrix, calculate_manual_tfidf

tfidf_bp = Blueprint('tfidf', __name__)

@tfidf_bp.route('/tfidf')
def tfidf():
    """TF-IDF and similarity calculation page"""
    return render_template('tfidf.html',
                         has_data=data_store.has_training_data() and data_store.has_job_data())

@tfidf_bp.route('/api/calculate-similarity', methods=['POST'])
def api_calculate_similarity():
    """Calculate similarity matrix for all documents"""
    try:
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        if df_pelatihan is None or df_lowongan is None:
            return jsonify({'success': False, 'message': 'Data not loaded'})
        
        if 'preprocessed_text' not in df_pelatihan.columns:
            return jsonify({'success': False, 'message': 'Data not preprocessed'})
        
        # Calculate similarity
        similarity_matrix, vectorizer, tfidf_matrix = calculate_similarity_matrix(
            df_pelatihan, df_lowongan
        )
        
        # Store in data store
        data_store.similarity_matrix = similarity_matrix
        
        # Save to database
        experiment_id = data_store.current_experiment_id
        if experiment_id:
            save_similarity_matrix(experiment_id, similarity_matrix, df_pelatihan, df_lowongan)
            save_tfidf_samples(experiment_id, vectorizer, tfidf_matrix, 
                             similarity_matrix, df_pelatihan, df_lowongan)
        
        # Statistics
        avg_similarity = similarity_matrix.mean()
        max_similarity = similarity_matrix.max()
        min_similarity = similarity_matrix.min()
        
        print(f"✓ Similarity matrix calculated: {similarity_matrix.shape}")
        
        return jsonify({
            'success': True,
            'message': 'Similarity calculated successfully',
            'stats': {
                'avg': float(avg_similarity),
                'max': float(max_similarity),
                'min': float(min_similarity),
                'total_calculations': int(similarity_matrix.size)
            }
        })
    
    except Exception as e:
        print(f"✗ Error calculating similarity: {e}")
        return jsonify({'success': False, 'message': str(e)})

@tfidf_bp.route('/api/get-training-programs', methods=['GET'])
def api_get_training_programs():
    """Get list of training programs for dropdown"""
    try:
        df_pelatihan = data_store.df_pelatihan
        
        if df_pelatihan is None:
            return jsonify({'success': False, 'message': 'Training data not loaded'})
        
        programs = []
        for idx, row in df_pelatihan.iterrows():
            programs.append({
                'index': int(idx),
                'name': row['PROGRAM PELATIHAN']
            })
        
        return jsonify({
            'success': True,
            'programs': programs,
            'count': len(programs)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@tfidf_bp.route('/api/tfidf-step', methods=['POST'])
def api_tfidf_step():
    """Execute specific TF-IDF calculation step"""
    try:
        data = request.json
        step = int(data.get('step'))
        training_idx = int(data.get('training_idx'))
        job_idx = int(data.get('job_idx'))
        step_data = data.get('step_data', {})
        
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        if df_pelatihan is None or df_lowongan is None:
            return jsonify({'success': False, 'message': 'Data not loaded'})
        
        if 'preprocessed_text' not in df_pelatihan.columns:
            return jsonify({'success': False, 'message': 'Data not preprocessed'})
        
        # Get documents
        doc1 = df_pelatihan.iloc[training_idx]
        doc2 = df_lowongan.iloc[job_idx]
        
        training_name = doc1['PROGRAM PELATIHAN']
        job_name = doc2['Nama Jabatan']
        
        result = {
            'success': True,
            'training_name': training_name,
            'job_name': job_name
        }
        
        if step == 1:  # Show Tokens
            tokens1 = doc1['stemmed_tokens'] if 'stemmed_tokens' in doc1 else doc1['tokens']
            tokens2 = doc2['stemmed_tokens'] if 'stemmed_tokens' in doc2 else doc2['tokens']
            all_terms = sorted(set(tokens1 + tokens2))
            
            result.update({
                'training_original': doc1['text_features'],
                'job_original': doc2['text_features'],
                'tokens1': tokens1,
                'tokens2': tokens2,
                'all_terms': all_terms,
                'step_data': {
                    'tokens1': tokens1,
                    'tokens2': tokens2,
                    'all_terms': all_terms
                }
            })
            
        elif step in [2, 3, 4, 5, 6]:
            # For other steps, calculate everything at once
            tokens1 = step_data.get('tokens1', doc1.get('stemmed_tokens', []))
            tokens2 = step_data.get('tokens2', doc2.get('stemmed_tokens', []))
            
            calc = calculate_manual_tfidf(tokens1, tokens2)
            
            # Return appropriate data based on step
            if step == 2:  # TF
                result.update({
                    'tf_d1': calc['tf_d1'],
                    'tf_d2': calc['tf_d2'],
                    'tokens1_count': len(tokens1),
                    'tokens2_count': len(tokens2),
                    'step_data': {
                        'tokens1': tokens1,
                        'tokens2': tokens2,
                        'all_terms': calc['all_terms'],
                        'tf_d1': calc['tf_d1'],
                        'tf_d2': calc['tf_d2']
                    }
                })
            elif step == 3:  # DF
                result.update({
                    'df_dict': calc['df_dict'],
                    'tf_d1': calc['tf_d1'],
                    'tf_d2': calc['tf_d2'],
                    'step_data': {
                        'tokens1': tokens1,
                        'tokens2': tokens2,
                        'all_terms': calc['all_terms'],
                        'tf_d1': calc['tf_d1'],
                        'tf_d2': calc['tf_d2'],
                        'df_dict': calc['df_dict']
                    }
                })
            elif step == 4:  # IDF
                result.update({
                    'idf_dict': calc['idf_dict'],
                    'df_dict': calc['df_dict'],
                    'step_data': {
                        'tokens1': tokens1,
                        'tokens2': tokens2,
                        'all_terms': calc['all_terms'],
                        'tf_d1': calc['tf_d1'],
                        'tf_d2': calc['tf_d2'],
                        'df_dict': calc['df_dict'],
                        'idf_dict': calc['idf_dict']
                    }
                })
            elif step == 5:  # TF-IDF
                result.update({
                    'tfidf_d1': calc['tfidf_d1'],
                    'tfidf_d2': calc['tfidf_d2'],
                    'tf_d1': calc['tf_d1'],
                    'tf_d2': calc['tf_d2'],
                    'idf_dict': calc['idf_dict'],
                    'step_data': {
                        'tokens1': tokens1,
                        'tokens2': tokens2,
                        'all_terms': calc['all_terms'],
                        'tf_d1': calc['tf_d1'],
                        'tf_d2': calc['tf_d2'],
                        'df_dict': calc['df_dict'],
                        'idf_dict': calc['idf_dict'],
                        'tfidf_d1': calc['tfidf_d1'],
                        'tfidf_d2': calc['tfidf_d2']
                    }
                })
            elif step == 6:  # Similarity
                result.update({
                    'dot_product': calc['dot_product'],
                    'mag_d1': calc['mag_d1'],
                    'mag_d2': calc['mag_d2'],
                    'similarity': calc['similarity'],
                    'step_data': step_data
                })
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in TF-IDF step {step}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})