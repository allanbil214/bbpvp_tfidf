"""
BBPVP Job Matching System - Flask Web Application (FIXED)
Using server-side storage instead of session cookies
"""

from flask import Flask, render_template, request, jsonify, session, send_file
import pandas as pd
import numpy as np
import re
import json
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import io
import os
from functools import wraps

# Try to import Sastrawi
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    factory = StemmerFactory()
    stemmer = factory.create_stemmer()
    SASTRAWI_AVAILABLE = True
except ImportError:
    SASTRAWI_AVAILABLE = False
    print("Warning: Sastrawi not available. Stemming will be skipped.")

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# ============================================================================
# SERVER-SIDE STORAGE (NEW!)
# ============================================================================
# Store data in memory instead of session cookies
DATA_STORE = {
    'df_pelatihan': None,
    'df_lowongan': None,
    'similarity_matrix': None,
    'current_experiment_id': None,
    'match_thresholds': {  # ADD THIS
        'excellent': 0.80,
        'very_good': 0.65,
        'good': 0.50,
        'fair': 0.35
    }
}

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'database': 'bbpvp_thesis',
    'user': 'root',
    'password': '',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# GitHub URLs for data
GITHUB_TRAINING_URL = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/2.%20data%20bersih%20Program%20Pelatihan%20Tahun.xlsx"
GITHUB_JOBS_URL = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/3%20.%20databersih-%20Rekap%20Surat%20Masuk%20dan%20Lowongan%202025.xlsx"

# Indonesian stopwords
STOPWORDS = {
    'dan', 'di', 'ke', 'dari', 'yang', 'untuk', 'pada', 'dengan',
    'dalam', 'adalah', 'ini', 'itu', 'atau', 'oleh', 'sebagai',
    'juga', 'akan', 'telah', 'dapat', 'ada', 'tidak', 'hal',
    'tersebut', 'serta', 'bagi', 'hanya', 'sangat', 'bila',
    'saat', 'kini', 'yaitu', 'dll', 'dsb', 'dst', 'setelah', 
    'mengikuti', 'sesuai', 'pelatihan'
}

CUSTOM_STEM_RULES = {
    'peserta': 'peserta',
    'perawatan': 'rawat',
}

TOTAL_SAVED_SAMPLE = 5

# ============================================================================
# Database Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def test_db_connection():
    """Test database connection"""
    conn = get_db_connection()
    if conn and conn.is_connected():
        info = conn.get_server_info()
        conn.close()
        return True, f"Connected to MySQL Server version {info}"
    return False, "Failed to connect to database"

# ============================================================================
# Text Preprocessing Functions
# ============================================================================

def normalize_text(text):
    """Normalize text: lowercase, remove punctuation and numbers"""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', '', text)
    text = ' '.join(text.split())
    return text

def remove_stopwords(text):
    """Remove Indonesian stopwords"""
    if not text:
        return ""
    words = text.split()
    filtered = [w for w in words if w not in STOPWORDS]
    return ' '.join(filtered)

def tokenize_text(text):
    """Tokenize text into words"""
    if not text:
        return []
    return text.split()

def stem_tokens(tokens):
    """Stem tokens using Sastrawi with custom rules"""
    if not tokens:
        return []
    if SASTRAWI_AVAILABLE:
        stemmed = []
        for token in tokens:
            if token in CUSTOM_STEM_RULES:
                stemmed.append(CUSTOM_STEM_RULES[token])
            else:
                stemmed.append(stemmer.stem(token))
        return stemmed
    return tokens

