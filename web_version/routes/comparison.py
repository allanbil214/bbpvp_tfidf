"""
Cosine vs Jaccard Comparison routes
"""

from flask import Blueprint, render_template, request, jsonify
from models.data_store import data_store
import pandas as pd
import io
from flask import send_file

comparison_bp = Blueprint('comparison', __name__)

@comparison_bp.route('/comparison')
def comparison():
    """Comparison page"""
    has_both = (data_store.has_similarity_matrix() and 
                hasattr(data_store, 'jaccard_matrix') and 
                data_store.jaccard_matrix is not None)
    
    return render_template('comparison.html', has_data=has_both)

@comparison_bp.route('/api/get-comparison', methods=['POST'])
def api_get_comparison():
    """Get comparison between Cosine and Jaccard similarities"""
    try:
        cosine_matrix = data_store.similarity_matrix
        jaccard_matrix = getattr(data_store, 'jaccard_matrix', None)
        
        if cosine_matrix is None or jaccard_matrix is None:
            return jsonify({
                'success': False, 
                'message': 'Both similarity matrices must be calculated first'
            })
        
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        mode = request.json.get('mode', 'all')  # 'all' or 'single'
        min_threshold = float(request.json.get('min_threshold', 0.01))
        training_idx = request.json.get('training_idx')
        job_idx = request.json.get('job_idx')
        
        comparisons = []
        
        if mode == 'single' and training_idx is not None and job_idx is not None:
            # Single pair comparison
            training_idx = int(training_idx)
            job_idx = int(job_idx)
            
            cosine_score = float(cosine_matrix[training_idx, job_idx])
            jaccard_score = float(jaccard_matrix[training_idx, job_idx])
            
            if cosine_score > 0 and jaccard_score > 0:
                comparisons.append({
                    'training_idx': training_idx,
                    'training_name': df_pelatihan.iloc[training_idx]['PROGRAM PELATIHAN'],
                    'job_idx': job_idx,
                    'job_name': df_lowongan.iloc[job_idx]['Nama Jabatan'],
                    'cosine_similarity': cosine_score,
                    'jaccard_similarity': jaccard_score,
                    'difference': abs(cosine_score - jaccard_score),
                    'cosine_percentage': cosine_score * 100,
                    'jaccard_percentage': jaccard_score * 100
                })
        else:
            # All pairs comparison (only non-zero)
            for i in range(len(df_pelatihan)):
                for j in range(len(df_lowongan)):
                    cosine_score = float(cosine_matrix[i, j])
                    jaccard_score = float(jaccard_matrix[i, j])
                    
                    # Only include if BOTH are > threshold
                    if cosine_score >= min_threshold and jaccard_score >= min_threshold:
                        comparisons.append({
                            'training_idx': i,
                            'training_name': df_pelatihan.iloc[i]['PROGRAM PELATIHAN'],
                            'job_idx': j,
                            'job_name': df_lowongan.iloc[j]['Nama Jabatan'],
                            'cosine_similarity': cosine_score,
                            'jaccard_similarity': jaccard_score,
                            'difference': abs(cosine_score - jaccard_score),
                            'cosine_percentage': cosine_score * 100,
                            'jaccard_percentage': jaccard_score * 100
                        })
        
        # Calculate statistics
        if len(comparisons) > 0:
            import numpy as np
            cosine_values = [c['cosine_similarity'] for c in comparisons]
            jaccard_values = [c['jaccard_similarity'] for c in comparisons]
            
            # Calculate correlation
            correlation = np.corrcoef(cosine_values, jaccard_values)[0, 1]
            
            stats = {
                'total_comparisons': len(comparisons),
                'avg_cosine': float(np.mean(cosine_values)),
                'avg_jaccard': float(np.mean(jaccard_values)),
                'avg_difference': float(np.mean([c['difference'] for c in comparisons])),
                'correlation': float(correlation)
            }
        else:
            stats = {
                'total_comparisons': 0,
                'avg_cosine': 0,
                'avg_jaccard': 0,
                'avg_difference': 0,
                'correlation': 0
            }
        
        print(f"✓ Generated {len(comparisons)} comparisons")
        
        return jsonify({
            'success': True,
            'comparisons': comparisons,
            'stats': stats
        })
    
    except Exception as e:
        print(f"✗ Error getting comparison: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@comparison_bp.route('/api/export-comparison', methods=['POST'])
def api_export_comparison():
    """Export comparison to Excel"""
    try:
        comparisons = request.json.get('comparisons', [])
        
        if not comparisons:
            return jsonify({'success': False, 'message': 'No data to export'})
        
        df = pd.DataFrame(comparisons)
        
        output = io.BytesIO()
        df.to_excel(output, index=False, sheet_name='Comparison')
        output.seek(0)
        
        return send_file(output,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name='cosine_vs_jaccard_comparison.xlsx')
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})