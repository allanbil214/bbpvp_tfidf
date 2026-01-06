"""
View Data routes
"""

from flask import Blueprint, render_template, jsonify # type: ignore
from models.data_store import data_store

view_data_bp = Blueprint('view_data', __name__)

@view_data_bp.route('/view-data')
def view_data():
    """View data page"""
    return render_template('view_data.html',
                         has_training=data_store.has_training_data(),
                         has_jobs=data_store.has_job_data(),
                         training_count=data_store.get_training_count(),
                         job_count=data_store.get_job_count())

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
            display_columns = ['PROGRAM PELATIHAN', 'Tujuan/Kompetensi', 'Deskripsi Program']
            
        else:  # job
            df = data_store.df_lowongan
            if df is None:
                return jsonify({'success': False, 'message': 'Job data not loaded'})
            
            # Get columns to display
            display_columns = ['Nama Jabatan', 'Deskripsi KBJI', 'Kompetensi']
        
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
                    # Truncate long text for display
                    if isinstance(value, str) and len(value) > 200:
                        record[col] = value[:200] + '...'
                    else:
                        record[col] = str(value) if value is not None else ''
                else:
                    record[col] = ''
            records.append(record)
        
        return jsonify({
            'success': True,
            'records': records,
            'columns': display_columns,
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
        else:
            df = data_store.df_lowongan
            if df is None:
                return jsonify({'success': False, 'message': 'Job data not loaded'})
        
        if record_idx >= len(df):
            return jsonify({'success': False, 'message': 'Record index out of range'})
        
        record = df.iloc[record_idx]
        
        # Convert to dict with all columns
        detail = {'index': record_idx}
        for col in df.columns:
            value = record[col]
            if isinstance(value, (list, dict)):
                detail[col] = str(value)
            else:
                detail[col] = str(value) if value is not None else ''
        
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
            search_columns = ['PROGRAM PELATIHAN', 'Tujuan/Kompetensi', 'Deskripsi Program']
        else:
            df = data_store.df_lowongan
            search_columns = ['Nama Jabatan', 'Deskripsi KBJI', 'Kompetensi']
        
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
                for col in search_columns:
                    if col in row:
                        value = row[col]
                        if isinstance(value, str) and len(value) > 200:
                            record[col] = value[:200] + '...'
                        else:
                            record[col] = str(value) if value is not None else ''
                    else:
                        record[col] = ''
                matching_records.append(record)
        
        return jsonify({
            'success': True,
            'records': matching_records,
            'columns': search_columns,
            'total_found': len(matching_records)
        })
    
    except Exception as e:
        print(f"Error searching data: {e}")
        return jsonify({'success': False, 'message': str(e)})