def fill_missing_pelatihan(df):
    """Fill missing values in training data"""
    def fill_tujuan(row):
        if pd.isna(row['Tujuan/Kompetensi']) or str(row['Tujuan/Kompetensi']).strip() == '':
            program = row['PROGRAM PELATIHAN'].strip()
            return f"Setelah mengikuti pelatihan ini peserta kompeten dalam melaksanakan pekerjaan {program.lower()} sesuai standar dan SOP di tempat kerja."
        return row['Tujuan/Kompetensi']
    
    def fill_deskripsi(row):
        if pd.isna(row['Deskripsi Program']) or str(row['Deskripsi Program']).strip() == '':
            program = row['PROGRAM PELATIHAN'].strip()
            return f"Pelatihan ini adalah pelatihan untuk melaksanakan pekerjaan {program.lower()} sesuai standar dan SOP di tempat kerja."
        return row['Deskripsi Program']
    
    df['Tujuan/Kompetensi'] = df.apply(fill_tujuan, axis=1)
    df['Deskripsi Program'] = df.apply(fill_deskripsi, axis=1)
    return df

# ============================================================================
# Database Operations
# ============================================================================

def create_experiment(name, description=""):
    """Create new experiment in database"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        training_count = len(DATA_STORE['df_pelatihan']) if DATA_STORE['df_pelatihan'] is not None else 0
        job_count = len(DATA_STORE['df_lowongan']) if DATA_STORE['df_lowongan'] is not None else 0
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        experiment_name = f"{name} ({timestamp})"
        
        query = """
        INSERT INTO experiments 
        (experiment_name, description, dataset_training_count, dataset_job_count)
        VALUES (%s, %s, %s, %s)
        """
        
        cursor.execute(query, (experiment_name, description, training_count, job_count))
        conn.commit()
        experiment_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        DATA_STORE['current_experiment_id'] = experiment_id
        return experiment_id
    except Error as e:
        print(f"Error creating experiment: {e}")
        return None

def save_preprocessing_sample(experiment_id, dataset_type, record_index, row):
    """Save preprocessing sample to database"""
    conn = get_db_connection()
    if not conn or not experiment_id:
        return
    
    try:
        cursor = conn.cursor()
        
        record_name = row['PROGRAM PELATIHAN'] if dataset_type == 'training' else row['Nama Jabatan']
        
        query = """
        INSERT INTO preprocessing_samples 
        (experiment_id, dataset_type, record_index, record_name, 
        original_text, normalized_text, stopwords_removed, 
        tokenized, stemmed_text, token_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        token_count = int(row.get('token_count', 0)) if pd.notna(row.get('token_count', 0)) else 0
        
        values = (
            experiment_id,
            dataset_type,
            int(record_index),
            record_name,
            row.get('text_features', ''),
            row.get('normalized', ''),
            row.get('no_stopwords', ''),
            json.dumps(row.get('tokens', [])),
            row.get('stemmed', ''),
            token_count
        )
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error saving preprocessing sample: {e}")

def save_similarity_matrix(experiment_id, similarity_matrix, df_pelatihan, df_lowongan):
    """Save full similarity matrix to database"""
    conn = get_db_connection()
    if not conn or not experiment_id:
        return
    
    try:
        cursor = conn.cursor()
        
        query = """
        INSERT INTO similarity_matrix 
        (experiment_id, training_index, training_name, job_index, job_name, similarity_score)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        batch_data = []
        for job_idx in range(len(df_lowongan)):
            job_name = df_lowongan.iloc[job_idx]['Nama Jabatan']
            for pel_idx in range(len(df_pelatihan)):
                training_name = df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
                similarity = float(similarity_matrix[pel_idx, job_idx])
                
                batch_data.append((
                    experiment_id,
                    int(pel_idx),
                    training_name,
                    int(job_idx),
                    job_name,
                    float(similarity)
                ))
        
        cursor.executemany(query, batch_data)
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error saving similarity matrix: {e}")

def save_recommendations(experiment_id, recommendations):
    """Save recommendations to database"""
    conn = get_db_connection()
    if not conn or not experiment_id:
        return
    
    try:
        cursor = conn.cursor()
        
        query = """
        INSERT INTO recommendations 
        (experiment_id, job_index, job_name, training_index, training_name,
        rank_position, similarity_score, similarity_percentage, match_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        batch_data = []
        for rec in recommendations:
            similarity = rec['Similarity_Score']
            match_level = get_match_level(similarity)  # USE HELPER FUNCTION
            
            batch_data.append((
                experiment_id,
                int(rec['Job_Index']),
                rec['Job_Name'],
                int(rec['Training_Index']),
                rec['Training_Program'],
                int(rec['Rank']),
                float(rec['Similarity_Score']),
                float(rec['Similarity_Percentage']),
                match_level
            ))
        
        cursor.executemany(query, batch_data)
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error saving recommendations: {e}")

def complete_experiment(experiment_id):
    """Mark experiment as completed"""
    conn = get_db_connection()
    if not conn or not experiment_id:
        return
    
    try:
        cursor = conn.cursor()
        cursor.callproc('sp_complete_experiment', [experiment_id])
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error completing experiment: {e}")

def save_tfidf_samples(experiment_id, vectorizer, tfidf_matrix, similarity_matrix, df_pelatihan, df_lowongan):
    """Save sample TF-IDF calculations from sklearn results"""
    conn = get_db_connection()
    if not conn or not experiment_id:
        return
    
    try:
        cursor = conn.cursor()
        
        # Save top 5 samples (or less if fewer jobs)
        sample_count = min(5, len(df_lowongan))
        
        query = """
        INSERT INTO tfidf_calculations 
        (experiment_id, training_index, training_name, job_index, job_name,
        unique_terms_count, terms_json, tfidf_training_json, tfidf_job_json, cosine_similarity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Get feature names (terms)
        feature_names = vectorizer.get_feature_names_out()
        n_pelatihan = len(df_pelatihan)
        
        batch_data = []
        for low_idx in range(sample_count):
            # Get best matching training for this job
            similarities = similarity_matrix[:, low_idx]
            top_pel_idx = int(np.argmax(similarities))
            
            training_name = df_pelatihan.iloc[top_pel_idx]['PROGRAM PELATIHAN']
            job_name = df_lowongan.iloc[low_idx]['Nama Jabatan']
            
            # Get TF-IDF vectors for these documents
            training_vector = tfidf_matrix[top_pel_idx].toarray()[0]
            job_vector = tfidf_matrix[n_pelatihan + low_idx].toarray()[0]
            
            # Build simplified JSON structures (only non-zero values)
            tfidf_training = {term: float(training_vector[i]) 
                            for i, term in enumerate(feature_names) 
                            if training_vector[i] > 0}
            
            tfidf_job = {term: float(job_vector[i]) 
                        for i, term in enumerate(feature_names) 
                        if job_vector[i] > 0}
            
            # Get unique terms from both documents
            unique_terms = sorted(set(list(tfidf_training.keys()) + list(tfidf_job.keys())))
            
            batch_data.append((
                experiment_id,
                int(top_pel_idx),
                training_name,
                int(low_idx),
                job_name,
                len(unique_terms),
                json.dumps(unique_terms),
                json.dumps(tfidf_training),
                json.dumps(tfidf_job),
                float(similarities[top_pel_idx])
            ))
        
        cursor.executemany(query, batch_data)
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✓ Saved {len(batch_data)} TF-IDF calculation samples to database")
        
    except Error as e:
        print(f"✗ Error saving TF-IDF samples: {e}")

def get_match_level(similarity):
    """Get match level based on current thresholds"""
    thresholds = DATA_STORE['match_thresholds']
    
    if similarity >= thresholds['excellent']:
        return 'excellent'
    elif similarity >= thresholds['very_good']:
        return 'very_good'
    elif similarity >= thresholds['good']:
        return 'good'
    elif similarity >= thresholds['fair']:
        return 'fair'
    else:
        return 'weak'

# ============================================================================
# Flask Routes
# ============================================================================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/database')
def database():
    """Database configuration page"""
    return render_template('database.html', db_config=DB_CONFIG)

@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    """Test database connection"""
    success, message = test_db_connection()
    return jsonify({'success': success, 'message': message})

@app.route('/import')
def import_data():
    """Data import page"""
    return render_template('import.html')

@app.route('/api/load-data', methods=['POST'])
def api_load_data():
    """Load data from GitHub or uploaded files"""
    try:
        data_source = request.json.get('source', 'github')
        
        if data_source == 'github':
            # Load training data
            df_pelatihan = pd.read_excel(GITHUB_TRAINING_URL, sheet_name="Versi Ringkas Untuk Tesis")
            df_pelatihan = fill_missing_pelatihan(df_pelatihan)
            
            # Load job data
            df_lowongan = pd.read_excel(GITHUB_JOBS_URL, sheet_name="petakan ke KBJI")
            
            # Store in SERVER-SIDE storage (NOT session)
            DATA_STORE['df_pelatihan'] = df_pelatihan
            DATA_STORE['df_lowongan'] = df_lowongan
            
            # Create experiment
            experiment_id = create_experiment("Data Import Session", 
                            f"Loaded {len(df_pelatihan)} training programs and {len(df_lowongan)} jobs")
            
            print(f"✓ Data loaded successfully:")
            print(f"  - Training programs: {len(df_pelatihan)}")
            print(f"  - Job positions: {len(df_lowongan)}")
            print(f"  - Experiment ID: {experiment_id}")
            
            return jsonify({
                'success': True,
                'message': 'Data loaded successfully',
                'training_count': len(df_pelatihan),
                'job_count': len(df_lowongan)
            })
        else:
            return jsonify({'success': False, 'message': 'File upload not implemented yet'})
    
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/preprocessing')
def preprocessing():
    """Preprocessing page"""
    df_pelatihan = DATA_STORE['df_pelatihan']
    df_lowongan = DATA_STORE['df_lowongan']
    
    return render_template('preprocessing.html',
                         has_training=df_pelatihan is not None,
                         has_jobs=df_lowongan is not None,
                         training_count=len(df_pelatihan) if df_pelatihan is not None else 0,
                         job_count=len(df_lowongan) if df_lowongan is not None else 0)

@app.route('/api/preprocess-step', methods=['POST'])
def api_preprocess_step():
    """Show specific preprocessing step"""
    try:
        dataset = request.json.get('dataset')
        row_idx = int(request.json.get('row_idx', 0))
        step = int(request.json.get('step', 0))
        
        # Get data from SERVER-SIDE storage
        if dataset == 'training':
            df = DATA_STORE['df_pelatihan']
            if df is None:
                return jsonify({'success': False, 'message': 'Training data not loaded'})
            text_col = 'PROGRAM PELATIHAN'
        else:
            df = DATA_STORE['df_lowongan']
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

@app.route('/api/process-all', methods=['POST'])
def api_process_all():
    """Process all data"""
    try:
        experiment_id = DATA_STORE['current_experiment_id']
        
        # Process training data
        df_pelatihan = DATA_STORE['df_pelatihan']
        if df_pelatihan is not None:
            df = df_pelatihan.copy()
            
            df['text_features'] = df['Tujuan/Kompetensi'].fillna('')
            df['normalized'] = df['text_features'].apply(normalize_text)
            df['no_stopwords'] = df['normalized'].apply(remove_stopwords)
            df['tokens'] = df['no_stopwords'].apply(tokenize_text)
            df['stemmed_tokens'] = df['tokens'].apply(stem_tokens)
            df['stemmed'] = df['stemmed_tokens'].apply(lambda x: ' '.join(x))
            df['token_count'] = df['stemmed_tokens'].apply(len)
            df['preprocessed_text'] = df['stemmed']
            
            DATA_STORE['df_pelatihan'] = df
            
            # Save samples
            if experiment_id:
                for idx in range(min(TOTAL_SAVED_SAMPLE, len(df))):
                    save_preprocessing_sample(experiment_id, 'training', idx, df.iloc[idx])
        
        # Process job data
        df_lowongan = DATA_STORE['df_lowongan']
        if df_lowongan is not None:
            df = df_lowongan.copy()
            
            df['text_features'] = df['Deskripsi KBJI'].fillna('')
            df['normalized'] = df['text_features'].apply(normalize_text)
            df['no_stopwords'] = df['normalized'].apply(remove_stopwords)
            df['tokens'] = df['no_stopwords'].apply(tokenize_text)
            df['stemmed_tokens'] = df['tokens'].apply(stem_tokens)
            df['stemmed'] = df['stemmed_tokens'].apply(lambda x: ' '.join(x))
            df['token_count'] = df['stemmed_tokens'].apply(len)
            df['preprocessed_text'] = df['stemmed']
            
            DATA_STORE['df_lowongan'] = df
            
            # Save samples
            if experiment_id:
                for idx in range(min(TOTAL_SAVED_SAMPLE, len(df))):
                    save_preprocessing_sample(experiment_id, 'job', idx, df.iloc[idx])
        
        print("✓ All data processed successfully")
        return jsonify({'success': True, 'message': 'All data processed successfully'})
    
    except Exception as e:
        print(f"✗ Error processing data: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/tfidf')
def tfidf():
    """TF-IDF and similarity calculation page"""
    df_pelatihan = DATA_STORE['df_pelatihan']
    df_lowongan = DATA_STORE['df_lowongan']
    
    return render_template('tfidf.html',
                         has_data=df_pelatihan is not None and df_lowongan is not None)

@app.route('/api/calculate-similarity', methods=['POST'])
def api_calculate_similarity():
    """Calculate similarity matrix for all documents"""
    try:
        df_pelatihan = DATA_STORE['df_pelatihan']
        df_lowongan = DATA_STORE['df_lowongan']
        
        if df_pelatihan is None or df_lowongan is None:
            return jsonify({'success': False, 'message': 'Data not loaded'})
        
        if 'preprocessed_text' not in df_pelatihan.columns:
            return jsonify({'success': False, 'message': 'Data not preprocessed'})
        
        # Combine all texts
        all_texts = list(df_pelatihan['preprocessed_text']) + list(df_lowongan['preprocessed_text'])
        
        # Calculate TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        # Split back
        n_pelatihan = len(df_pelatihan)
        pelatihan_vectors = tfidf_matrix[:n_pelatihan]
        lowongan_vectors = tfidf_matrix[n_pelatihan:]
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(pelatihan_vectors, lowongan_vectors)
        
        # Store in SERVER-SIDE storage
        DATA_STORE['similarity_matrix'] = similarity_matrix
        
        # Save to database
        experiment_id = DATA_STORE['current_experiment_id']
        if experiment_id:
            save_similarity_matrix(experiment_id, similarity_matrix, df_pelatihan, df_lowongan)
            
            # ADD THIS: Save sample TF-IDF calculations
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

@app.route('/recommendations')
def recommendations():
    """Recommendations page"""
    has_similarity = DATA_STORE['similarity_matrix'] is not None
    
    return render_template('recommendations.html',
                         has_similarity=has_similarity)

@app.route('/api/get-job-positions', methods=['GET'])
def api_get_job_positions():
    """Get list of job positions for dropdown"""
    try:
        df_lowongan = DATA_STORE['df_lowongan']
        
        if df_lowongan is None:
            return jsonify({'success': False, 'message': 'Job data not loaded'})
        
        # Create list of job positions with their indices
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

@app.route('/api/get-recommendations', methods=['POST'])
def api_get_recommendations():
    """Get recommendations for jobs"""
    try:
        similarity_matrix = DATA_STORE['similarity_matrix']
        if similarity_matrix is None:
            return jsonify({'success': False, 'message': 'Similarity matrix not calculated'})
        
        df_pelatihan = DATA_STORE['df_pelatihan']
        df_lowongan = DATA_STORE['df_lowongan']
        
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
        
        # Save to database
        experiment_id = DATA_STORE['current_experiment_id']
        if experiment_id and job_idx is None:  # Only save for all jobs
            save_recommendations(experiment_id, recommendations)
            complete_experiment(experiment_id)
        
        print(f"✓ Generated {len(recommendations)} recommendations")
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    
    except Exception as e:
        print(f"✗ Error getting recommendations: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/export-recommendations', methods=['POST'])
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

# Add these routes to your app.py file

@app.route('/api/get-training-programs', methods=['GET'])
def api_get_training_programs():
    """Get list of training programs for dropdown"""
    try:
        df_pelatihan = DATA_STORE['df_pelatihan']
        
        if df_pelatihan is None:
            return jsonify({'success': False, 'message': 'Training data not loaded'})
        
        # Create list of training programs with their indices
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


@app.route('/api/tfidf-step', methods=['POST'])
def api_tfidf_step():
    """Execute specific TF-IDF calculation step"""
    try:
        data = request.json
        step = int(data.get('step'))
        training_idx = int(data.get('training_idx'))
        job_idx = int(data.get('job_idx'))
        step_data = data.get('step_data', {})
        
        df_pelatihan = DATA_STORE['df_pelatihan']
        df_lowongan = DATA_STORE['df_lowongan']
        
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
            
        elif step == 2:  # Calculate TF
            tokens1 = step_data.get('tokens1', [])
            tokens2 = step_data.get('tokens2', [])
            all_terms = step_data.get('all_terms', [])
            
            # Calculate TF for D1
            tf_d1 = {}
            for term in all_terms:
                count = tokens1.count(term)
                tf = count / len(tokens1) if len(tokens1) > 0 else 0
                tf_d1[term] = {'count': count, 'tf': tf}
            
            # Calculate TF for D2
            tf_d2 = {}
            for term in all_terms:
                count = tokens2.count(term)
                tf = count / len(tokens2) if len(tokens2) > 0 else 0
                tf_d2[term] = {'count': count, 'tf': tf}
            
            result.update({
                'tf_d1': tf_d1,
                'tf_d2': tf_d2,
                'tokens1_count': len(tokens1),
                'tokens2_count': len(tokens2),
                'step_data': {
                    'tokens1': tokens1,
                    'tokens2': tokens2,
                    'all_terms': all_terms,
                    'tf_d1': tf_d1,
                    'tf_d2': tf_d2
                }
            })
            
        elif step == 3:  # Calculate DF
            all_terms = step_data.get('all_terms', [])
            tf_d1 = step_data.get('tf_d1', {})
            tf_d2 = step_data.get('tf_d2', {})
            
            df_dict = {}
            for term in all_terms:
                count = 0
                if tf_d1.get(term, {}).get('count', 0) > 0:
                    count += 1
                if tf_d2.get(term, {}).get('count', 0) > 0:
                    count += 1
                df_dict[term] = count
            
            result.update({
                'df_dict': df_dict,
                'tf_d1': tf_d1,
                'tf_d2': tf_d2,
                'step_data': {
                    'tokens1': step_data.get('tokens1'),
                    'tokens2': step_data.get('tokens2'),
                    'all_terms': all_terms,
                    'tf_d1': tf_d1,
                    'tf_d2': tf_d2,
                    'df_dict': df_dict
                }
            })
            
        elif step == 4:  # Calculate IDF
            all_terms = step_data.get('all_terms', [])
            df_dict = step_data.get('df_dict', {})
            
            N = 2  # Total documents
            idf_dict = {}
            for term in all_terms:
                df = df_dict.get(term, 0)
                idf = np.log((N + 1) / (df + 1)) + 1  # smoothing
                idf_dict[term] = idf
            
            result.update({
                'idf_dict': idf_dict,
                'df_dict': df_dict,
                'step_data': {
                    'tokens1': step_data.get('tokens1'),
                    'tokens2': step_data.get('tokens2'),
                    'all_terms': all_terms,
                    'tf_d1': step_data.get('tf_d1'),
                    'tf_d2': step_data.get('tf_d2'),
                    'df_dict': df_dict,
                    'idf_dict': idf_dict
                }
            })
            
        elif step == 5:  # Calculate TF-IDF
            all_terms = step_data.get('all_terms', [])
            tf_d1 = step_data.get('tf_d1', {})
            tf_d2 = step_data.get('tf_d2', {})
            idf_dict = step_data.get('idf_dict', {})
            
            # Calculate TF-IDF for D1
            tfidf_d1 = {}
            for term in all_terms:
                tf = tf_d1.get(term, {}).get('tf', 0)
                idf = idf_dict.get(term, 0)
                tfidf_d1[term] = tf * idf
            
            # Calculate TF-IDF for D2
            tfidf_d2 = {}
            for term in all_terms:
                tf = tf_d2.get(term, {}).get('tf', 0)
                idf = idf_dict.get(term, 0)
                tfidf_d2[term] = tf * idf
            
            result.update({
                'tfidf_d1': tfidf_d1,
                'tfidf_d2': tfidf_d2,
                'tf_d1': tf_d1,
                'tf_d2': tf_d2,
                'idf_dict': idf_dict,
                'step_data': {
                    'tokens1': step_data.get('tokens1'),
                    'tokens2': step_data.get('tokens2'),
                    'all_terms': all_terms,
                    'tf_d1': tf_d1,
                    'tf_d2': tf_d2,
                    'df_dict': step_data.get('df_dict'),
                    'idf_dict': idf_dict,
                    'tfidf_d1': tfidf_d1,
                    'tfidf_d2': tfidf_d2
                }
            })
            
        elif step == 6:  # Calculate Similarity
            all_terms = step_data.get('all_terms', [])
            tfidf_d1 = step_data.get('tfidf_d1', {})
            tfidf_d2 = step_data.get('tfidf_d2', {})
            
            # Create vectors
            vec_d1 = [tfidf_d1.get(term, 0) for term in all_terms]
            vec_d2 = [tfidf_d2.get(term, 0) for term in all_terms]
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec_d1, vec_d2))
            
            # Calculate magnitudes
            mag_d1 = np.sqrt(sum(a * a for a in vec_d1))
            mag_d2 = np.sqrt(sum(b * b for b in vec_d2))
            
            # Calculate cosine similarity
            if mag_d1 > 0 and mag_d2 > 0:
                similarity = dot_product / (mag_d1 * mag_d2)
            else:
                similarity = 0
            
            result.update({
                'dot_product': float(dot_product),
                'mag_d1': float(mag_d1),
                'mag_d2': float(mag_d2),
                'similarity': float(similarity),
                'step_data': step_data  # Keep all previous data
            })
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in TF-IDF step {step}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', 
                         thresholds=DATA_STORE['match_thresholds'])

@app.route('/api/get-settings', methods=['GET'])
def api_get_settings():
    """Get current settings"""
    return jsonify({
        'success': True,
        'thresholds': DATA_STORE['match_thresholds']
    })

@app.route('/api/save-settings', methods=['POST'])
def api_save_settings():
    """Save settings"""
    try:
        data = request.json
        thresholds = data.get('thresholds')
        
        # Validate thresholds
        if not all(key in thresholds for key in ['excellent', 'very_good', 'good', 'fair']):
            return jsonify({'success': False, 'message': 'Missing threshold values'})
        
        # Validate order (excellent > very_good > good > fair)
        if not (thresholds['excellent'] > thresholds['very_good'] > 
                thresholds['good'] > thresholds['fair'] >= 0):
            return jsonify({'success': False, 
                          'message': 'Thresholds must be in descending order: Excellent > Very Good > Good > Fair ≥ 0'})
        
        # Validate range (0-1)
        if not all(0 <= v <= 1 for v in thresholds.values()):
            return jsonify({'success': False, 
                          'message': 'All thresholds must be between 0 and 1'})
        
        # Save settings
        DATA_STORE['match_thresholds'] = thresholds
        
        print(f"✓ Settings saved: {thresholds}")
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully',
            'thresholds': thresholds
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/reset-settings', methods=['POST'])
def api_reset_settings():
    """Reset settings to defaults"""
    try:
        default_thresholds = {
            'excellent': 0.80,
            'very_good': 0.65,
            'good': 0.50,
            'fair': 0.35
        }
        
        DATA_STORE['match_thresholds'] = default_thresholds
        
        print("✓ Settings reset to defaults")
        
        return jsonify({
            'success': True,
            'message': 'Settings reset to defaults',
            'thresholds': default_thresholds
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)