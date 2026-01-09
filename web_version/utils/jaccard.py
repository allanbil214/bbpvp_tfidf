"""
Jaccard Similarity calculation utilities
"""

def calculate_jaccard_similarity(tokens1, tokens2):
    """
    Calculate Jaccard Similarity between two token lists
    
    Args:
        tokens1: List of tokens from document 1
        tokens2: List of tokens from document 2
    
    Returns:
        dict with calculation steps and final similarity
    """
    # Convert to sets
    set1 = set(tokens1)
    set2 = set(tokens2)
    
    # Calculate intersection
    intersection = set1.intersection(set2)
    intersection_list = sorted(list(intersection))
    
    # Calculate union
    union = set1.union(set2)
    union_list = sorted(list(union))
    
    # Calculate Jaccard similarity
    if len(union) > 0:
        jaccard_score = len(intersection) / len(union)
    else:
        jaccard_score = 0.0
    
    return {
        'tokens1': tokens1,
        'tokens2': tokens2,
        'set1': sorted(list(set1)),
        'set2': sorted(list(set2)),
        'intersection': intersection_list,
        'intersection_count': len(intersection),
        'union': union_list,
        'union_count': len(union),
        'jaccard_similarity': float(jaccard_score)
    }

def calculate_jaccard_matrix(df_pelatihan, df_lowongan):
    """
    Calculate Jaccard similarity matrix for all document pairs
    
    Returns:
        numpy array of shape (n_training, n_jobs)
    """
    import numpy as np
    
    n_training = len(df_pelatihan)
    n_jobs = len(df_lowongan)
    
    jaccard_matrix = np.zeros((n_training, n_jobs))
    
    for i in range(n_training):
        tokens1 = df_pelatihan.iloc[i]['stemmed_tokens']
        for j in range(n_jobs):
            tokens2 = df_lowongan.iloc[j]['stemmed_tokens']
            result = calculate_jaccard_similarity(tokens1, tokens2)
            jaccard_matrix[i, j] = result['jaccard_similarity']
    
    return jaccard_matrix