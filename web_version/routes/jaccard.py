"""
Jaccard Similarity calculation routes
"""

from flask import Blueprint, render_template, request, jsonify
from models.data_store import data_store
from utils.jaccard import calculate_jaccard_similarity, calculate_jaccard_matrix
import numpy as np

jaccard_bp = Blueprint('jaccard', __name__)

@jaccard_bp.route('/jaccard')
def jaccard():
    """Jaccard Similarity calculation page"""
    return render_template('jaccard.html',
                         has_data=data_store.has_training_data() and data_store.has_job_data())

@jaccard_bp.route('/api/jaccard-step', methods=['POST'])
def api_jaccard_step():
    """Execute specific Jaccard calculation step"""
    try:
        data = request.json
        step = int(data.get('step'))
        training_idx = int(data.get('training_idx'))
        job_idx = int(data.get('job_idx'))
        
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        if df_pelatihan is None or df_lowongan is None:
            return jsonify({'success': False, 'message': 'Data not loaded'})
        
        if 'stemmed_tokens' not in df_pelatihan.columns:
            return jsonify({'success': False, 'message': 'Data not preprocessed'})
        
        # Get documents
        doc1 = df_pelatihan.iloc[training_idx]
        doc2 = df_lowongan.iloc[job_idx]
        
        training_name = doc1['PROGRAM PELATIHAN']
        job_name = doc2['Nama Jabatan']
        
        tokens1 = doc1['stemmed_tokens']
        tokens2 = doc2['stemmed_tokens']
        
        # Calculate Jaccard
        jaccard_result = calculate_jaccard_similarity(tokens1, tokens2)
        
        result = {
            'success': True,
            'training_name': training_name,
            'job_name': job_name,
            'step': step
        }
        
        if step == 1:  # Show Tokens
            result.update({
                'tokens1': jaccard_result['tokens1'],
                'tokens2': jaccard_result['tokens2'],
                'set1': jaccard_result['set1'],
                'set2': jaccard_result['set2'],
                'unique_count1': len(jaccard_result['set1']),
                'unique_count2': len(jaccard_result['set2'])
            })
        elif step == 2:  # Intersection
            result.update({
                'set1': jaccard_result['set1'],
                'set2': jaccard_result['set2'],
                'intersection': jaccard_result['intersection'],
                'intersection_count': jaccard_result['intersection_count']
            })
        elif step == 3:  # Union
            result.update({
                'set1': jaccard_result['set1'],
                'set2': jaccard_result['set2'],
                'union': jaccard_result['union'],
                'union_count': jaccard_result['union_count']
            })
        elif step == 4:  # Calculate Jaccard
            result.update({
                'intersection_count': jaccard_result['intersection_count'],
                'union_count': jaccard_result['union_count'],
                'jaccard_similarity': jaccard_result['jaccard_similarity']
            })
        elif step == 5:  # Show All Steps
            result.update(jaccard_result)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in Jaccard step {step}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@jaccard_bp.route('/api/calculate-jaccard-all', methods=['POST'])
def api_calculate_jaccard_all():
    """Calculate Jaccard similarity for all document pairs"""
    try:
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        if df_pelatihan is None or df_lowongan is None:
            return jsonify({'success': False, 'message': 'Data not loaded'})
        
        if 'stemmed_tokens' not in df_pelatihan.columns:
            return jsonify({'success': False, 'message': 'Data not preprocessed'})
        
        # Calculate Jaccard matrix
        jaccard_matrix = calculate_jaccard_matrix(df_pelatihan, df_lowongan)
        
        # Store in data store
        data_store.jaccard_matrix = jaccard_matrix
        
        # Statistics
        avg_similarity = jaccard_matrix.mean()
        max_similarity = jaccard_matrix.max()
        min_similarity = jaccard_matrix.min()
        
        # Count non-zero similarities
        non_zero_count = np.count_nonzero(jaccard_matrix)
        total_count = jaccard_matrix.size
        
        print(f"✓ Jaccard matrix calculated: {jaccard_matrix.shape}")
        
        return jsonify({
            'success': True,
            'message': 'Jaccard similarity calculated successfully',
            'stats': {
                'avg': float(avg_similarity),
                'max': float(max_similarity),
                'min': float(min_similarity),
                'non_zero_count': int(non_zero_count),
                'total_calculations': int(total_count),
                'non_zero_percentage': float((non_zero_count / total_count) * 100)
            }
        })
    
    except Exception as e:
        print(f"✗ Error calculating Jaccard: {e}")
        return jsonify({'success': False, 'message': str(e)})