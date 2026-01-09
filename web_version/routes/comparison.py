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
            }), 400  # ✅ Add status code
        
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        # ✅ ADD: Validate DataFrames
        if df_pelatihan is None or df_lowongan is None:
            return jsonify({
                'success': False,
                'message': 'Data not loaded'
            }), 400
        
        mode = request.json.get('mode', 'all')
        min_threshold = float(request.json.get('min_threshold', 0.01))
        training_idx = request.json.get('training_idx')
        job_idx = request.json.get('job_idx')
        
        comparisons = []
        
        if mode == 'single' and training_idx is not None and job_idx is not None:
            training_idx = int(training_idx)
            job_idx = int(job_idx)
            
            if training_idx >= len(df_pelatihan) or job_idx >= len(df_lowongan):
                return jsonify({
                    'success': False,
                    'message': 'Invalid document indices'
                }), 400
            
            cosine_score = float(cosine_matrix[training_idx, job_idx])
            jaccard_score = float(jaccard_matrix[training_idx, job_idx])
            
            if cosine_score > 0 and jaccard_score > 0:
                comparisons.append({
                    'training_idx': int(training_idx),
                    'training_name': str(df_pelatihan.iloc[training_idx]['PROGRAM PELATIHAN']),
                    'job_idx': int(job_idx),
                    'job_name': str(df_lowongan.iloc[job_idx]['Nama Jabatan']),
                    'cosine_similarity': round(float(cosine_score), 6),
                    'jaccard_similarity': round(float(jaccard_score), 6),
                    'difference': round(float(abs(cosine_score - jaccard_score)), 6),
                    'cosine_percentage': round(float(cosine_score * 100), 2),
                    'jaccard_percentage': round(float(jaccard_score * 100), 2)
                })
        else:
            for i in range(len(df_pelatihan)):
                for j in range(len(df_lowongan)):
                    cosine_score = float(cosine_matrix[i, j])
                    jaccard_score = float(jaccard_matrix[i, j])
                    
                    if cosine_score >= min_threshold and jaccard_score >= min_threshold:
                        comparisons.append({
                            'training_idx': int(i),
                            'training_name': str(df_pelatihan.iloc[i]['PROGRAM PELATIHAN']),
                            'job_idx': int(j),
                            'job_name': str(df_lowongan.iloc[j]['Nama Jabatan']),
                            'cosine_similarity': round(float(cosine_score), 6),
                            'jaccard_similarity': round(float(jaccard_score), 6),
                            'difference': round(float(abs(cosine_score - jaccard_score)), 6),
                            'cosine_percentage': round(float(cosine_score * 100), 2),
                            'jaccard_percentage': round(float(jaccard_score * 100), 2)
                        })
        
        # Calculate statistics
        if len(comparisons) > 0:
            import numpy as np
            cosine_values = [c['cosine_similarity'] for c in comparisons]
            jaccard_values = [c['jaccard_similarity'] for c in comparisons]
            
            if len(comparisons) > 1:
                correlation = np.corrcoef(cosine_values, jaccard_values)[0, 1]
                if np.isnan(correlation):
                    correlation = 0.0
            else:
                correlation = 0.0
            
            stats = {
                'total_comparisons': int(len(comparisons)),
                'avg_cosine': round(float(np.mean(cosine_values)), 6),
                'avg_jaccard': round(float(np.mean(jaccard_values)), 6),
                'avg_difference': round(float(np.mean([c['difference'] for c in comparisons])), 6),
                'correlation': round(float(correlation), 6)
            }
        else:
            stats = {
                'total_comparisons': 0,
                'avg_cosine': 0.0,
                'avg_jaccard': 0.0,
                'avg_difference': 0.0,
                'correlation': 0.0
            }        
        print(f"✓ Generated {len(comparisons)} comparisons")
        
        return jsonify({
            'success': True,
            'comparisons': comparisons,
            'stats': stats
        }), 200
    
    except Exception as e:
        print(f"✗ Error getting comparison: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': str(e)
        }), 500
    
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