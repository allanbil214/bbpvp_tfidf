"""
Configuration settings for BBPVP Job Matching System
"""

# Flask Configuration
SECRET_KEY = 'your-secret-key-change-this-in-production'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'database': 'bbpvp_thesis',
    'user': 'root',
    'password': '',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# GitHub Data URLs
GITHUB_TRAINING_URL = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/programpelatihan.xlsx"
GITHUB_JOBS_URL = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/lowonganpekerjaan.xlsx"
GITHUB_REALISASI_URL = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/realisasipenempatan.xlsx"

# Indonesian Stopwords
STOPWORDS = {
    'dan', 'di', 'ke', 'dari', 'yang', 'untuk', 'pada', 'dengan',
    'dalam', 'adalah', 'ini', 'itu', 'atau', 'oleh', 'sebagai',
    'juga', 'akan', 'telah', 'dapat', 'ada', 'tidak', 'hal',
    'tersebut', 'serta', 'bagi', 'hanya', 'sangat', 'bila',
    'saat', 'kini', 'yaitu', 'dll', 'dsb', 'dst', 'setelah', 
    'mengikuti', 'sesuai', 'pelatihan'
}

# Custom Stemming Rules
CUSTOM_STEM_RULES = {
    'peserta': 'peserta',
    'perawatan': 'rawat',
}

# Processing Configuration
TOTAL_SAVED_SAMPLE = 5

# Default Match Thresholds
DEFAULT_MATCH_THRESHOLDS = {
    'excellent': 0.40,
    'very_good': 0.30,
    'good': 0.20,
    'fair': 0.10
}

CACHE_DIR = "cache"
CACHE_ENABLED = True

# Sastrawi Configuration
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory # type: ignore
    factory = StemmerFactory()
    STEMMER = factory.create_stemmer()
    SASTRAWI_AVAILABLE = True
except ImportError:
    STEMMER = None
    SASTRAWI_AVAILABLE = False
    print("Warning: Sastrawi not available. Stemming will be skipped.")