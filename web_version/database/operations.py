"""
Database CRUD operations
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from mysql.connector import Error # type: ignore
from database.connection import get_db_connection
from utils.similarity import get_match_level

def create_experiment(name, description="", training_count=0, job_count=0):
    """Create new experiment in database"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
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

def save_tfidf_samples(experiment_id, vectorizer, tfidf_matrix, similarity_matrix, df_pelatihan, df_lowongan, sample_count=5):
    """Save sample TF-IDF calculations from sklearn results"""
    conn = get_db_connection()
    if not conn or not experiment_id:
        return
    
    try:
        cursor = conn.cursor()
        
        # Use configurable sample count, default to 5
        actual_sample_count = min(sample_count, len(df_lowongan))
        
        query = """
        INSERT INTO tfidf_calculations 
        (experiment_id, training_index, training_name, job_index, job_name,
        unique_terms_count, terms_json, tfidf_training_json, tfidf_job_json, cosine_similarity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        feature_names = vectorizer.get_feature_names_out()
        n_pelatihan = len(df_pelatihan)
        
        batch_data = []
        for low_idx in range(actual_sample_count):
            similarities = similarity_matrix[:, low_idx]
            top_pel_idx = int(np.argmax(similarities))
            
            training_name = df_pelatihan.iloc[top_pel_idx]['PROGRAM PELATIHAN']
            job_name = df_lowongan.iloc[low_idx]['Nama Jabatan']
            
            training_vector = tfidf_matrix[top_pel_idx].toarray()[0]
            job_vector = tfidf_matrix[n_pelatihan + low_idx].toarray()[0]
            
            # Only store non-zero TF-IDF values
            tfidf_training = {term: float(training_vector[i]) 
                            for i, term in enumerate(feature_names) 
                            if training_vector[i] > 0}
            
            tfidf_job = {term: float(job_vector[i]) 
                        for i, term in enumerate(feature_names) 
                        if job_vector[i] > 0}
            
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

def save_tfidf_calculation(experiment_id, pel_idx, low_idx, calculation_data):
    """Save detailed TF-IDF calculation (manual step-by-step) to database"""
    conn = get_db_connection()
    if not conn or not experiment_id:
        return
    
    try:
        cursor = conn.cursor()
        
        query = """
        INSERT INTO tfidf_calculations 
        (experiment_id, training_index, training_name, job_index, job_name,
        unique_terms_count, terms_json, tf_training_json, tf_job_json,
        idf_json, tfidf_training_json, tfidf_job_json, cosine_similarity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            experiment_id,
            int(pel_idx),
            calculation_data['training_name'],
            int(low_idx),
            calculation_data['job_name'],
            int(len(calculation_data['all_terms'])),
            json.dumps(calculation_data['all_terms']),
            json.dumps(calculation_data['tf_d1']),
            json.dumps(calculation_data['tf_d2']),
            json.dumps(calculation_data['idf_dict']),
            json.dumps(calculation_data['tfidf_d1']),
            json.dumps(calculation_data['tfidf_d2']),
            float(calculation_data['similarity'])
        )
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ TF-IDF calculation saved to database")
    except Error as e:
        print(f"✗ Error saving TF-IDF calculation: {e}")

def save_recommendations(experiment_id, recommendations, thresholds):
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
            match_level = get_match_level(similarity, thresholds)
            
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