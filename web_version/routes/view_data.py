"""
View Data routes
"""

from flask import Blueprint, render_template, jsonify # type: ignore
from models.data_store import data_store
import pandas as pd

view_data_bp = Blueprint('view_data', __name__)

@view_data_bp.route('/view-data')
def view_data():
    """View data page"""
    return render_template('view_data.html',
                         has_training=data_store.has_training_data(),
                         has_jobs=data_store.has_job_data(),
                         has_realisasi=data_store.has_realisasi_data(),
                         training_count=data_store.get_training_count(),
                         job_count=data_store.get_job_count(),
                         realisasi_count=data_store.get_realisasi_count())


@view_data_bp.route('/api/get-data', methods=['POST'])
def api_get_data():
    """Get data for viewing"""
    try:
        from flask import request
        dataset_type = request.json.get('dataset', 'training')
        page = int(request.json.get('page', 1))
        per_page = int(request.json.get('per_page', 10))
        
        if dataset_type == 'training':
            df = data_store.df_pelatihan
            if df is None:
                return jsonify({'success': False, 'message': 'Training data not loaded'})
            
            # Get columns to display
            display_columns = ['NO', 'PROGRAM PELATIHAN', 'Tujuan/Kompetensi']
            
        elif dataset_type == 'job':
            df = data_store.df_lowongan
            if df is None:
                return jsonify({'success': False, 'message': 'Job data not loaded'})
            
            # Get columns to display
            display_columns = ['NO', 'Nama Jabatan', 'Deskripsi KBJI', 'Perkiraan Lowongan']
        
        else:  # realisasi
            df = data_store.df_realisasi
            if df is None:
                return jsonify({'success': False, 'message': 'Realisasi data not loaded'})
            
            # Get columns to display
            display_columns = ['No', 'Kejuruan', 'Program Pelatihan', 'Jumlah Peserta', 'Penempatan', '% Penempatan']
        
        # Calculate pagination
        total_records = len(df)
        total_pages = (total_records + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_records)
        
        # Get page data
        page_df = df.iloc[start_idx:end_idx]
        
        # Convert to records
        records = []
        for idx, row in page_df.iterrows():
            record = {'index': int(idx)}
            for col in display_columns:
                if col in row:
                    value = row[col]
                    # Handle NaN values
                    if pd.isna(value):
                        record[col] = ''
                    else:
                        # Truncate long text for display
                        if isinstance(value, str) and len(value) > 200:
                            record[col] = value[:200] + '...'
                        else:
                            record[col] = str(value)
                else:
                    record[col] = ''
            records.append(record)
        
        return jsonify({
            'success': True,
            'records': records,
            'columns': display_columns,
            'dataset_type': dataset_type,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_records': total_records,
                'total_pages': total_pages,
                'start_idx': start_idx + 1,
                'end_idx': end_idx
            }
        })
    
    except Exception as e:
        print(f"Error getting data: {e}")
        return jsonify({'success': False, 'message': str(e)})

@view_data_bp.route('/api/get-record-detail', methods=['POST'])
def api_get_record_detail():
    """Get full details of a single record"""
    try:
        from flask import request
        dataset_type = request.json.get('dataset', 'training')
        record_idx = int(request.json.get('index'))
        
        if dataset_type == 'training':
            df = data_store.df_pelatihan
            if df is None:
                return jsonify({'success': False, 'message': 'Training data not loaded'})
        elif dataset_type == 'job':
            df = data_store.df_lowongan
            if df is None:
                return jsonify({'success': False, 'message': 'Job data not loaded'})
        else:  # realisasi
            df = data_store.df_realisasi
            if df is None:
                return jsonify({'success': False, 'message': 'Realisasi data not loaded'})
        
        if record_idx >= len(df):
            return jsonify({'success': False, 'message': 'Record index out of range'})
        
        record = df.iloc[record_idx]
        
        # Convert to dict with all columns
        detail = {'index': record_idx}
        for col in df.columns:
            value = record[col]
            if pd.isna(value):
                detail[col] = ''
            elif isinstance(value, (list, dict)):
                detail[col] = str(value)
            else:
                detail[col] = str(value)
        
        # Add dataset type to response
        detail['dataset_type'] = dataset_type
        
        return jsonify({
            'success': True,
            'record': detail
        })
    
    except Exception as e:
        print(f"Error getting record detail: {e}")
        return jsonify({'success': False, 'message': str(e)})

