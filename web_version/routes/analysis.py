"""
Market Analysis routes - FIXED VERSION
"""

import numpy as np
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file
from models.data_store import data_store
from utils.text_preprocessing import preprocess_dataframe
from utils.similarity import calculate_similarity_matrix
import io

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analysis')
def analysis():
    """Market Analysis page"""
    return render_template('analysis.html',
                         has_data=data_store.has_realisasi_data() and 
                                 data_store.has_job_data() and
                                 data_store.has_training_data(),
                         realisasi_count=data_store.get_realisasi_count(),
                         training_count=data_store.get_training_count(),
                         job_count=data_store.get_job_count())

@analysis_bp.route('/api/calculate-market-analysis', methods=['POST'])
def api_calculate_market_analysis():
    """Calculate market analysis by matching realisasi to training to jobs"""
    try:
        # Get configuration
        job_similarity_threshold = float(request.json.get('job_threshold', 0.3))
        program_similarity_threshold = float(request.json.get('program_threshold', 0.3)) 
        
        df_realisasi = data_store.df_realisasi
        df_pelatihan = data_store.df_pelatihan
        df_lowongan = data_store.df_lowongan
        
        if df_realisasi is None or df_pelatihan is None or df_lowongan is None:
            return jsonify({
                'success': False,
                'message': 'Required data not loaded. Please import all datasets first.'
            }), 400
        
        # Check if training and job data are preprocessed
        if 'preprocessed_text' not in df_pelatihan.columns or 'preprocessed_text' not in df_lowongan.columns:
            return jsonify({
                'success': False,
                'message': 'Data not preprocessed. Please run preprocessing first.'
            }), 400
        
        print("=" * 80)
        print("CALCULATING MARKET ANALYSIS")
        print("=" * 80)
        
        # Step 1: Preprocess realisasi program names
        print("\n🔍 Step 1: Preprocessing realisasi program names...")
        df_realisasi_preprocessed = preprocess_dataframe(df_realisasi.copy(), 'realisasi')
        
        print(f"   ✓ Preprocessed {len(df_realisasi_preprocessed)} realisasi programs")
        
        # Step 2: Match realisasi programs to training programs
        print("\n🔗 Step 2: Matching realisasi programs to training programs...")
        print(f"   Program similarity threshold: {program_similarity_threshold}")
        
        # Calculate similarity between realisasi and training programs
        all_texts = list(df_realisasi_preprocessed['preprocessed_text']) + list(df_pelatihan['preprocessed_text'])
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        n_realisasi = len(df_realisasi_preprocessed)
        realisasi_vectors = tfidf_matrix[:n_realisasi]
        training_vectors = tfidf_matrix[n_realisasi:]
        
        # Calculate similarity matrix: realisasi x training
        realisasi_to_training_sim = cosine_similarity(realisasi_vectors, training_vectors)
        
        # Step 3: Get existing training-to-jobs similarity
        print("\n💼 Step 3: Using existing training-to-jobs similarity matrix...")
        training_to_jobs_sim = data_store.similarity_matrix
        
        if training_to_jobs_sim is None:
            return jsonify({
                'success': False,
                'message': 'Similarity matrix not calculated. Please calculate TF-IDF similarity first.'
            }), 400
        
        print(f"   ✓ Loaded similarity matrix: {training_to_jobs_sim.shape}")
        
        # Step 4: Calculate market analysis for each realisasi program
        print("\n📊 Step 4: Calculating market analysis...")
        print(f"   Job similarity threshold: {job_similarity_threshold}")
        
        results = []
        unmatched_programs = []
        
        for real_idx, real_row in df_realisasi_preprocessed.iterrows():
            program_name = real_row['Program Pelatihan']
            
            # Skip NaN program names (like the TOTAL row)
            if pd.isna(program_name):
                continue
                
            graduates = int(real_row['Jumlah Peserta'])
            placed = int(real_row['Penempatan'])
            
            # ✅ FIXED: Parse placement rate correctly
            placement_rate_str = str(real_row['% Penempatan'])
            if '%' in placement_rate_str:
                # Already in percentage format (e.g., "50.00%")
                placement_rate = float(placement_rate_str.replace('%', '').strip())
            else:
                # Decimal format (e.g., 0.5) - convert to percentage
                try:
                    placement_rate = float(placement_rate_str) * 100
                except:
                    placement_rate = 0.0
            
            # Find best matching training program
            similarities_to_training = realisasi_to_training_sim[real_idx, :]
            best_training_idx = int(np.argmax(similarities_to_training))
            best_training_score = float(similarities_to_training[best_training_idx])
            
            training_match_name = df_pelatihan.iloc[best_training_idx]['PROGRAM PELATIHAN']
            
            # Get job similarities for this training program
            job_similarities = training_to_jobs_sim[best_training_idx, :]
            
            # ✅ FIXED: Debug print AFTER job_similarities is defined
            if real_idx < 5:
                print(f"\n   DEBUG [{real_idx}]: '{program_name}'")
                print(f"         → Best training match: '{training_match_name}' (confidence: {best_training_score:.3f})")
                print(f"         → Job similarities: min={job_similarities.min():.3f}, max={job_similarities.max():.3f}")
                print(f"         → Jobs above {job_similarity_threshold:.2f}: {np.sum(job_similarities >= job_similarity_threshold)}")
            
            if best_training_score < program_similarity_threshold:
                # Program doesn't match well with any training program
                unmatched_programs.append({
                    'program_name': program_name,
                    'best_match': training_match_name,
                    'confidence': round(best_training_score * 100, 2)
                })
                
                results.append({
                    'program_name': program_name,
                    'graduates': graduates,
                    'placed': placed,
                    'placement_rate': placement_rate,
                    'matching_jobs': 0,
                    'total_vacancies': 0,
                    'market_capacity': 0.0,
                    'gap': placement_rate - 0.0,  # gap = placement_rate - market_capacity
                    'status': 'UNMATCHED',
                    'confidence': round(best_training_score * 100, 2),
                    'training_match': training_match_name,
                    'top_jobs': []
                })
                continue
            
            # Find matching jobs (above threshold)
            matching_job_indices = [i for i, sim in enumerate(job_similarities) 
                                   if sim >= job_similarity_threshold]
            
            # Calculate total vacancies and get job details
            total_vacancies = 0
            top_jobs = []
            
            for job_idx in matching_job_indices:
                job_row = df_lowongan.iloc[job_idx]
                vacancy_count = int(job_row['Perkiraan Lowongan'])
                total_vacancies += vacancy_count
                
                top_jobs.append({
                    'job_name': job_row['Nama Jabatan (Sumber Perusahaan)'],
                    'company_name': job_row.get('NAMA PERUSAHAAN', '-'),  # NEW
                    'similarity': round(float(job_similarities[job_idx]) * 100, 2),
                    'vacancies': vacancy_count
                })
            
            # Sort jobs by similarity
            top_jobs.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Calculate metrics
            market_capacity = (total_vacancies / graduates * 100) if graduates > 0 else 0.0
            gap = placement_rate - market_capacity
            
            # Classify status
            if gap > 20:
                status = 'OVERSUPPLY'
            elif gap > 10:
                status = 'HIGH_EXTERNAL'
            elif gap >= -10:
                status = 'BALANCED'
            elif gap >= -20:
                status = 'UNDERSUPPLY'
            else:
                status = 'CRITICAL_UNDERSUPPLY'
            
            results.append({
                'program_name': program_name,
                'graduates': graduates,
                'placed': placed,
                'placement_rate': placement_rate,
                'matching_jobs': len(matching_job_indices),
                'total_vacancies': total_vacancies,
                'market_capacity': round(market_capacity, 2),
                'gap': round(gap, 2),
                'status': status,
                'confidence': round(best_training_score * 100, 2),
                'training_match': training_match_name,
                'top_jobs': top_jobs[:10]  # Top 10 jobs
            })
            
            if real_idx < 3:
                print(f"   ✓ {program_name}: {len(matching_job_indices)} jobs, {total_vacancies} vacancies, gap={gap:.2f}%")
        
        # Calculate summary statistics
        total_graduates = sum(r['graduates'] for r in results)
        total_placed = sum(r['placed'] for r in results)
        total_vacancies = sum(r['total_vacancies'] for r in results)
        
        overall_placement_rate = (total_placed / total_graduates * 100) if total_graduates > 0 else 0
        overall_market_capacity = (total_vacancies / total_graduates * 100) if total_graduates > 0 else 0
        overall_gap = overall_placement_rate - overall_market_capacity
        
        summary = {
            'total_programs': len(results),
            'total_graduates': total_graduates,
            'total_placed': total_placed,
            'total_vacancies': total_vacancies,
            'overall_placement_rate': round(overall_placement_rate, 2),
            'overall_market_capacity': round(overall_market_capacity, 2),
            'overall_gap': round(overall_gap, 2),
            'matched_programs': len([r for r in results if r['status'] != 'UNMATCHED']),
            'unmatched_programs': len(unmatched_programs)
        }
        
        print("\n" + "=" * 80)
        print("CALCULATION COMPLETE")
        print("=" * 80)
        print(f"✓ Total Programs: {len(results)}")
        print(f"✓ Matched: {summary['matched_programs']}")
        print(f"✓ Unmatched: {summary['unmatched_programs']}")
        print(f"✓ Total Graduates: {total_graduates}")
        print(f"✓ Total Placed: {total_placed} ({overall_placement_rate:.2f}%)")
        print(f"✓ Total Vacancies: {total_vacancies}")
        print(f"✓ Market Capacity: {overall_market_capacity:.2f}%")
        print(f"✓ Overall Gap: {overall_gap:.2f}%")
        print("=" * 80)
        
        response_data = {
            'success': True,
            'message': 'Market analysis calculated successfully',
            'summary': summary,
            'results': results,
            'unmatched': unmatched_programs
        }
        
        print(f"\n✓ Returning response with {len(results)} results")
        
        return jsonify(response_data), 200
    
    except Exception as e:
        print(f"✗ Error calculating market analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error calculating market analysis: {str(e)}'
        }), 500

