"""
Recommendations routes
"""

import io
import numpy as np
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file # type: ignore
from models.data_store import data_store
from database.operations import save_recommendations, complete_experiment

recommendations_bp = Blueprint('recommendations', __name__)

@recommendations_bp.route('/recommendations')
def recommendations():
    """Recommendations page"""
    return render_template('recommendations.html',
                         has_similarity=data_store.has_similarity_matrix())

@recommendations_bp.route('/api/get-job-positions', methods=['GET'])
def api_get_job_positions():
    """Get list of job positions for dropdown"""
    try:
        df_lowongan = data_store.df_lowongan
        
        if df_lowongan is None:
            return jsonify({'success': False, 'message': 'Job data not loaded'})
        
        jobs = []
        for idx, row in df_lowongan.iterrows():
            jobs.append({
                'index': int(idx),
                'name': row['Nama Jabatan']
            })
        
        print(f"✓ Returning {len(jobs)} job positions")
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'count': len(jobs)
        })
    
    except Exception as e:
        print(f"✗ Error getting job positions: {e}")
        return jsonify({'success': False, 'message': str(e)})

@recommendations_bp.route('/api/get-recommendations', methods=['POST'])
def api_get_recommendations():
    """Get recommendations for jobs"""
    try:
        similarity_matrix = data_store.similarity_matrix
        if similarity_matrix is None:
            return jsonify({'success': False, 'message': 'Similarity matrix not calculated'})
        
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        top_n = int(request.json.get('top_n', 3))
        threshold = float(request.json.get('threshold', 0.01))
        job_idx = request.json.get('job_idx')
        
        recommendations = []
        
        if job_idx is not None:
            # Single job
            job_idx = int(job_idx)
            job_name = df_lowongan.iloc[job_idx]['Nama Jabatan']
            similarities = similarity_matrix[:, job_idx]
            
            filtered_indices = [i for i in range(len(similarities)) if similarities[i] >= threshold]
            filtered_indices.sort(key=lambda i: similarities[i], reverse=True)
            top_indices = filtered_indices[:top_n]
            
            for rank, pel_idx in enumerate(top_indices, 1):
                recommendations.append({
                    'Job_Index': job_idx,
                    'Job_Name': job_name,
                    'Rank': rank,
                    'Training_Index': int(pel_idx),
                    'Training_Program': df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN'],
                    'Similarity_Score': float(similarities[pel_idx]),
                    'Similarity_Percentage': float(similarities[pel_idx] * 100)
                })
        else:
            # All jobs
            for job_idx in range(len(df_lowongan)):
                job_name = df_lowongan.iloc[job_idx]['Nama Jabatan']
                similarities = similarity_matrix[:, job_idx]
                
                top_indices = np.argsort(similarities)[::-1]
                filtered_indices = [idx for idx in top_indices if similarities[idx] >= threshold][:top_n]
                
                for rank, pel_idx in enumerate(filtered_indices, 1):
                    recommendations.append({
                        'Job_Index': job_idx,
                        'Job_Name': job_name,
                        'Rank': rank,
                        'Training_Index': int(pel_idx),
                        'Training_Program': df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN'],
                        'Similarity_Score': float(similarities[pel_idx]),
                        'Similarity_Percentage': float(similarities[pel_idx] * 100)
                    })
        
        # Save to database - ALWAYS save, whether single or all jobs
        experiment_id = data_store.current_experiment_id
        if experiment_id and len(recommendations) > 0:
            try:
                print(f"Saving {len(recommendations)} recommendations to database...")
                save_recommendations(experiment_id, recommendations, data_store.match_thresholds)
                
                # Only complete experiment if it's "all jobs" mode
                if job_idx is None:
                    complete_experiment(experiment_id)
                    print("✓ Experiment marked as completed")
                
                print("✓ Recommendations saved to database")
            except Exception as e:
                print(f"✗ Error saving recommendations: {e}")
                # Don't fail the request, just log the error
        else:
            if not experiment_id:
                print("⚠ Warning: No experiment_id found, recommendations not saved to database")
            if len(recommendations) == 0:
                print("⚠ Warning: No recommendations to save")
        
        print(f"✓ Generated {len(recommendations)} recommendations")
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    
    except Exception as e:
        print(f"✗ Error getting recommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})
    
@recommendations_bp.route('/api/export-recommendations', methods=['POST'])
def api_export_recommendations():
    """Export recommendations to Excel or CSV"""
    try:
        recommendations = request.json.get('recommendations')
        format_type = request.json.get('format', 'excel')
        
        if not recommendations:
            return jsonify({'success': False, 'message': 'No recommendations to export'})
        
        df = pd.DataFrame(recommendations)
        
        output = io.BytesIO()
        if format_type == 'excel':
            df.to_excel(output, index=False, sheet_name='Recommendations')
            output.seek(0)
            return send_file(output, 
                           mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           as_attachment=True,
                           download_name='recommendations.xlsx')
        else:
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            return send_file(output,
                           mimetype='text/csv',
                           as_attachment=True,
                           download_name='recommendations.csv')
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})