@view_data_bp.route('/api/search-data', methods=['POST'])
def api_search_data():
    """Search data"""
    try:
        from flask import request
        dataset_type = request.json.get('dataset', 'training')
        search_term = request.json.get('search', '').lower()
        
        if dataset_type == 'training':
            df = data_store.df_pelatihan
            search_columns = ['PROGRAM PELATIHAN', 'Tujuan/Kompetensi']
        elif dataset_type == 'job':
            df = data_store.df_lowongan
            search_columns = ['Nama Jabatan', 'Deskripsi KBJI', 'Kompetensi']
        else:  # realisasi
            df = data_store.df_realisasi
            search_columns = ['Kejuruan', 'Program Pelatihan', '% Penempatan']
        
        if df is None:
            return jsonify({'success': False, 'message': 'Data not loaded'})
        
        # Filter records that match search term
        matching_records = []
        for idx, row in df.iterrows():
            match = False
            for col in search_columns:
                if col in row:
                    value = str(row[col]).lower()
                    if search_term in value:
                        match = True
                        break
            
            if match:
                record = {'index': int(idx)}
                if dataset_type == 'realisasi':
                    # For realisasi, show different columns
                    display_columns = ['No', 'Kejuruan', 'Program Pelatihan', 'Jumlah Peserta', 'Penempatan', '% Penempatan']
                    for col in display_columns:
                        if col in row:
                            value = row[col]
                            if pd.isna(value):
                                record[col] = ''
                            else:
                                if isinstance(value, str) and len(value) > 100:
                                    record[col] = value[:100] + '...'
                                else:
                                    record[col] = str(value)
                        else:
                            record[col] = ''
                else:
                    for col in search_columns:
                        if col in row:
                            value = row[col]
                            if pd.isna(value):
                                record[col] = ''
                            else:
                                if isinstance(value, str) and len(value) > 100:
                                    record[col] = value[:100] + '...'
                                else:
                                    record[col] = str(value)
                        else:
                            record[col] = ''
                matching_records.append(record)
        
        return jsonify({
            'success': True,
            'records': matching_records,
            'columns': search_columns if dataset_type != 'realisasi' else ['No', 'Kejuruan', 'Program Pelatihan', 'Jumlah Peserta', 'Penempatan', '% Penempatan'],
            'total_found': len(matching_records),
            'dataset_type': dataset_type
        })
    
    except Exception as e:
        print(f"Error searching data: {e}")
        return jsonify({'success': False, 'message': str(e)})

@view_data_bp.route('/api/get-statistics', methods=['POST'])
def api_get_statistics():
    """Get statistics for realisasi data"""
    try:
        from flask import request
        dataset_type = request.json.get('dataset', 'training')
        
        if dataset_type != 'realisasi':
            return jsonify({'success': True, 'statistics': None})
        
        df = data_store.df_realisasi
        if df is None:
            return jsonify({'success': False, 'message': 'Realisasi data not loaded'})
        
        # Calculate statistics
        statistics = {}
        
        if 'Jumlah Peserta' in df.columns:
            total_peserta = df['Jumlah Peserta'].sum()
            statistics['total_peserta'] = int(total_peserta)
        
        if 'Penempatan' in df.columns:
            total_penempatan = df['Penempatan'].sum()
            statistics['total_penempatan'] = int(total_penempatan)
            
            # Calculate placement rate
            if total_peserta > 0:
                placement_rate = (total_penempatan / total_peserta) * 100
                statistics['placement_rate'] = round(placement_rate, 2)
        
        if '% Penempatan' in df.columns:
            try:
                # Find top 3 programs by placement rate
                df_temp = df.copy()
                # Convert percentage string to float
                df_temp['% Penempatan_float'] = df_temp['% Penempatan'].str.replace('%', '').astype(float)
                top_programs = df_temp.nlargest(3, '% Penempatan_float')
                
                top_programs_list = []
                for _, row in top_programs.iterrows():
                    top_programs_list.append({
                        'program': row['Program Pelatihan'],
                        'rate': row['% Penempatan'],
                        'peserta': int(row['Jumlah Peserta']),
                        'penempatan': int(row['Penempatan'])
                    })
                statistics['top_programs'] = top_programs_list
                
                # Find programs with lowest placement rate (excluding 0%)
                non_zero = df_temp[df_temp['% Penempatan_float'] > 0]
                if len(non_zero) > 0:
                    bottom_programs = non_zero.nsmallest(3, '% Penempatan_float')
                    bottom_programs_list = []
                    for _, row in bottom_programs.iterrows():
                        bottom_programs_list.append({
                            'program': row['Program Pelatihan'],
                            'rate': row['% Penempatan'],
                            'peserta': int(row['Jumlah Peserta']),
                            'penempatan': int(row['Penempatan'])
                        })
                    statistics['bottom_programs'] = bottom_programs_list
            except Exception as e:
                print(f"Error calculating placement rates: {e}")
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
    
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'message': str(e)})