"""
Text preprocessing utilities
"""

import re
import pandas as pd
from config import STOPWORDS, CUSTOM_STEM_RULES, STEMMER, SASTRAWI_AVAILABLE

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
                stemmed.append(STEMMER.stem(token))
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

def preprocess_dataframe(df, dataset_type='training'):
    """
    Preprocess entire dataframe
    
    Args:
        df: DataFrame to process
        dataset_type: 'training' or 'job'
    
    Returns:
        Processed DataFrame
    """
    df = df.copy()
    
    # Select text column based on dataset type
    if dataset_type == 'training':
        df['text_features'] = df['Tujuan/Kompetensi'].fillna('')
    else:
        df['text_features'] = df['Deskripsi KBJI'].fillna('')
    
    # Apply preprocessing steps
    df['normalized'] = df['text_features'].apply(normalize_text)
    df['no_stopwords'] = df['normalized'].apply(remove_stopwords)
    df['tokens'] = df['no_stopwords'].apply(tokenize_text)
    df['stemmed_tokens'] = df['tokens'].apply(stem_tokens)
    df['stemmed'] = df['stemmed_tokens'].apply(lambda x: ' '.join(x))
    df['token_count'] = df['stemmed_tokens'].apply(len)
    df['preprocessed_text'] = df['stemmed']
    
    return df