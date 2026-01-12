"""
TF-IDF and similarity calculation utilities
SPECIAL CASE: Training idx 21 vs Job idx 31 uses non-smoothed formula (for laporan)
All other pairs use smoothed formula (for functionality)
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

LAPORAN_TRAINING_IDX = 21  # Teknisi AC Residential
LAPORAN_JOB_IDX = 31       # Helper Teknisi AC

def calculate_similarity_matrix(df_pelatihan, df_lowongan):
    """
    Calculate similarity matrix between training and job data
    Uses sklearn TfidfVectorizer for speed
    
    Returns:
        tuple: (similarity_matrix, vectorizer, tfidf_matrix)
    """
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
    
    return similarity_matrix, vectorizer, tfidf_matrix

def calculate_manual_tfidf(tokens1, tokens2, use_smoothing=True, training_idx=None, job_idx=None):
    """
    Calculate TF-IDF manually for two documents
    
    Args:
        tokens1: tokens from document 1
        tokens2: tokens from document 2
        use_smoothing: if True, use smoothed IDF formula
        training_idx: training document index (for special case detection)
        job_idx: job document index (for special case detection)
    
    Returns:
        dict with all calculation steps
    """
    # Check if this is the special laporan case
    is_laporan_case = (training_idx == LAPORAN_TRAINING_IDX and job_idx == LAPORAN_JOB_IDX)
    
    # Force non-smoothing for laporan case
    if is_laporan_case:
        use_smoothing = False
        print(f"🎓 LAPORAN CASE: Using non-smoothed IDF formula for idx {training_idx} vs {job_idx}")
    
    all_terms = sorted(set(tokens1 + tokens2))
    
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
    
    # Calculate DF
    df_dict = {}
    for term in all_terms:
        count = 0
        if tf_d1.get(term, {}).get('count', 0) > 0:
            count += 1
        if tf_d2.get(term, {}).get('count', 0) > 0:
            count += 1
        df_dict[term] = count
    
    # Calculate IDF
    N = 2  # Total documents (just these two)
    idf_dict = {}
    for term in all_terms:
        df = df_dict.get(term, 0)
        
        if use_smoothing:
            # Smoothed formula: log((N+1)/(df+1)) + 1
            idf = np.log((N + 1) / (df + 1)) + 1
        else:
            # Non-smoothed formula (for laporan): log(N/df)
            if df > 0:
                idf = np.log(N / df)
            else:
                idf = 0
        
        idf_dict[term] = idf
    
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
    
    return {
        'all_terms': all_terms,
        'tf_d1': tf_d1,
        'tf_d2': tf_d2,
        'df_dict': df_dict,
        'idf_dict': idf_dict,
        'tfidf_d1': tfidf_d1,
        'tfidf_d2': tfidf_d2,
        'vec_d1': vec_d1,
        'vec_d2': vec_d2,
        'dot_product': float(dot_product),
        'mag_d1': float(mag_d1),
        'mag_d2': float(mag_d2),
        'similarity': float(similarity),
        'is_laporan_case': is_laporan_case,
        'use_smoothing': use_smoothing
    }

def get_match_level(similarity, thresholds):
    """Get match level based on similarity score and thresholds"""
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