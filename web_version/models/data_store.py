# models/data_store.py - MODIFIED VERSION

import os
import pickle
import hashlib
from config import DEFAULT_MATCH_THRESHOLDS, CACHE_DIR, CACHE_ENABLED

class DataStore:
    """Singleton class for managing application data"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataStore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.df_pelatihan = None
        self.df_lowongan = None
        self.df_realisasi = None
        self.similarity_matrix = None
        self.current_experiment_id = None
        self.match_thresholds = DEFAULT_MATCH_THRESHOLDS.copy()
        self.jaccard_matrix = None

        # Cache setup
        self.cache_dir = CACHE_DIR
        if CACHE_ENABLED:
            os.makedirs(self.cache_dir, exist_ok=True)
        
        self._initialized = True
    
    def reset(self):
        """Reset all data"""
        self.df_pelatihan = None
        self.df_lowongan = None
        self.df_realisasi = None
        self.similarity_matrix = None
        self.current_experiment_id = None
        self.jaccard_matrix = None
        self.match_thresholds = DEFAULT_MATCH_THRESHOLDS.copy()
    
    def has_training_data(self):
        """Check if training data is loaded"""
        return self.df_pelatihan is not None
    
    def has_job_data(self):
        """Check if job data is loaded"""
        return self.df_lowongan is not None
    
    def has_realisasi_data(self):
        """Check if realisasi data is loaded"""
        return self.df_realisasi is not None
    
    def has_similarity_matrix(self):
        """Check if similarity matrix is calculated"""
        return self.similarity_matrix is not None
    
    def get_training_count(self):
        """Get number of training programs"""
        return len(self.df_pelatihan) if self.df_pelatihan is not None else 0
    
    def get_job_count(self):
        """Get number of job positions"""
        return len(self.df_lowongan) if self.df_lowongan is not None else 0
    
    def get_realisasi_count(self):
        """Get number of realisasi records"""
        return len(self.df_realisasi) if self.df_realisasi is not None else 0
    
    # Cache methods
    def get_cache_key(self, df, dataset_type):
        """Generate cache key based on dataset content"""
        content = f"{dataset_type}_{len(df)}"
        for idx in range(min(5, len(df))):
            row = df.iloc[idx]
            if dataset_type == 'training':
                content += str(row.get('Deskripsi Tujuan Program Pelatihan/Kompetensi', ''))
            elif dataset_type == 'job':
                content += str(row.get('Deskripsi Pekerjaan', ''))
        return hashlib.md5(content.encode()).hexdigest()
    
    def load_from_cache(self, cache_key):
        """Load preprocessed data from cache"""
        if not CACHE_ENABLED:
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Cache load error: {e}")
                return None
        return None
    
    def save_to_cache(self, cache_key, data):
        """Save preprocessed data to cache"""
        if not CACHE_ENABLED:
            return False
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"Cache save error: {e}")
            return False

# Global instance
data_store = DataStore()