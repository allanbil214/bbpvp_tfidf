"""
In-memory data storage for the application
Replaces session-based storage
"""

from config import DEFAULT_MATCH_THRESHOLDS

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
        self.similarity_matrix = None
        self.current_experiment_id = None
        self.match_thresholds = DEFAULT_MATCH_THRESHOLDS.copy()
        self._initialized = True
    
    def reset(self):
        """Reset all data"""
        self.df_pelatihan = None
        self.df_lowongan = None
        self.similarity_matrix = None
        self.current_experiment_id = None
        self.match_thresholds = DEFAULT_MATCH_THRESHOLDS.copy()
    
    def has_training_data(self):
        """Check if training data is loaded"""
        return self.df_pelatihan is not None
    
    def has_job_data(self):
        """Check if job data is loaded"""
        return self.df_lowongan is not None
    
    def has_similarity_matrix(self):
        """Check if similarity matrix is calculated"""
        return self.similarity_matrix is not None
    
    def get_training_count(self):
        """Get number of training programs"""
        return len(self.df_pelatihan) if self.df_pelatihan is not None else 0
    
    def get_job_count(self):
        """Get number of job positions"""
        return len(self.df_lowongan) if self.df_lowongan is not None else 0

# Global instance
data_store = DataStore()