@analysis_bp.route('/api/export-market-analysis', methods=['POST'])
def api_export_market_analysis():
    """Export market analysis to Excel with enhanced formatting"""
    try:
        data = request.json.get('data', {})
        results = data.get('results', [])
        summary = data.get('summary', {})
        unmatched = data.get('unmatched', [])
        
        if not results:
            return jsonify({
                'success': False,
                'message': 'No data to export'
            }), 400
        
        # Create Excel file
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Summary Statistics
            summary_data = {
                'Metric': [
                    'Total Programs Analyzed',
                    'Programs Matched',
                    'Programs Unmatched',
                    'Total Graduates',
                    'Total Placed',
                    'Overall Placement Rate (%)',
                    'Total Market Vacancies',
                    'Overall Market Capacity (%)',
                    'Overall Gap (%)',
                ],
                'Value': [
                    summary['total_programs'],
                    summary['matched_programs'],
                    summary['unmatched_programs'],
                    summary['total_graduates'],
                    summary['total_placed'],
                    round(summary['overall_placement_rate'], 2),
                    summary['total_vacancies'],
                    round(summary['overall_market_capacity'], 2),
                    round(summary['overall_gap'], 2),
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 2: Detailed Program Analysis (Main Table)
            analysis_data = []
            for result in results:
                analysis_data.append({
                    'Program Name': result['program_name'],
                    'Training Match': result['training_match'],
                    'Match Confidence (%)': result['confidence'],
                    'Graduates': result['graduates'],
                    'Placed': result['placed'],
                    'Placement Rate (%)': round(result['placement_rate'], 2),
                    'Unplaced': result['graduates'] - result['placed'],
                    'Matching Jobs': result['matching_jobs'],
                    'Total Vacancies': result['total_vacancies'],
                    'Market Capacity (%)': round(result['market_capacity'], 2),
                    'Gap (%)': round(result['gap'], 2),
                    'Status': result['status'],
                })
            
            analysis_df = pd.DataFrame(analysis_data)
            analysis_df.to_excel(writer, sheet_name='Program Analysis', index=False)
            
            # Auto-adjust column widths for Program Analysis
            worksheet = writer.sheets['Program Analysis']
            for idx, col in enumerate(analysis_df.columns):
                max_length = max(
                    analysis_df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
            
            # Sheet 3: Matching Jobs Detail (Expanded)
            job_details = []
            for result in results:
                program_name = result['program_name']
                status = result['status']
                
                if result.get('top_jobs') and len(result['top_jobs']) > 0:
                    for job in result['top_jobs']:
                        job_details.append({
                            'Program Name': program_name,
                            'Program Status': status,
                            'Job Name': job['job_name'],
                            'Similarity (%)': job['similarity'],
                            'Vacancies': job['vacancies']
                        })
                else:
                    # Add row even if no jobs matched
                    job_details.append({
                        'Program Name': program_name,
                        'Program Status': status,
                        'Job Name': 'No matching jobs',
                        'Similarity (%)': 0,
                        'Vacancies': 0
                    })
            
            jobs_df = pd.DataFrame(job_details)
            jobs_df.to_excel(writer, sheet_name='Matching Jobs', index=False)
            
            # Auto-adjust column widths for Matching Jobs
            worksheet = writer.sheets['Matching Jobs']
            for idx, col in enumerate(jobs_df.columns):
                max_length = max(
                    jobs_df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
            
            # Sheet 4: Unmatched Programs (if any)
            if unmatched and len(unmatched) > 0:
                unmatched_data = []
                for item in unmatched:
                    unmatched_data.append({
                        'Program Name': item['program_name'],
                        'Best Training Match': item['best_match'],
                        'Confidence (%)': item['confidence'],
                        'Reason': 'Confidence below threshold'
                    })
                
                unmatched_df = pd.DataFrame(unmatched_data)
                unmatched_df.to_excel(writer, sheet_name='Unmatched Programs', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Unmatched Programs']
                for idx, col in enumerate(unmatched_df.columns):
                    max_length = max(
                        unmatched_df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
            
            # Sheet 5: Status Distribution
            status_counts = {}
            for result in results:
                status = result['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            status_data = {
                'Status': list(status_counts.keys()),
                'Count': list(status_counts.values()),
                'Percentage': [round((count / len(results)) * 100, 2) for count in status_counts.values()]
            }
            status_df = pd.DataFrame(status_data)
            status_df = status_df.sort_values('Count', ascending=False)
            status_df.to_excel(writer, sheet_name='Status Distribution', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='market_analysis_report.xlsx'
        )
    
    except Exception as e:
        print(f"✗ Error exporting market analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error exporting: {str(e)}'
        }), 500