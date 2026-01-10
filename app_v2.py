"""
BBPVP Job Matching System - GUI Application
A complete GUI for text preprocessing and TF-IDF based job matching
"""
# pip install pandas numpy scikit-learn matplotlib Sastrawi openpyxl mysql-connector-python
# > use this symbol to fold level 2

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import io
import os
import threading
import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime
import pickle
import hashlib

# Try to import Sastrawi, provide fallback if not available
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    factory = StemmerFactory()
    stemmer = factory.create_stemmer()
    SASTRAWI_AVAILABLE = True
except ImportError:
    SASTRAWI_AVAILABLE = False
    print("Warning: Sastrawi not available. Stemming will be skipped.")


class BBPVPMatchingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BBPVP Job to Training Program Matching System")
        self.root.geometry("1400x900")
        
        self.db_config = {
            'host': 'localhost',
            'port': 3307,
            'database': 'bbpvp_thesis',
            'user': 'root',
            'password': '',
            'charset': 'utf8mb4',
            'use_unicode': True
        }

        self.match_thresholds = {
            'excellent': 0.40,
            'very_good': 0.30,
            'good': 0.20,
            'fair': 0.10
        }

        self.default_match_thresholds = {
            'excellent': 0.40,
            'very_good': 0.30,
            'good': 0.20,
            'fair': 0.10
        }

        self.db_connection = None
        self.current_experiment_id = None
        self.connect_to_database()
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)

        self.progress_var = tk.DoubleVar()
        self.progress_label_var = tk.StringVar()

        # Data storage
        self.df_pelatihan = None
        self.df_lowongan = None
        self.df_realisasi = None  
        self.current_step = 0
        self.total_saved_sample = 5
        
        # GitHub URLs 
        self.github_training_url = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/programpelatihan.xlsx"
        self.github_jobs_url = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/lowonganpekerjaan.xlsx"
        self.github_realisasi_url = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/realisasipenempatan.xlsx"  
        
        # Indonesian stopwords
        self.stopwords = {
            'dan', 'di', 'ke', 'dari', 'yang', 'untuk', 'pada', 'dengan',
            'dalam', 'adalah', 'ini', 'itu', 'atau', 'oleh', 'sebagai',
            'juga', 'akan', 'telah', 'dapat', 'ada', 'tidak', 'hal',
            'tersebut', 'serta', 'bagi', 'hanya', 'sangat', 'bila',
            'saat', 'kini', 'yaitu', 'dll', 'dsb', 'dst', 'setelah', 
            'mengikuti', 'sesuai', 'pelatihan'
        }

        self.custom_stem_rules = {
            'peserta': 'peserta',     
            'perawatan': 'rawat',
        }
        
        self.tabs_config = {
            "database": {
                "title": "0. Database Config",
                "visible": True,
                "builder": self.create_database_tab
            },
            "settings": {  # NEW
                "title": "0. Settings",
                "visible": True,
                "builder": self.create_settings_tab
            },
            "import": {
                "title": "1. Import Data",
                "visible": True,
                "builder": self.create_import_tab
            },
            "view": {
                "title": "2. View Data",
                "visible": True,
                "builder": self.create_view_data_tab
            },
            "preprocess": {
                "title": "3. Preprocessing",
                "visible": True,
                "builder": self.create_preprocess_tab
            },
            "tfidf": {
                "title": "4. TF-IDF & Cosine Similarity",
                "visible": True,
                "builder": self.create_tfidf_tab
            },
            "recommendations": {
                "title": "5. Recommendations",
                "visible": True,
                "builder": self.create_recommendations_tab
            },
            "analysis": {
                "title": "6. Market Analysis",
                "visible": True,
                "builder": self.create_analysis_tab
            },
            "results": {
                "title": "x. Results & Analysis (UNUSED)",
                "visible": False,
                "builder": self.create_results_tab
            },
            "jaccard": {
                "title": "7. Jaccard Similarity",
                "visible": True,
                "builder": self.create_jaccard_tab
            },
            "comparison": {
                "title": "8. Cosine vs Jaccard",
                "visible": True,
                "builder": self.create_comparison_tab
            }
        }
        self.create_widgets()

    def get_cache_key(self, df, dataset_type):
        """Generate cache key based on dataset content"""
        # Create hash from dataset content
        content = f"{dataset_type}_{len(df)}"
        for idx in range(min(5, len(df))):  # Sample first 5 rows for hash
            row = df.iloc[idx]
            if dataset_type == 'pelatihan':
                content += str(row.get('Deskripsi Tujuan Program Pelatihan/Kompetensi', ''))
            else:
                content += str(row.get('Deskripsi Pekerjaan', ''))
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def load_from_cache(self, cache_key):
        """Load preprocessed data from cache"""
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
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"Cache save error: {e}")
            return False

    def show_progress_bar(self, parent_widget):
        """Show progress bar in the output widget"""
        self.progress_label_var.set("Processing...")
        parent_widget.insert(tk.END, "\n")
        
    def update_progress(self, current, total, message, parent_widget):
        """Update progress bar on the same line"""
        percentage = (current / total) * 100 if total > 0 else 0
        
        # Create a simple text-based progress bar
        bar_length = 50
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Get current content
        content = parent_widget.get(1.0, tk.END)
        # lines = content.rstrip('\n').split('\n')
        
        # # Check if last line is a progress bar (starts with '[')
        # if lines and lines[-1].startswith('['):
        #     # Remove the last line (old progress bar)
        #     parent_widget.delete(f"{len(lines)}.0", tk.END)
        
        # Insert new progress bar
        progress_line = f"[{bar}] {percentage:.1f}% - {message} ({current}/{total})\n"
        parent_widget.insert(tk.END, progress_line)
        parent_widget.see(tk.END)
        self.root.update()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        for cfg in self.tabs_config.values():
            if not cfg["visible"]:
                continue

            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=cfg["title"])
            cfg["builder"](frame)
        
    def create_database_tab(self, parent):
        """Create database configuration tab"""
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Configuration
        left_frame = ttk.Frame(main_frame, width=500)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        left_frame.pack_propagate(False)
        
        title = ttk.Label(left_frame, text="Database Configuration", font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Connection settings frame
        settings_frame = ttk.LabelFrame(left_frame, text="MySQL Connection Settings", padding="15")
        settings_frame.pack(fill='x', pady=10)
        
        # Host
        ttk.Label(settings_frame, text="Host:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=8)
        self.db_host_entry = ttk.Entry(settings_frame, width=30)
        self.db_host_entry.grid(row=0, column=1, sticky='ew', pady=8, padx=(10, 0))
        self.db_host_entry.insert(0, self.db_config['host'])
        
        # Port
        ttk.Label(settings_frame, text="Port:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky='w', pady=8)
        self.db_port_entry = ttk.Entry(settings_frame, width=30)
        self.db_port_entry.grid(row=1, column=1, sticky='ew', pady=8, padx=(10, 0))
        self.db_port_entry.insert(0, str(self.db_config['port']))
        
        # Database name
        ttk.Label(settings_frame, text="Database:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky='w', pady=8)
        self.db_name_entry = ttk.Entry(settings_frame, width=30)
        self.db_name_entry.grid(row=2, column=1, sticky='ew', pady=8, padx=(10, 0))
        self.db_name_entry.insert(0, self.db_config['database'])
        
        # Username
        ttk.Label(settings_frame, text="Username:", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky='w', pady=8)
        self.db_user_entry = ttk.Entry(settings_frame, width=30)
        self.db_user_entry.grid(row=3, column=1, sticky='ew', pady=8, padx=(10, 0))
        self.db_user_entry.insert(0, self.db_config['user'])
        
        # Password
        ttk.Label(settings_frame, text="Password:", font=('Arial', 10, 'bold')).grid(row=4, column=0, sticky='w', pady=8)
        self.db_password_entry = ttk.Entry(settings_frame, width=30, show='•')
        self.db_password_entry.grid(row=4, column=1, sticky='ew', pady=8, padx=(10, 0))
        self.db_password_entry.insert(0, self.db_config['password'])
        
        # Show/Hide password checkbox
        self.show_password_var = tk.BooleanVar(value=False)
        def toggle_password():
            if self.show_password_var.get():
                self.db_password_entry.config(show='')
            else:
                self.db_password_entry.config(show='•')
        
        ttk.Checkbutton(settings_frame, text="Show password", 
                    variable=self.show_password_var,
                    command=toggle_password).grid(row=5, column=1, sticky='w', pady=5, padx=(10, 0))
        
        settings_frame.columnconfigure(1, weight=1)
        
        # Buttons frame
        button_frame = ttk.LabelFrame(left_frame, text="Actions", padding="15")
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="💾 Save Configuration", 
                command=self.save_db_config,
                style='Accent.TButton', width=35).pack(pady=5)
        
        ttk.Button(button_frame, text="🔌 Test Connection", 
                command=self.test_db_connection,
                width=35).pack(pady=5)
        
        ttk.Button(button_frame, text="🔄 Reconnect with New Settings", 
                command=self.reconnect_database,
                width=35).pack(pady=5)
        
        ttk.Separator(button_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="↺ Reset to Defaults", 
                command=self.reset_db_config,
                width=35).pack(pady=5)
        
        # Info frame
        info_frame = ttk.LabelFrame(left_frame, text="💡 Information", padding="10")
        info_frame.pack(fill='x', pady=10)
        
        info_text = tk.Text(info_frame, height=10, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill='x')
        info_text.insert(1.0, 
            "Database Configuration Guide:\n\n"
            "1. Enter your MySQL connection details\n"
            "2. Click 'Test Connection' to verify\n"
            "3. Click 'Save Configuration' to apply\n"
            "4. Connection status appears on the right →\n\n"
            "Default Settings:\n"
            "• Host: localhost\n"
            "• Port: 3307\n"
            "• Database: bbpvp_thesis\n"
            "• User: root\n"
            "• Password: (empty)\n\n"
            "Note: Make sure MySQL is running and\n"
            "the database schema is created!"
        )
        info_text.config(state='disabled')
        
        # Right panel - Status and logs
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Connection Status & Logs", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Connection status display
        status_frame = ttk.LabelFrame(right_frame, text="Current Status", padding="10")
        status_frame.pack(fill='x', pady=5)
        
        self.db_status_label = ttk.Label(status_frame, text="⚫ Not Connected", 
                                        font=('Arial', 11, 'bold'))
        self.db_status_label.pack(pady=5)
        
        self.db_status_detail = tk.Text(status_frame, height=4, wrap=tk.WORD, 
                                        font=('Arial', 9), state='disabled')
        self.db_status_detail.pack(fill='x', pady=5)
        
        # Connection logs
        logs_frame = ttk.LabelFrame(right_frame, text="Connection Logs", padding="5")
        logs_frame.pack(fill='both', expand=True, pady=5)
        
        self.db_log_output = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, 
                                                    font=('Consolas', 9))
        self.db_log_output.pack(fill='both', expand=True)
        
        # Initial connection check
        self.update_db_status()

    def create_import_tab(self, parent):
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls
        left_frame = ttk.Frame(main_frame, width=400)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        
        title = ttk.Label(left_frame, text="Data Import", font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Data source selection
        source_frame = ttk.LabelFrame(left_frame, text="Select Data Source", padding="10")
        source_frame.pack(fill='x', pady=10)
        
        self.data_source_var = tk.StringVar(value="github")
        
        ttk.Radiobutton(source_frame, text="Load from GitHub", 
                       variable=self.data_source_var, value="github").pack(anchor='w', pady=5)
        ttk.Radiobutton(source_frame, text="Upload from Local Files", 
                       variable=self.data_source_var, value="upload").pack(anchor='w', pady=5)
        
        # Buttons frame
        button_frame = ttk.LabelFrame(left_frame, text="Load Options", padding="10")
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="Load All Data", 
                  command=self.load_both_data, width=30,
                  style='Accent.TButton').pack(pady=5)
        
        ttk.Separator(button_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(button_frame, text="Or load individually:", 
                 font=('Arial', 9, 'italic')).pack(pady=5)
        
        ttk.Button(button_frame, text="Load Training Data", 
                  command=self.load_training_data, width=30).pack(pady=3)
        ttk.Button(button_frame, text="Load Job Data", 
                  command=self.load_job_data, width=30).pack(pady=3)
        ttk.Button(button_frame, text="Load Realisasi Penempatan",
                   command=self.load_realisasi_data, width=30).pack(pady=3)
        
        # Info box
        info_frame = ttk.LabelFrame(left_frame, text="💡 Quick Guide", padding="10")
        info_frame.pack(fill='x', pady=10)
        
        info_text = tk.Text(info_frame, height=8, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill='x')
        info_text.insert(1.0, 
            "1. Select data source (GitHub or Local)\n"
            "2. Click 'Load BOTH Data' for quick start\n"
            "3. Or load datasets individually\n"
            "4. Check the output panel →\n"
            "5. Proceed to 'Preprocessing' tab\n\n"
            "GitHub mode: Loads from online repository\n"
            "Local mode: Upload your own files"
        )
        info_text.config(state='disabled')
        
        # Right panel - Output
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Import Status & Data Preview", 
                 font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.import_status = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                       font=('Consolas', 9))
        self.import_status.pack(fill='both', expand=True)

    def create_view_data_tab(self, parent):
        """Create simplified view data tab"""
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls (fixed width) with scrollbar
        left_container = ttk.Frame(main_frame, width=350)
        left_container.pack(side='left', fill='y', padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Get the background color from the current theme
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')
        
        # Create canvas and scrollbar
        left_canvas = tk.Canvas(left_container, width=350, bg=bg_color, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        
        # Create frame inside canvas
        left_frame = ttk.Frame(left_canvas)
        
        # Configure canvas
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Pack scrollbar and canvas
        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        canvas_frame = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        
        # Configure scroll region
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        
        left_frame.bind("<Configure>", configure_scroll_region)
        
        # Configure canvas window width
        def configure_canvas_width(event):
            left_canvas.itemconfig(canvas_frame, width=event.width)
        
        left_canvas.bind("<Configure>", configure_canvas_width)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")
        
        left_canvas.bind("<Enter>", bind_mousewheel)
        left_canvas.bind("<Leave>", unbind_mousewheel)
        
        # Now add all your content to left_frame
        title = ttk.Label(left_frame, text="View Data", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Dataset selection
        dataset_frame = ttk.LabelFrame(left_frame, text="Select Dataset", padding="10")
        dataset_frame.pack(fill='x', pady=10)
        
        self.view_dataset_var = tk.StringVar(value="training")
        ttk.Radiobutton(dataset_frame, text="Training Programs", 
                    variable=self.view_dataset_var, value="training").pack(anchor='w', pady=3)
        ttk.Radiobutton(dataset_frame, text="Job Positions", 
                    variable=self.view_dataset_var, value="job").pack(anchor='w', pady=3)
        ttk.Radiobutton(dataset_frame, text="Realisasi Penempatan", 
                        variable=self.view_dataset_var, value="realisasi").pack(anchor='w', pady=3)
        
        # Records to display
        display_frame = ttk.LabelFrame(left_frame, text="Display Options", padding="10")
        display_frame.pack(fill='x', pady=10)
        
        ttk.Label(display_frame, text="Records to show:").pack(anchor='w', pady=3)
        self.view_records_spinbox = ttk.Spinbox(display_frame, from_=5, to=100, increment=5, width=15)
        self.view_records_spinbox.set(20)
        self.view_records_spinbox.pack(anchor='w', pady=5)
        
        # View style selection
        style_frame = ttk.LabelFrame(left_frame, text="View Style", padding="10")
        style_frame.pack(fill='x', pady=10)
        
        ttk.Button(style_frame, text="📊 Table View (Horizontal)", 
                command=self.show_data_table_view,
                style='Accent.TButton', width=30).pack(pady=5)
        
        ttk.Button(style_frame, text="📋 List View (Vertical)", 
                command=self.show_data_list_view,
                width=30).pack(pady=5)
        
        # Info
        info_frame = ttk.LabelFrame(left_frame, text="💡 Info", padding="10")
        info_frame.pack(fill='x', pady=10)
        
        info_text = tk.Text(info_frame, height=8, wrap=tk.WORD, font=('Arial', 8))
        info_text.pack(fill='x')
        info_text.insert(1.0, 
            "Browse imported datasets:\n\n"
            "1. Select dataset type\n"
            "2. Choose records to display\n"
            "3. Pick view style:\n"
            "   • Table: Excel-like grid\n"
            "   • List: Detailed vertical\n"
            "4. View results on the right →"
        )
        info_text.config(state='disabled')
        
        # Right panel - Data display
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Dataset Browser", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.view_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                    font=('Consolas', 9))
        self.view_output.pack(fill='both', expand=True)

    def create_preprocess_tab(self, parent):
        # Main frame with two columns
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls (fixed width) with scrollbar
        left_container = ttk.Frame(main_frame, width=350)
        left_container.pack(side='left', fill='y', padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Get the background color from the current theme
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')
        
        # Create canvas and scrollbar
        left_canvas = tk.Canvas(left_container, width=350, bg=bg_color, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        
        # Create frame inside canvas
        left_frame = ttk.Frame(left_canvas)
        
        # Configure canvas
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Pack scrollbar and canvas
        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        canvas_frame = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        
        # Configure scroll region
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        
        left_frame.bind("<Configure>", configure_scroll_region)
        
        # Configure canvas window width
        def configure_canvas_width(event):
            left_canvas.itemconfig(canvas_frame, width=event.width)
        
        left_canvas.bind("<Configure>", configure_canvas_width)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")
        
        left_canvas.bind("<Enter>", bind_mousewheel)
        left_canvas.bind("<Leave>", unbind_mousewheel)
        
        # Now add all your content to left_frame
        title = ttk.Label(left_frame, text="Preprocessing Steps", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Dataset selection
        dataset_frame = ttk.LabelFrame(left_frame, text="Select Dataset", padding="10")
        dataset_frame.pack(fill='x', pady=10)
        
        self.dataset_var = tk.StringVar(value="pelatihan")
        ttk.Radiobutton(dataset_frame, text="Training Programs", 
                    variable=self.dataset_var, value="pelatihan").pack(anchor='w', pady=3)
        ttk.Radiobutton(dataset_frame, text="Job Positions", 
                    variable=self.dataset_var, value="lowongan").pack(anchor='w', pady=3)
        
        # Row selection
        row_frame = ttk.LabelFrame(left_frame, text="Select Row", padding="10")
        row_frame.pack(fill='x', pady=10)
        
        ttk.Label(row_frame, text="Row Index:").pack()
        self.row_spinbox = ttk.Spinbox(row_frame, from_=0, to=100, width=15)
        self.row_spinbox.pack(pady=5)
        self.row_spinbox.set(0)
        
        # Step buttons
        steps_frame = ttk.LabelFrame(left_frame, text="Processing Steps", padding="10")
        steps_frame.pack(fill='x', pady=10)
        
        steps = [
            ("Original Text", 0),
            ("1. Normalization", 1),
            ("2. Stopword Removal", 2),
            ("3. Tokenization", 3),
            ("4. Stemming", 4),
            ("Show All Steps", 5)
        ]
        
        for step_name, step_num in steps:
            ttk.Button(steps_frame, text=step_name, 
                    command=lambda s=step_num: self.show_preprocessing_step(s),
                    width=28).pack(pady=2)
        
        # Process all button
        ttk.Separator(left_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(left_frame, text="▶ Process All Data", 
                command=self.process_all_data,
                style='Accent.TButton', width=28).pack(pady=10)
        
        # Right panel - Display
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Preprocessing Output", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.preprocess_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                        font=('Consolas', 9))
        self.preprocess_output.pack(fill='both', expand=True)
        
    def create_tfidf_tab(self, parent):
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls (fixed width) with scrollbar
        left_container = ttk.Frame(main_frame, width=380)
        left_container.pack(side='left', fill='y', padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Get the background color from the current theme
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')
        
        # Create canvas and scrollbar
        left_canvas = tk.Canvas(left_container, width=380, bg=bg_color, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        
        # Create frame inside canvas
        left_frame = ttk.Frame(left_canvas)
        
        # Configure canvas
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Pack scrollbar and canvas
        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        canvas_frame = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        
        # Configure scroll region
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        
        left_frame.bind("<Configure>", configure_scroll_region)
        
        # Configure canvas window width
        def configure_canvas_width(event):
            left_canvas.itemconfig(canvas_frame, width=event.width)
        
        left_canvas.bind("<Configure>", configure_canvas_width)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")
        
        left_canvas.bind("<Enter>", bind_mousewheel)
        left_canvas.bind("<Leave>", unbind_mousewheel)
        
        # Now add all your content to left_frame
        title = ttk.Label(left_frame, text="TF-IDF & Similarity", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Document selection
        doc_frame = ttk.LabelFrame(left_frame, text="Select Documents", padding="10")
        doc_frame.pack(fill='x', pady=10)
        
        ttk.Button(doc_frame, text="Load Document Options", 
                command=self.load_document_options, width=30).pack(pady=5)

        ttk.Label(doc_frame, text="Training Program:").pack(anchor='w', pady=2)
        self.pelatihan_combo = ttk.Combobox(doc_frame, state='readonly', width=35)
        self.pelatihan_combo.pack(fill='x', pady=5)
        
        ttk.Label(doc_frame, text="Job Position:").pack(anchor='w', pady=2)
        self.lowongan_combo = ttk.Combobox(doc_frame, state='readonly', width=35)
        self.lowongan_combo.pack(fill='x', pady=5)
        
        # Step buttons
        step_frame = ttk.LabelFrame(left_frame, text="TF-IDF Steps", padding="10")
        step_frame.pack(fill='x', pady=10)
        
        steps = [
            ("1. Show Tokens", self.show_tokens),
            ("2. Calculate TF", self.calculate_tf),
            ("3. Calculate DF", self.calculate_df),
            ("4. Calculate IDF", self.calculate_idf),
            ("5. Calculate TF-IDF", self.calculate_tfidf),
            ("6. Calculate Similarity", self.calculate_similarity),
        ]
        
        for step_name, command in steps:
            ttk.Button(step_frame, text=step_name, command=command, 
                    width=30).pack(pady=2)
        
        ttk.Separator(step_frame, orient='horizontal').pack(fill='x', pady=8)
        
        ttk.Button(step_frame, text="▶ Run All Steps", 
                command=self.run_all_tfidf_steps,
                style='Accent.TButton', width=30).pack(pady=5)
        
        # Calculate all button
        ttk.Separator(left_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(left_frame, text="Calculate All Documents\n(Full Similarity Matrix)", 
                command=self.calculate_all_documents,
                style='Accent.TButton', width=30).pack(pady=10)
        
        # Right panel - Output
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="TF-IDF Calculation Output", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.tfidf_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                    font=('Consolas', 9))
        self.tfidf_output.pack(fill='both', expand=True)

    def create_recommendations_tab(self, parent):
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel with scrollbar
        left_container = ttk.Frame(main_frame, width=420)
        left_container.pack(side='left', fill='y', padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Get the background color from the current theme
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')
        
        # Create canvas and scrollbar
        left_canvas = tk.Canvas(left_container, width=400, bg=bg_color, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        
        # Create frame inside canvas
        left_frame = ttk.Frame(left_canvas)
        
        # Configure canvas
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Pack scrollbar and canvas
        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        canvas_frame = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        
        # Configure scroll region
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        
        left_frame.bind("<Configure>", configure_scroll_region)
        
        # Configure canvas window width
        def configure_canvas_width(event):
            left_canvas.itemconfig(canvas_frame, width=event.width)
        
        left_canvas.bind("<Configure>", configure_canvas_width)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")
        
        left_canvas.bind("<Enter>", bind_mousewheel)
        left_canvas.bind("<Leave>", unbind_mousewheel)
        
        # Now add all your content to left_frame (not left_container)
        title = ttk.Label(left_frame, text="Recommendations", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Recommendation Mode Selection
        mode_frame = ttk.LabelFrame(left_frame, text="Recommendation Mode", padding="10")
        mode_frame.pack(fill='x', pady=10, padx=5)
        
        self.rec_mode_var = tk.StringVar(value="by_job")
        
        ttk.Radiobutton(mode_frame, text="By Job Position (Jobs → Training)", 
                    variable=self.rec_mode_var, value="by_job",
                    command=self.update_recommendation_display).pack(anchor='w', pady=3)
        ttk.Radiobutton(mode_frame, text="By Training Program (Training → Jobs)", 
                    variable=self.rec_mode_var, value="by_training",
                    command=self.update_recommendation_display).pack(anchor='w', pady=3)
        
        # Single Selection Frame (will change based on mode)
        self.single_frame = ttk.LabelFrame(left_frame, text="Single Selection", padding="10")
        self.single_frame.pack(fill='x', pady=10, padx=5)
        
        # Container for dynamic content
        self.single_content_frame = ttk.Frame(self.single_frame)
        self.single_content_frame.pack(fill='x')
        
        # All Selection Frame
        all_frame = ttk.LabelFrame(left_frame, text="All Items", padding="10")
        all_frame.pack(fill='x', pady=10, padx=5)
        
        ttk.Label(all_frame, text="Top N per item:").pack(anchor='w', pady=3)
        self.rec_all_count_spinbox = ttk.Spinbox(all_frame, from_=1, to=10, width=15)
        self.rec_all_count_spinbox.set(3)
        self.rec_all_count_spinbox.pack(anchor='w', pady=5)
        
        ttk.Label(all_frame, text="Minimum Similarity:").pack(anchor='w', pady=3)
        threshold_frame = ttk.Frame(all_frame)
        threshold_frame.pack(fill='x', pady=5)
        
        self.rec_threshold_var = tk.DoubleVar(value=0.01)
        self.rec_threshold_scale = ttk.Scale(threshold_frame, from_=0.0, to=1.0, 
                                            variable=self.rec_threshold_var, 
                                            orient='horizontal')
        self.rec_threshold_scale.pack(side='left', fill='x', expand=True)
        self.rec_threshold_label = ttk.Label(threshold_frame, text="0.00", width=6)
        self.rec_threshold_label.pack(side='right', padx=5)
        
        def update_threshold_label(*args):
            self.rec_threshold_label.config(text=f"{self.rec_threshold_var.get():.2f}")
        self.rec_threshold_var.trace('w', update_threshold_label)
        update_threshold_label()  

        ttk.Button(all_frame, text="Get All Recommendations", 
                command=self.show_all_recommendations,
                style='Accent.TButton', width=30).pack(pady=10)
        
        # Export buttons
        export_frame = ttk.LabelFrame(left_frame, text="Export Results", padding="10")
        export_frame.pack(fill='x', pady=10, padx=5)
        
        ttk.Button(export_frame, text="📊 Export to Excel", 
                command=self.export_recommendations_excel,
                width=30).pack(pady=3)
        ttk.Button(export_frame, text="📄 Export to CSV", 
                command=self.export_recommendations_csv,
                width=30).pack(pady=3)
        
        # Info
        info_text = tk.Text(left_frame, height=5, wrap=tk.WORD, font=('Arial', 8))
        info_text.pack(fill='x', pady=10, padx=5)
        info_text.insert(1.0, 
            "💡 Make sure to:\n"
            "1. Import data (Tab 1)\n"
            "2. Preprocess (Tab 3)\n"
            "3. Calculate similarity (Tab 4)\n"
            "4. Choose recommendation mode"
        )
        info_text.config(state='disabled')
        
        # Right panel - Output
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Recommendation Results", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.rec_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                    font=('Consolas', 9))
        self.rec_output.pack(fill='both', expand=True)
        
        # Initial display
        self.update_recommendation_display()

    def create_analysis_tab(self, parent):
        """Create market analysis tab"""
        # Main frame
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel with scrollbar (similar to other tabs)
        left_container = ttk.Frame(main_frame, width=420)
        left_container.pack(side='left', fill='y', padx=(0, 10))
        left_container.pack_propagate(False)
        
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')
        
        left_canvas = tk.Canvas(left_container, width=420, bg=bg_color, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        left_frame = ttk.Frame(left_canvas)
        
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        canvas_frame = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        left_frame.bind("<Configure>", configure_scroll_region)
        
        def configure_canvas_width(event):
            left_canvas.itemconfig(canvas_frame, width=event.width)
        left_canvas.bind("<Configure>", configure_canvas_width)
        
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        def unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")
        left_canvas.bind("<Enter>", bind_mousewheel)
        left_canvas.bind("<Leave>", unbind_mousewheel)
        
        # Title
        title = ttk.Label(left_frame, text="Market Analysis", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Info section
        info_frame = ttk.LabelFrame(left_frame, text="ℹ️ About", padding="10")
        info_frame.pack(fill='x', pady=10, padx=5)
        
        info_text = tk.Text(info_frame, height=6, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill='x')
        info_text.insert(1.0,
            "Market Analysis compares:\n"
            "• Realisasi (actual placements)\n"
            "• Training programs offered\n"
            "• Job market demand\n\n"
            "Identifies supply-demand gaps."
        )
        info_text.config(state='disabled')
        
        # Threshold settings
        threshold_frame = ttk.LabelFrame(left_frame, text="Threshold Settings", padding="10")
        threshold_frame.pack(fill='x', pady=10, padx=5)

        # Program Match Threshold
        ttk.Label(threshold_frame, text="Program Match Threshold:").pack(anchor='w', pady=(5, 2))

        program_container = ttk.Frame(threshold_frame)
        program_container.pack(fill='x', pady=(0, 10))

        self.program_threshold_scale = ttk.Scale(program_container, from_=0.0, to=1.0, orient='horizontal')
        self.program_threshold_scale.set(0.01)
        self.program_threshold_scale.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.program_threshold_label = ttk.Label(program_container, text="0.01", width=6)
        self.program_threshold_label.pack(side='right')

        def update_program_label(*args):
            val = self.program_threshold_scale.get()
            self.program_threshold_label.config(text=f"{val:.2f}")
        self.program_threshold_scale.config(command=update_program_label)

        # Job Match Threshold
        ttk.Label(threshold_frame, text="Job Match Threshold:").pack(anchor='w', pady=(5, 2))

        job_container = ttk.Frame(threshold_frame)
        job_container.pack(fill='x', pady=(0, 5))

        self.job_threshold_scale = ttk.Scale(job_container, from_=0.0, to=1.0, orient='horizontal')
        self.job_threshold_scale.set(0.01)
        self.job_threshold_scale.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.job_threshold_label = ttk.Label(job_container, text="0.01", width=6)
        self.job_threshold_label.pack(side='right')

        def update_job_label(*args):
            val = self.job_threshold_scale.get()
            self.job_threshold_label.config(text=f"{val:.2f}")
        self.job_threshold_scale.config(command=update_job_label)
        
        # Calculate button
        calc_frame = ttk.LabelFrame(left_frame, text="Actions", padding="10")
        calc_frame.pack(fill='x', pady=10, padx=5)
        
        ttk.Button(calc_frame, text="📊 Calculate Market Analysis", 
                command=self.calculate_market_analysis,
                style='Accent.TButton', width=35).pack(pady=5)
        
        ttk.Button(calc_frame, text="💾 Export to Excel", 
                command=self.export_market_analysis,
                width=35).pack(pady=5)
        
        # Requirements checklist
        req_frame = ttk.LabelFrame(left_frame, text="✅ Requirements", padding="10")
        req_frame.pack(fill='x', pady=10, padx=5)
        
        req_text = tk.Text(req_frame, height=8, wrap=tk.WORD, font=('Arial', 9))
        req_text.pack(fill='x')
        req_text.insert(1.0,
            "Before running analysis:\n\n"
            "1. ✓ Import all 3 datasets\n"
            "   (Training, Jobs, Realisasi)\n"
            "2. ✓ Preprocess data\n"
            "3. ✓ Calculate TF-IDF similarity\n\n"
            "Then run Market Analysis!"
        )
        req_text.config(state='disabled')
        
        # Right panel - Results
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Market Analysis Results", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.analysis_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                        font=('Consolas', 9))
        self.analysis_output.pack(fill='both', expand=True)

    def calculate_market_analysis(self):
        """Calculate market analysis matching realisasi -> training -> jobs"""
        self.analysis_output.delete(1.0, tk.END)
        
        # Check prerequisites
        if self.df_realisasi is None:
            messagebox.showwarning("Warning", "Realisasi data not loaded!")
            return
        
        if self.df_pelatihan is None or self.df_lowongan is None:
            messagebox.showwarning("Warning", "Training or Job data not loaded!")
            return
        
        if not hasattr(self, 'similarity_matrix') or self.similarity_matrix is None:
            messagebox.showwarning("Warning", 
                                "Please calculate similarity matrix first!\n"
                                "Go to TF-IDF tab and click 'Calculate All Documents'")
            return
        
        # Check if data is preprocessed
        if 'preprocessed_text' not in self.df_pelatihan.columns or 'preprocessed_text' not in self.df_lowongan.columns:
            messagebox.showwarning("Warning",
                                "Data not preprocessed!\n"
                                "Go to Preprocessing tab and click 'Process All Data'")
            return
        
        # Get thresholds
        program_threshold = float(self.program_threshold_scale.get())
        job_threshold = float(self.job_threshold_scale.get())
        
        self.log_message("=" * 120, self.analysis_output)
        self.log_message("CALCULATING MARKET ANALYSIS", self.analysis_output)
        self.log_message("=" * 120, self.analysis_output)
        self.log_message(f"\n⚙️ Configuration:", self.analysis_output)
        self.log_message(f"   Program Similarity Threshold: {program_threshold:.2f}", self.analysis_output)
        self.log_message(f"   Job Similarity Threshold: {job_threshold:.2f}\n", self.analysis_output)
        
        def analyze():
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                
                # Step 1: Preprocess realisasi program names
                self.log_message("📝 Step 1/3: Preprocessing realisasi program names...", self.analysis_output)
                df_real_copy = self.df_realisasi.copy()
                
                # Preprocess realisasi
                df_real_copy['text_features'] = df_real_copy['Program Pelatihan'].fillna('')
                df_real_copy['normalized'] = df_real_copy['text_features'].apply(self.normalize_text)
                df_real_copy['no_stopwords'] = df_real_copy['normalized'].apply(self.remove_stopwords)
                df_real_copy['tokens'] = df_real_copy['no_stopwords'].apply(self.tokenize_text)
                df_real_copy['stemmed_tokens'] = df_real_copy['tokens'].apply(self.stem_tokens)
                df_real_copy['preprocessed_text'] = df_real_copy['stemmed_tokens'].apply(lambda x: ' '.join(x))
                
                self.log_message(f"   ✓ Preprocessed {len(df_real_copy)} realisasi programs\n", self.analysis_output)
                
                # Step 2: Match realisasi programs to training programs
                self.log_message("🔗 Step 2/3: Matching realisasi programs to training programs...", self.analysis_output)
                self.log_message(f"   Program similarity threshold: {program_threshold:.2f}", self.analysis_output)
                
                # Calculate similarity between realisasi and training programs
                all_texts = list(df_real_copy['preprocessed_text']) + list(self.df_pelatihan['preprocessed_text'])
                
                vectorizer = TfidfVectorizer()
                tfidf_matrix = vectorizer.fit_transform(all_texts)
                
                n_realisasi = len(df_real_copy)
                realisasi_vectors = tfidf_matrix[:n_realisasi]
                training_vectors = tfidf_matrix[n_realisasi:]
                
                # Calculate similarity matrix: realisasi x training
                realisasi_to_training_sim = cosine_similarity(realisasi_vectors, training_vectors)
                
                self.log_message(f"   ✓ Calculated realisasi-to-training similarities\n", self.analysis_output)
                
                # Step 3: Get existing training-to-jobs similarity
                self.log_message("💼 Step 3/3: Using existing training-to-jobs similarity matrix...", self.analysis_output)
                training_to_jobs_sim = self.similarity_matrix
                
                self.log_message(f"   ✓ Loaded similarity matrix: {training_to_jobs_sim.shape}", self.analysis_output)
                self.log_message(f"   Job similarity threshold: {job_threshold:.2f}\n", self.analysis_output)
                
                # Step 4: Calculate market analysis for each realisasi program
                self.log_message("📊 Step 4/4: Calculating market analysis...\n", self.analysis_output)
                
                results = []
                job_details_list = []
                unmatched_programs = []
                
                # Table header
                self.log_message("=" * 120, self.analysis_output)
                self.log_message(
                    f"┌{'─' * 45}┬{'─' * 12}┬{'─' * 12}┬{'─' * 12}┬{'─' * 12}┬{'─' * 12}┬{'─' * 10}┐",
                    self.analysis_output
                )
                self.log_message(
                    f"│ {'Program Name':<43} │ {'Graduates':<10} │ {'Placed':<10} │ {'Place %':<10} │ {'Jobs':<10} │ {'Capacity':<10} │ {'Status':<8} │",
                    self.analysis_output
                )
                self.log_message(
                    f"├{'─' * 45}┼{'─' * 12}┼{'─' * 12}┼{'─' * 12}┼{'─' * 12}┼{'─' * 12}┼{'─' * 10}┤",
                    self.analysis_output
                )
                
                for real_idx, real_row in df_real_copy.iterrows():
                    program_name = real_row['Program Pelatihan']
                    
                    # Skip NaN program names (like the TOTAL row)
                    if pd.isna(program_name):
                        continue
                    
                    graduates = int(real_row['Jumlah Peserta'])
                    placed = int(real_row['Penempatan'])
                    
                    # Parse placement rate correctly
                    placement_rate_str = str(real_row['% Penempatan'])
                    if '%' in placement_rate_str:
                        # Already in percentage format (e.g., "50.00%")
                        placement_rate = float(placement_rate_str.replace('%', '').strip())
                    else:
                        # Decimal format (e.g., 0.5) - convert to percentage
                        try:
                            placement_rate = float(placement_rate_str) * 100
                        except:
                            placement_rate = 0.0
                    
                    # Find best matching training program
                    similarities_to_training = realisasi_to_training_sim[real_idx, :]
                    best_training_idx = int(np.argmax(similarities_to_training))
                    best_training_score = float(similarities_to_training[best_training_idx])
                    
                    training_match_name = self.df_pelatihan.iloc[best_training_idx]['PROGRAM PELATIHAN']
                    
                    # Get job similarities for this training program
                    job_similarities = training_to_jobs_sim[best_training_idx, :]
                    
                    if best_training_score < program_threshold:
                        # Program doesn't match well with any training program
                        unmatched_programs.append({
                            'program_name': program_name,
                            'best_match': training_match_name,
                            'confidence': round(best_training_score * 100, 2)
                        })
                        
                        prog_display = program_name[:41] + ".." if len(program_name) > 43 else program_name
                        self.log_message(
                            f"│ {prog_display:<43} │ {graduates:>10} │ {placed:>10} │ {placement_rate:>9.1f}% │ {0:>10} │ {0.0:>9.1f}% │ {'UNMATCH':<8} │",
                            self.analysis_output
                        )
                        
                        results.append({
                            'program_name': program_name,
                            'training_match': training_match_name,
                            'confidence': round(best_training_score * 100, 2),
                            'graduates': graduates,
                            'placed': placed,
                            'placement_rate': placement_rate,
                            'matching_jobs': 0,
                            'total_vacancies': 0,
                            'market_capacity': 0.0,
                            'gap': placement_rate - 0.0,
                            'status': 'UNMATCHED',
                            'top_jobs': []
                        })
                        continue
                    
                    # Find matching jobs (above threshold)
                    matching_job_indices = [i for i, sim in enumerate(job_similarities) 
                                        if sim >= job_threshold]
                    
                    # Calculate total vacancies and get job details
                    total_vacancies = 0
                    top_jobs = []
                    
                    for job_idx in matching_job_indices:
                        job_row = self.df_lowongan.iloc[job_idx]
                        vacancy_count = int(job_row.get('Perkiraan Lowongan', 1))
                        total_vacancies += vacancy_count
                        
                        top_jobs.append({
                            'job_name': job_row['Nama Jabatan (Sumber Perusahaan)'],
                            'similarity': round(float(job_similarities[job_idx]) * 100, 2),
                            'vacancies': vacancy_count
                        })
                    
                    # Sort jobs by similarity
                    top_jobs.sort(key=lambda x: x['similarity'], reverse=True)
                    
                    # Calculate metrics
                    market_capacity = (total_vacancies / graduates * 100) if graduates > 0 else 0.0
                    gap = placement_rate - market_capacity
                    
                    # Classify status
                    if gap > 20:
                        status = 'OVERSUPPLY'
                    elif gap > 10:
                        status = 'HIGH_EXTERNAL'
                    elif gap >= -10:
                        status = 'BALANCED'
                    elif gap >= -20:
                        status = 'UNDERSUPPLY'
                    else:
                        status = 'CRITICAL_UNDERSUPPLY'
                    
                    prog_display = program_name[:41] + ".." if len(program_name) > 43 else program_name
                    self.log_message(
                        f"│ {prog_display:<43} │ {graduates:>10} │ {placed:>10} │ {placement_rate:>9.1f}% │ {len(matching_job_indices):>10} │ {market_capacity:>9.1f}% │ {status[:8]:<8} │",
                        self.analysis_output
                    )
                    
                    results.append({
                        'program_name': program_name,
                        'training_match': training_match_name,
                        'confidence': round(best_training_score * 100, 2),
                        'graduates': graduates,
                        'placed': placed,
                        'placement_rate': placement_rate,
                        'matching_jobs': len(matching_job_indices),
                        'total_vacancies': total_vacancies,
                        'market_capacity': round(market_capacity, 2),
                        'gap': round(gap, 2),
                        'status': status,
                        'top_jobs': top_jobs[:10]  # Top 10 jobs
                    })
                    
                    # Store job details for export
                    for job in top_jobs[:10]:
                        job_details_list.append({
                            'program_name': program_name,
                            'status': status,
                            'job_name': job['job_name'],
                            'similarity': job['similarity'],
                            'vacancies': job['vacancies']
                        })
                
                # Table footer
                self.log_message(
                    f"└{'─' * 45}┴{'─' * 12}┴{'─' * 12}┴{'─' * 12}┴{'─' * 12}┴{'─' * 12}┴{'─' * 10}┘",
                    self.analysis_output
                )
                
                # Calculate summary statistics
                total_graduates = sum(r['graduates'] for r in results)
                total_placed = sum(r['placed'] for r in results)
                total_vacancies = sum(r['total_vacancies'] for r in results)
                
                overall_placement_rate = (total_placed / total_graduates * 100) if total_graduates > 0 else 0
                overall_market_capacity = (total_vacancies / total_graduates * 100) if total_graduates > 0 else 0
                overall_gap = overall_placement_rate - overall_market_capacity
                
                summary = {
                    'total_programs': len(results),
                    'total_graduates': total_graduates,
                    'total_placed': total_placed,
                    'total_vacancies': total_vacancies,
                    'overall_placement_rate': round(overall_placement_rate, 2),
                    'overall_market_capacity': round(overall_market_capacity, 2),
                    'overall_gap': round(overall_gap, 2),
                    'matched_programs': len([r for r in results if r['status'] != 'UNMATCHED']),
                    'unmatched_programs': len(unmatched_programs)
                }
                
                # Display summary
                self.log_message("\n" + "=" * 120, self.analysis_output)
                self.log_message("CALCULATION COMPLETE", self.analysis_output)
                self.log_message("=" * 120, self.analysis_output)
                self.log_message(f"\n✓ Total Programs: {len(results)}", self.analysis_output)
                self.log_message(f"✓ Matched: {summary['matched_programs']}", self.analysis_output)
                self.log_message(f"✓ Unmatched: {summary['unmatched_programs']}", self.analysis_output)
                self.log_message(f"✓ Total Graduates: {total_graduates:,}", self.analysis_output)
                self.log_message(f"✓ Total Placed: {total_placed:,} ({overall_placement_rate:.2f}%)", self.analysis_output)
                self.log_message(f"✓ Total Vacancies: {total_vacancies:,}", self.analysis_output)
                self.log_message(f"✓ Market Capacity: {overall_market_capacity:.2f}%", self.analysis_output)
                self.log_message(f"✓ Overall Gap: {overall_gap:.2f}%", self.analysis_output)
                self.log_message("=" * 120, self.analysis_output)
                
                self.log_message(f"\n✅ Analysis Complete! You can now export the results.", self.analysis_output)
                
                # Store results
                self.market_analysis_results = results
                self.market_analysis_jobs = job_details_list
                self.market_analysis_summary = summary
                self.market_analysis_unmatched = unmatched_programs
                
                messagebox.showinfo("Complete", 
                                f"Market analysis completed!\n\n"
                                f"Programs analyzed: {len(results)}\n"
                                f"Matched: {summary['matched_programs']}\n"
                                f"Unmatched: {summary['unmatched_programs']}\n\n"
                                f"Ready to export!")
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.log_message(f"\n✗ Error: {str(e)}", self.analysis_output)
                messagebox.showerror("Error", f"Calculation failed:\n{str(e)}")
        
        # Run in thread to prevent UI freeze
        threading.Thread(target=analyze, daemon=True).start()

    def export_market_analysis(self):
        """Export market analysis results to Excel with enhanced formatting"""
        if not hasattr(self, 'market_analysis_results'):
            messagebox.showwarning("Warning", "No analysis results to export!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="market_analysis_report.xlsx"
        )
        
        if not filename:
            return
        
        try:
            results = self.market_analysis_results
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Sheet 1: Summary Statistics
                summary_data = {
                    'Metric': [
                        'Total Programs Analyzed',
                        'Programs Matched',
                        'Programs Unmatched',
                        'Total Graduates',
                        'Total Placed',
                        'Overall Placement Rate (%)',
                        'Total Market Vacancies',
                        'Overall Market Capacity (%)',
                        'Overall Gap (%)',
                    ],
                    'Value': [
                        len(results),
                        len([r for r in results if r['status'] != 'UNMATCHED']),
                        len([r for r in results if r['status'] == 'UNMATCHED']),
                        sum(r['graduates'] for r in results),
                        sum(r['placed'] for r in results),
                        round((sum(r['placed'] for r in results) / sum(r['graduates'] for r in results) * 100) 
                            if sum(r['graduates'] for r in results) > 0 else 0, 2),
                        sum(r['total_vacancies'] for r in results),
                        round((sum(r['total_vacancies'] for r in results) / sum(r['graduates'] for r in results) * 100) 
                            if sum(r['graduates'] for r in results) > 0 else 0, 2),
                        round((sum(r['placed'] for r in results) / sum(r['graduates'] for r in results) * 100) 
                            if sum(r['graduates'] for r in results) > 0 else 0, 2) - 
                        round((sum(r['total_vacancies'] for r in results) / sum(r['graduates'] for r in results) * 100) 
                            if sum(r['graduates'] for r in results) > 0 else 0, 2),
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Sheet 2: Program Analysis (Main Table)
                analysis_data = []
                for result in results:
                    analysis_data.append({
                        'Program Name': result['program_name'],
                        'Training Match': result.get('training_match', 'N/A'),
                        'Match Confidence (%)': result.get('confidence', 0),
                        'Graduates': result['graduates'],
                        'Placed': result['placed'],
                        'Placement Rate (%)': round(result['placement_rate'], 2),
                        'Unplaced': result['graduates'] - result['placed'],
                        'Matching Jobs': result['matching_jobs'],
                        'Total Vacancies': result['total_vacancies'],
                        'Market Capacity (%)': round(result['market_capacity'], 2),
                        'Gap (%)': round(result['gap'], 2),
                        'Status': result['status'],
                    })
                
                analysis_df = pd.DataFrame(analysis_data)
                analysis_df.to_excel(writer, sheet_name='Program Analysis', index=False)
                
                # Auto-adjust column widths for Program Analysis
                worksheet = writer.sheets['Program Analysis']
                for idx, col in enumerate(analysis_df.columns):
                    max_length = max(
                        analysis_df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
                
                # Sheet 3: Matching Jobs Detail (if available)
                if hasattr(self, 'market_analysis_jobs'):
                    job_details = []
                    for job_data in self.market_analysis_jobs:
                        job_details.append({
                            'Program Name': job_data['program_name'],
                            'Program Status': job_data['status'],
                            'Job Name': job_data['job_name'],
                            'Similarity (%)': job_data['similarity'],
                            'Vacancies': job_data['vacancies']
                        })
                    
                    if job_details:
                        jobs_df = pd.DataFrame(job_details)
                        jobs_df.to_excel(writer, sheet_name='Matching Jobs', index=False)
                        
                        worksheet = writer.sheets['Matching Jobs']
                        for idx, col in enumerate(jobs_df.columns):
                            max_length = max(
                                jobs_df[col].astype(str).apply(len).max(),
                                len(col)
                            ) + 2
                            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
                
                # Sheet 4: Status Distribution
                status_counts = {}
                for result in results:
                    status = result['status']
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                status_data = {
                    'Status': list(status_counts.keys()),
                    'Count': list(status_counts.values()),
                    'Percentage': [round((count / len(results)) * 100, 2) 
                                for count in status_counts.values()]
                }
                status_df = pd.DataFrame(status_data)
                status_df = status_df.sort_values('Count', ascending=False)
                status_df.to_excel(writer, sheet_name='Status Distribution', index=False)
                
                # Sheet 5: Unmatched Programs (if any)
                unmatched = [r for r in results if r['status'] == 'UNMATCHED']
                if unmatched:
                    unmatched_data = []
                    for item in unmatched:
                        unmatched_data.append({
                            'Program Name': item['program_name'],
                            'Best Training Match': item.get('training_match', 'N/A'),
                            'Confidence (%)': item.get('confidence', 0),
                            'Reason': 'Confidence below threshold'
                        })
                    
                    unmatched_df = pd.DataFrame(unmatched_data)
                    unmatched_df.to_excel(writer, sheet_name='Unmatched Programs', index=False)
                    
                    worksheet = writer.sheets['Unmatched Programs']
                    for idx, col in enumerate(unmatched_df.columns):
                        max_length = max(
                            unmatched_df[col].astype(str).apply(len).max(),
                            len(col)
                        ) + 2
                        worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
            
            messagebox.showinfo("Success", 
                            f"Market Analysis exported successfully!\n\n"
                            f"File: {filename}\n"
                            f"Sheets: Summary, Program Analysis, Status Distribution, "
                            f"{'Matching Jobs, ' if hasattr(self, 'market_analysis_jobs') else ''}"
                            f"{'Unmatched Programs' if unmatched else ''}")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")

    def update_recommendation_display(self):
        """Update the recommendation display based on selected mode"""
        # Clear current content
        for widget in self.single_content_frame.winfo_children():
            widget.destroy()
        
        mode = self.rec_mode_var.get()
        
        if mode == "by_job":
            # Job mode
            self.single_frame.config(text="Single Job Position")
            
            ttk.Label(self.single_content_frame, text="Select Job Position:").pack(anchor='w', pady=3)
            self.rec_job_combo = ttk.Combobox(self.single_content_frame, state='readonly', width=35)
            self.rec_job_combo.pack(fill='x', pady=5)
            
            ttk.Label(self.single_content_frame, text="Number of Recommendations:").pack(anchor='w', pady=3)
            self.rec_count_spinbox = ttk.Spinbox(self.single_content_frame, from_=1, to=20, width=15)
            self.rec_count_spinbox.set(5)
            self.rec_count_spinbox.pack(anchor='w', pady=5)
            
            ttk.Label(self.single_content_frame, text="Minimum Similarity:").pack(anchor='w', pady=3)
            threshold_frame = ttk.Frame(self.single_content_frame)
            threshold_frame.pack(fill='x', pady=5)
            
            self.rec_single_threshold_var = tk.DoubleVar(value=0.01)
            self.rec_single_threshold_scale = ttk.Scale(threshold_frame, from_=0.0, to=1.0, 
                                                variable=self.rec_single_threshold_var, 
                                                orient='horizontal')
            self.rec_single_threshold_scale.pack(side='left', fill='x', expand=True)
            self.rec_single_threshold_label = ttk.Label(threshold_frame, text="0.01", width=6)
            self.rec_single_threshold_label.pack(side='right', padx=5)
            
            def update_label(*args):
                self.rec_single_threshold_label.config(text=f"{self.rec_single_threshold_var.get():.2f}")
            self.rec_single_threshold_var.trace('w', update_label)
            
            ttk.Button(self.single_content_frame, text="Get Recommendations", 
                    command=self.show_single_recommendation,
                    style='Accent.TButton', width=30).pack(pady=10)
            
            # Load job options
            if self.df_lowongan is not None:
                job_options = [f"{i}: {row['Nama Jabatan (Sumber Perusahaan)']}" 
                            for i, row in self.df_lowongan.iterrows()]
                self.rec_job_combo['values'] = job_options
                if job_options:
                    self.rec_job_combo.current(0)
        
        else:  # by_training
            # Training mode
            self.single_frame.config(text="Single Training Program")
            
            ttk.Label(self.single_content_frame, text="Select Training Program:").pack(anchor='w', pady=3)
            self.rec_training_combo = ttk.Combobox(self.single_content_frame, state='readonly', width=35)
            self.rec_training_combo.pack(fill='x', pady=5)
            
            ttk.Label(self.single_content_frame, text="Number of Recommendations:").pack(anchor='w', pady=3)
            self.rec_training_count_spinbox = ttk.Spinbox(self.single_content_frame, from_=1, to=20, width=15)
            self.rec_training_count_spinbox.set(5)
            self.rec_training_count_spinbox.pack(anchor='w', pady=5)
            
            ttk.Label(self.single_content_frame, text="Minimum Similarity:").pack(anchor='w', pady=3)
            threshold_frame = ttk.Frame(self.single_content_frame)
            threshold_frame.pack(fill='x', pady=5)
            
            self.rec_training_threshold_var = tk.DoubleVar(value=0.01)
            self.rec_training_threshold_scale = ttk.Scale(threshold_frame, from_=0.0, to=1.0, 
                                                variable=self.rec_training_threshold_var, 
                                                orient='horizontal')
            self.rec_training_threshold_scale.pack(side='left', fill='x', expand=True)
            self.rec_training_threshold_label = ttk.Label(threshold_frame, text="0.01", width=6)
            self.rec_training_threshold_label.pack(side='right', padx=5)
            
            def update_label(*args):
                self.rec_training_threshold_label.config(text=f"{self.rec_training_threshold_var.get():.2f}")
            self.rec_training_threshold_var.trace('w', update_label)
            
            ttk.Button(self.single_content_frame, text="Get Recommendations", 
                    command=self.show_single_recommendation,
                    style='Accent.TButton', width=30).pack(pady=10)
            
            # Load training options
            if self.df_pelatihan is not None:
                training_options = [f"{i}: {row['PROGRAM PELATIHAN']}" 
                            for i, row in self.df_pelatihan.iterrows()]
                self.rec_training_combo['values'] = training_options
                if training_options:
                    self.rec_training_combo.current(0)

    def show_single_recommendation(self):
        """Show single recommendation based on current mode"""
        mode = self.rec_mode_var.get()
        
        if mode == "by_job":
            self.show_single_job_recommendations()
        else:
            self.show_single_training_recommendations()

    def show_all_recommendations(self):
        """Show all recommendations based on current mode"""
        mode = self.rec_mode_var.get()
        
        if mode == "by_job":
            self.show_all_jobs_recommendations()
        else:
            self.show_all_trainings_recommendations()

    def create_settings_tab(self, parent):
        """Create settings tab for threshold configuration"""
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls (fixed width) with scrollbar
        left_container = ttk.Frame(main_frame, width=450)
        left_container.pack(side='left', fill='y', padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Get the background color from the current theme
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')
        
        # Create canvas and scrollbar
        left_canvas = tk.Canvas(left_container, width=450, bg=bg_color, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        
        # Create frame inside canvas
        left_frame = ttk.Frame(left_canvas)
        
        # Configure canvas
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Pack scrollbar and canvas
        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        canvas_frame = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        
        # Configure scroll region
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        
        left_frame.bind("<Configure>", configure_scroll_region)
        
        # Configure canvas window width
        def configure_canvas_width(event):
            left_canvas.itemconfig(canvas_frame, width=event.width)
        
        left_canvas.bind("<Configure>", configure_canvas_width)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")
        
        left_canvas.bind("<Enter>", bind_mousewheel)
        left_canvas.bind("<Leave>", unbind_mousewheel)
        
        # Now add all your content to left_frame
        title = ttk.Label(left_frame, text="Match Level Settings", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Info alert
        info_frame = ttk.LabelFrame(left_frame, text="ℹ️ About Thresholds", padding="10")
        info_frame.pack(fill='x', pady=10)
        
        info_text = tk.Text(info_frame, height=4, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill='x')
        info_text.insert(1.0,
            "These thresholds determine how similarity scores are classified. "
            "Adjust them to make matching more strict (higher values) or more lenient (lower values)."
        )
        info_text.config(state='disabled')
        
        # Threshold settings
        settings_frame = ttk.LabelFrame(left_frame, text="Configure Thresholds", padding="15")
        settings_frame.pack(fill='x', pady=10)
        
        # Excellent
        ttk.Label(settings_frame, text="🟢 Excellent Match (≥):", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=8)
        self.excellent_scale = ttk.Scale(settings_frame, from_=0, to=1, orient='horizontal')
        self.excellent_scale.set(self.match_thresholds['excellent'])
        self.excellent_scale.grid(row=0, column=1, sticky='ew', padx=10)
        self.excellent_label = ttk.Label(settings_frame, text=f"{self.match_thresholds['excellent']:.2f}", width=6)
        self.excellent_label.grid(row=0, column=2)
        self.excellent_scale.config(command=lambda v: self.excellent_label.config(text=f"{float(v):.2f}"))
        
        # Very Good
        ttk.Label(settings_frame, text="🟢 Very Good Match (≥):", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky='w', pady=8)
        self.very_good_scale = ttk.Scale(settings_frame, from_=0, to=1, orient='horizontal')
        self.very_good_scale.set(self.match_thresholds['very_good'])
        self.very_good_scale.grid(row=1, column=1, sticky='ew', padx=10)
        self.very_good_label = ttk.Label(settings_frame, text=f"{self.match_thresholds['very_good']:.2f}", width=6)
        self.very_good_label.grid(row=1, column=2)
        self.very_good_scale.config(command=lambda v: self.very_good_label.config(text=f"{float(v):.2f}"))
        
        # Good
        ttk.Label(settings_frame, text="🟡 Good Match (≥):", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky='w', pady=8)
        self.good_scale = ttk.Scale(settings_frame, from_=0, to=1, orient='horizontal')
        self.good_scale.set(self.match_thresholds['good'])
        self.good_scale.grid(row=2, column=1, sticky='ew', padx=10)
        self.good_label = ttk.Label(settings_frame, text=f"{self.match_thresholds['good']:.2f}", width=6)
        self.good_label.grid(row=2, column=2)
        self.good_scale.config(command=lambda v: self.good_label.config(text=f"{float(v):.2f}"))
        
        # Fair
        ttk.Label(settings_frame, text="🟡 Fair Match (≥):", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky='w', pady=8)
        self.fair_scale = ttk.Scale(settings_frame, from_=0, to=1, orient='horizontal')
        self.fair_scale.set(self.match_thresholds['fair'])
        self.fair_scale.grid(row=3, column=1, sticky='ew', padx=10)
        self.fair_label = ttk.Label(settings_frame, text=f"{self.match_thresholds['fair']:.2f}", width=6)
        self.fair_label.grid(row=3, column=2)
        self.fair_scale.config(command=lambda v: self.fair_label.config(text=f"{float(v):.2f}"))
        
        # Weak (info only)
        ttk.Label(settings_frame, text="🔴 Weak Match:", font=('Arial', 10, 'bold')).grid(row=4, column=0, sticky='w', pady=8)
        ttk.Label(settings_frame, text="< Fair threshold (automatic)", font=('Arial', 9, 'italic')).grid(row=4, column=1, columnspan=2, sticky='w', padx=10)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.LabelFrame(left_frame, text="Actions", padding="10")
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="💾 Save Settings", 
                command=self.save_threshold_settings,
                style='Accent.TButton', width=35).pack(pady=5)
        
        ttk.Button(button_frame, text="↺ Reset to Defaults", 
                command=self.reset_threshold_settings, width=35).pack(pady=5)
        
        # Guidelines
        guide_frame = ttk.LabelFrame(left_frame, text="📋 Guidelines", padding="10")
        guide_frame.pack(fill='x', pady=10)
        
        guide_text = tk.Text(guide_frame, height=8, wrap=tk.WORD, font=('Arial', 9))
        guide_text.pack(fill='x')
        guide_text.insert(1.0,
            "How to Use:\n"
            "1. Adjust sliders to set threshold values (0.00 to 1.00)\n"
            "2. Ensure descending order: Excellent > Very Good > Good > Fair\n"
            "3. Click 'Save Settings' to apply\n\n"
            "Tips:\n"
            "• Higher thresholds = stricter matching\n"
            "• Lower thresholds = more lenient matching\n"
            "• Default values: 0.40, 0.30, 0.20, 0.10"
        )
        guide_text.config(state='disabled')
        
        # Right panel - Preview
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Current Threshold Ranges", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Preview table
        preview_frame = ttk.LabelFrame(right_frame, text="Match Level Ranges", padding="10")
        preview_frame.pack(fill='both', expand=True, pady=10)
        
        self.threshold_preview = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, 
                                                        font=('Consolas', 10), height=20)
        self.threshold_preview.pack(fill='both', expand=True)
        
        # Initial preview
        self.update_threshold_preview()

    def save_threshold_settings(self):
        """Save threshold settings"""
        # Get values
        excellent = float(self.excellent_scale.get())
        very_good = float(self.very_good_scale.get())
        good = float(self.good_scale.get())
        fair = float(self.fair_scale.get())
        
        # Validate
        if not (excellent > very_good > good > fair >= 0):
            messagebox.showerror("Invalid Settings", 
                            "Thresholds must be in descending order:\n"
                            "Excellent > Very Good > Good > Fair ≥ 0")
            return
        
        if not all(0 <= v <= 1 for v in [excellent, very_good, good, fair]):
            messagebox.showerror("Invalid Settings", 
                            "All thresholds must be between 0 and 1")
            return
        
        # Save
        self.match_thresholds = {
            'excellent': excellent,
            'very_good': very_good,
            'good': good,
            'fair': fair
        }
        
        self.update_threshold_preview()
        messagebox.showinfo("Success", 
                        "Settings saved successfully!\n\n"
                        "New thresholds will be used for future recommendations.")

    def reset_threshold_settings(self):
        """Reset thresholds to defaults"""
        if messagebox.askyesno("Confirm Reset", 
                            "Reset all thresholds to default values?"):
            self.match_thresholds = self.default_match_thresholds.copy()
            
            self.excellent_scale.set(self.match_thresholds['excellent'])
            self.very_good_scale.set(self.match_thresholds['very_good'])
            self.good_scale.set(self.match_thresholds['good'])
            self.fair_scale.set(self.match_thresholds['fair'])
            
            self.update_threshold_preview()
            messagebox.showinfo("Reset Complete", "Thresholds reset to default values")

    def update_threshold_preview(self):
        """Update threshold preview display"""
        self.threshold_preview.delete(1.0, tk.END)
        
        t = self.match_thresholds
        
        preview = f"""
    {'=' * 60}
    MATCH LEVEL THRESHOLD RANGES
    {'=' * 60}

    🟢 EXCELLENT MATCH
    Range: ≥ {t['excellent']:.2f} ({t['excellent']*100:.0f}%)
    Description: Top tier matches

    🟢 VERY GOOD MATCH
    Range: {t['very_good']:.2f} to {t['excellent']:.2f} ({t['very_good']*100:.0f}% - {t['excellent']*100:.0f}%)
    Description: High quality matches

    🟡 GOOD MATCH
    Range: {t['good']:.2f} to {t['very_good']:.2f} ({t['good']*100:.0f}% - {t['very_good']*100:.0f}%)
    Description: Acceptable matches

    🟡 FAIR MATCH
    Range: {t['fair']:.2f} to {t['good']:.2f} ({t['fair']*100:.0f}% - {t['good']*100:.0f}%)
    Description: Marginal matches

    🔴 WEAK MATCH
    Range: < {t['fair']:.2f} (< {t['fair']*100:.0f}%)
    Description: Poor matches

    {'=' * 60}

    💡 These thresholds determine how similarity scores are 
    classified in recommendations.

    📊 Current Settings:
    • Excellent: {t['excellent']:.2f}
    • Very Good: {t['very_good']:.2f}
    • Good:      {t['good']:.2f}
    • Fair:      {t['fair']:.2f}

    {'=' * 60}
    """
        
        self.threshold_preview.insert(1.0, preview)

    def create_results_tab(self, parent):
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls (fixed width)
        left_frame = ttk.Frame(main_frame, width=350)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        left_frame.pack_propagate(False)
        
        title = ttk.Label(left_frame, text="Analysis Tools", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Statistics section
        stats_section = ttk.LabelFrame(left_frame, text="Available Analysis", padding="10")
        stats_section.pack(fill='x', pady=10)
        
        ttk.Button(stats_section, text="📊 Generate Statistics", 
                  command=self.generate_statistics,
                  style='Accent.TButton', width=28).pack(pady=5)
        
        ttk.Label(stats_section, text="Shows:", font=('Arial', 9)).pack(anchor='w', pady=5)
        features = [
            "• Dataset summaries",
            "• Token statistics",
            "• Distribution charts"
        ]
        for feature in features:
            ttk.Label(stats_section, text=feature, font=('Arial', 8)).pack(anchor='w', padx=10)
        
        # Info section
        info_frame = ttk.LabelFrame(left_frame, text="💡 About This Tab", padding="10")
        info_frame.pack(fill='x', pady=10)
        
        info_text = tk.Text(info_frame, height=12, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill='x')
        info_text.insert(1.0,
            "This tab provides statistical analysis "
            "of your processed datasets.\n\n"
            "You can view:\n"
            "• Total records\n"
            "• Token counts\n"
            "• Statistical measures\n"
            "• Visual distributions\n\n"
            "Make sure to process your data "
            "in Tab 2 first!"
        )
        info_text.config(state='disabled')
        
        # Right panel - Display (split into stats and viz)
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Analysis Results", 
                 font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Statistics text
        stats_frame = ttk.LabelFrame(right_frame, text="Dataset Statistics", padding="5")
        stats_frame.pack(fill='x', pady=5)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=10, 
                                                    wrap=tk.WORD, font=('Consolas', 9))
        self.stats_text.pack(fill='both', expand=True)
        
        # Visualization frame
        viz_frame = ttk.LabelFrame(right_frame, text="Token Distribution Charts", padding="5")
        viz_frame.pack(fill='both', expand=True, pady=5)
        
        self.viz_canvas_frame = ttk.Frame(viz_frame)
        self.viz_canvas_frame.pack(fill='both', expand=True)
		
    def log_message(self, message, widget=None):
        """Log message to specified widget or import_status"""
        if widget is None:
            widget = self.import_status
        widget.insert(tk.END, message + "\n")
        widget.see(tk.END)
        self.root.update()
    
    def connect_to_database(self):
        """Connect to MySQL database"""
        try:
            self.db_connection = mysql.connector.connect(**self.db_config)
            
            if self.db_connection.is_connected():
                print("✓ Connected to MySQL database")
                if hasattr(self, 'db_log_output'):
                    self.log_message(f"✓ Connected to MySQL database", self.db_log_output)
                    self.log_message(f"  Host: {self.db_config['host']}:{self.db_config['port']}", 
                                self.db_log_output)
                    self.log_message(f"  Database: {self.db_config['database']}\n", 
                                self.db_log_output)
        except Error as e:
            print(f"✗ Database connection error: {e}")
            if hasattr(self, 'db_log_output'):
                self.log_message(f"✗ Database connection error: {e}\n", self.db_log_output)
            self.db_connection = None

    def save_db_config(self):
        """Save database configuration"""
        try:
            self.db_config['host'] = self.db_host_entry.get().strip()
            self.db_config['port'] = int(self.db_port_entry.get().strip())
            self.db_config['database'] = self.db_name_entry.get().strip()
            self.db_config['user'] = self.db_user_entry.get().strip()
            self.db_config['password'] = self.db_password_entry.get()
            
            self.log_message("✓ Configuration saved successfully!", self.db_log_output)
            self.log_message(f"  Host: {self.db_config['host']}", self.db_log_output)
            self.log_message(f"  Port: {self.db_config['port']}", self.db_log_output)
            self.log_message(f"  Database: {self.db_config['database']}", self.db_log_output)
            self.log_message(f"  User: {self.db_config['user']}\n", self.db_log_output)
            
            messagebox.showinfo("Success", "Database configuration saved!\nClick 'Reconnect' to apply changes.")
        except ValueError:
            messagebox.showerror("Error", "Port must be a valid number!")

    def test_db_connection(self):
        """Test database connection with current settings"""
        self.log_message("=" * 80, self.db_log_output)
        self.log_message("TESTING DATABASE CONNECTION", self.db_log_output)
        self.log_message("=" * 80, self.db_log_output)
        
        try:
            # Get current form values
            test_config = {
                'host': self.db_host_entry.get().strip(),
                'port': int(self.db_port_entry.get().strip()),
                'database': self.db_name_entry.get().strip(),
                'user': self.db_user_entry.get().strip(),
                'password': self.db_password_entry.get(),
                'charset': 'utf8mb4',
                'use_unicode': True
            }
            
            self.log_message(f"\nConnecting to:", self.db_log_output)
            self.log_message(f"  Host: {test_config['host']}", self.db_log_output)
            self.log_message(f"  Port: {test_config['port']}", self.db_log_output)
            self.log_message(f"  Database: {test_config['database']}", self.db_log_output)
            self.log_message(f"  User: {test_config['user']}\n", self.db_log_output)
            
            # Attempt connection
            test_conn = mysql.connector.connect(**test_config)
            
            if test_conn.is_connected():
                db_info = test_conn.get_server_info()
                cursor = test_conn.cursor()
                cursor.execute("SELECT DATABASE();")
                db_name = cursor.fetchone()
                
                self.log_message("✅ CONNECTION SUCCESSFUL!", self.db_log_output)
                self.log_message(f"  MySQL Server Version: {db_info}", self.db_log_output)
                self.log_message(f"  Connected to database: {db_name[0]}\n", self.db_log_output)
                
                # Check tables
                cursor.execute("SHOW TABLES;")
                tables = cursor.fetchall()
                self.log_message(f"  Tables found: {len(tables)}", self.db_log_output)
                for table in tables:
                    self.log_message(f"    - {table[0]}", self.db_log_output)
                
                cursor.close()
                test_conn.close()
                
                messagebox.showinfo("Success", 
                                f"Connection successful!\n\n"
                                f"Server: {db_info}\n"
                                f"Database: {db_name[0]}\n"
                                f"Tables: {len(tables)}")
            
        except Error as e:
            self.log_message(f"\n❌ CONNECTION FAILED!", self.db_log_output)
            self.log_message(f"Error: {str(e)}\n", self.db_log_output)
            messagebox.showerror("Connection Failed", 
                            f"Could not connect to database:\n\n{str(e)}\n\n"
                            f"Please check your settings and try again.")
        except ValueError:
            messagebox.showerror("Error", "Port must be a valid number!")

    def reconnect_database(self):
        """Reconnect to database with new settings"""
        self.log_message("=" * 80, self.db_log_output)
        self.log_message("RECONNECTING TO DATABASE", self.db_log_output)
        self.log_message("=" * 80 + "\n", self.db_log_output)
        
        # Close existing connection
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            self.log_message("✓ Closed existing connection", self.db_log_output)
        
        # Save configuration
        self.save_db_config()
        
        # Reconnect
        self.connect_to_database()
        self.update_db_status()

    def reset_db_config(self):
        """Reset to default database configuration"""
        if messagebox.askyesno("Confirm Reset", 
                            "Reset database configuration to defaults?"):
            self.db_host_entry.delete(0, tk.END)
            self.db_host_entry.insert(0, 'localhost')
            
            self.db_port_entry.delete(0, tk.END)
            self.db_port_entry.insert(0, '3307')
            
            self.db_name_entry.delete(0, tk.END)
            self.db_name_entry.insert(0, 'bbpvp_thesis')
            
            self.db_user_entry.delete(0, tk.END)
            self.db_user_entry.insert(0, 'root')
            
            self.db_password_entry.delete(0, tk.END)
            
            self.log_message("✓ Configuration reset to defaults\n", self.db_log_output)
            messagebox.showinfo("Reset", "Configuration reset to defaults!")

    def update_db_status(self):
        """Update database connection status display"""
        if not hasattr(self, 'db_status_label'):
            return
        
        if self.db_connection and self.db_connection.is_connected():
            self.db_status_label.config(text="🟢 Connected", foreground='green')
            
            status_text = (
                f"Host: {self.db_config['host']}:{self.db_config['port']}\n"
                f"Database: {self.db_config['database']}\n"
                f"User: {self.db_config['user']}\n"
                f"Status: Active"
            )
        else:
            self.db_status_label.config(text="🔴 Disconnected", foreground='red')
            
            status_text = (
                f"Status: Not connected\n"
                f"Please check configuration and\n"
                f"click 'Test Connection' or 'Reconnect'"
            )
        
        self.db_status_detail.config(state='normal')
        self.db_status_detail.delete(1.0, tk.END)
        self.db_status_detail.insert(1.0, status_text)
        self.db_status_detail.config(state='disabled')

    def load_both_data(self):
        """Load both training and job data at once"""
        if self.data_source_var.get() != "github":
            messagebox.showinfo("Info", 
                            "Load Both Data option is only available for GitHub source.\n"
                            "Please select 'Load from GitHub' or load files individually.")
            return
        
        self.import_status.delete(1.0, tk.END)
        self.log_message("=" * 80)
        self.log_message("LOADING ALL DATASETS FROM GITHUB")
        self.log_message("=" * 80)
        
        def load():
            try:
                # Load Training Data
                self.log_message("\n[1/3] Loading Training Data (Pelatihan)...", self.import_status)
                self.update_progress(1, 3, "Loading training data", self.import_status)
                self.log_message(f"URL: {self.github_training_url}", self.import_status)
                self.df_pelatihan = pd.read_excel(self.github_training_url)
                self.log_message(f"✓ Training Data loaded: {self.df_pelatihan.shape[0]} rows, "
                            f"{self.df_pelatihan.shape[1]} columns", self.import_status)
                
                # Fill missing values
                self.fill_missing_pelatihan()
                
                # Load Job Data
                self.log_message("\n[2/3] Loading Job Data (Lowongan)...", self.import_status)
                self.update_progress(2, 3, "Loading job data", self.import_status)
                self.log_message(f"URL: {self.github_jobs_url}", self.import_status)
                self.df_lowongan = pd.read_excel(self.github_jobs_url)
                self.log_message(f"✓ Job Data loaded: {self.df_lowongan.shape[0]} rows, "
                            f"{self.df_lowongan.shape[1]} columns", self.import_status)
                
                # NEW: Check vacancy column
                if 'Perkiraan Lowongan' not in self.df_lowongan.columns:
                    self.log_message(f"⚠ Adding default vacancy estimates", self.import_status)
                    self.df_lowongan['Perkiraan Lowongan'] = 1
                
                # NEW: Load Realisasi Data
                self.log_message("\n[3/3] Loading Realisasi Penempatan...", self.import_status)
                self.update_progress(3, 3, "Loading placement data", self.import_status)
                self.log_message(f"URL: {self.github_realisasi_url}", self.import_status)
                self.df_realisasi = pd.read_excel(self.github_realisasi_url)
                self.log_message(f"✓ Realisasi Data loaded: {self.df_realisasi.shape[0]} rows, "
                            f"{self.df_realisasi.shape[1]} columns", self.import_status)
                
                # Calculate percentage if missing
                if '% Penempatan' not in self.df_realisasi.columns:
                    self.df_realisasi['% Penempatan'] = (
                        self.df_realisasi['Penempatan'] / self.df_realisasi['Jumlah Peserta'] * 100
                    ).round(2)
                
                # Summary
                self.log_message("\n" + "=" * 80, self.import_status)
                self.log_message("✓ ALL DATASETS LOADED SUCCESSFULLY!", self.import_status)
                self.log_message("=" * 80, self.import_status)
                self.log_message(f"\n📊 Summary:", self.import_status)
                self.log_message(f"  • Training Programs: {len(self.df_pelatihan)} records", self.import_status)
                self.log_message(f"  • Job Positions: {len(self.df_lowongan)} records", self.import_status)
                self.log_message(f"  • Realisasi Records: {len(self.df_realisasi)} programs", self.import_status)  # NEW
                self.log_message(f"  • Total: {len(self.df_pelatihan) + len(self.df_lowongan) + len(self.df_realisasi)} records", self.import_status)
                
                self.log_message(f"\n📋 Training Data Columns:", self.import_status)
                self.log_message(f"  {', '.join(self.df_pelatihan.columns.tolist())}", self.import_status)
                
                self.log_message(f"\n📋 Job Data Columns:", self.import_status)
                self.log_message(f"  {', '.join(self.df_lowongan.columns.tolist())}", self.import_status)
                
                self.log_message(f"\n✨ Ready for preprocessing! Go to 'Preprocessing' tab.", self.import_status)
                
                messagebox.showinfo("Success", 
                                f"Both datasets loaded successfully!\n\n"
                                f"Training: {len(self.df_pelatihan)} records\n"
                                f"Jobs: {len(self.df_lowongan)} records")
                
                self.create_experiment(
                    "Data Import Session",
                    f"Loaded {len(self.df_pelatihan)} training programs and {len(self.df_lowongan)} jobs"
                )

            except Exception as e:
                self.log_message(f"\n✗ Error: {str(e)}", self.import_status)
                messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
        
        threading.Thread(target=load, daemon=True).start()

    def load_training_data(self):
        self.import_status.delete(1.0, tk.END)
        self.log_message("Loading Training Data (Pelatihan)...")
        
        def load():
            try:
                if self.data_source_var.get() == "github":
                    self.log_message(f"Fetching from GitHub...")
                    self.df_pelatihan = pd.read_excel(self.github_training_url) #, 
                                                     # sheet_name="Versi Ringkas Untuk Tesis")
                else:
                    filename = filedialog.askopenfilename(
                        title="Select Training Data File",
                        filetypes=[("Excel files", "*.xlsx *.xls")]
                    )
                    if filename:
                        self.log_message(f"Loading from: {filename}")
                        self.df_pelatihan = pd.read_excel(filename) #, 
                                                         # sheet_name="Versi Ringkas Untuk Tesis")
                    else:
                        self.log_message("No file selected.")
                        return
                
                self.log_message(f"✓ Loaded: {self.df_pelatihan.shape[0]} rows, "
                               f"{self.df_pelatihan.shape[1]} columns")
                self.log_message(f"\nColumns: {', '.join(self.df_pelatihan.columns.tolist())}")
                self.log_message(f"\nFirst row preview:")
                self.log_message(str(self.df_pelatihan.head(1)))
                
                # Fill missing values
                self.fill_missing_pelatihan()
                
            except Exception as e:
                self.log_message(f"✗ Error: {str(e)}")
        
        threading.Thread(target=load, daemon=True).start()
    
    def load_job_data(self):
        self.import_status.delete(1.0, tk.END)
        self.log_message("Loading Job Data (Lowongan)...")
        
        def load():
            try:
                if self.data_source_var.get() == "github":
                    self.log_message(f"Fetching from GitHub...")
                    self.df_lowongan = pd.read_excel(self.github_jobs_url) #, 
                                                    # sheet_name="petakan ke KBJI")
                else:
                    filename = filedialog.askopenfilename(
                        title="Select Job Data File",
                        filetypes=[("Excel files", "*.xlsx *.xls")]
                    )
                    if filename:
                        self.log_message(f"Loading from: {filename}")
                        self.df_lowongan = pd.read_excel(filename) #, 
                                                        # sheet_name="petakan ke KBJI")
                    else:
                        self.log_message("No file selected.")
                        return
                
                self.log_message(f"✓ Loaded: {self.df_lowongan.shape[0]} rows, "
                               f"{self.df_lowongan.shape[1]} columns")
                self.log_message(f"\nColumns: {', '.join(self.df_lowongan.columns.tolist())}")
                self.log_message(f"\nFirst row preview:")
                self.log_message(str(self.df_lowongan.head(1)))
                
            except Exception as e:
                self.log_message(f"✗ Error: {str(e)}")
        
        threading.Thread(target=load, daemon=True).start()

    def load_realisasi_data(self):
        """Load placement realization data"""
        self.import_status.delete(1.0, tk.END)
        self.log_message("Loading Placement Realization Data...")
        
        def load():
            try:
                if self.data_source_var.get() == "github":
                    self.log_message(f"Fetching from GitHub...")
                    self.df_realisasi = pd.read_excel(self.github_realisasi_url)
                else:
                    filename = filedialog.askopenfilename(
                        title="Select Realisasi Penempatan File",
                        filetypes=[("Excel files", "*.xlsx *.xls")]
                    )
                    if filename:
                        self.log_message(f"Loading from: {filename}")
                        self.df_realisasi = pd.read_excel(filename)
                    else:
                        self.log_message("No file selected.")
                        return
                
                self.log_message(f"✓ Loaded: {self.df_realisasi.shape[0]} rows, "
                            f"{self.df_realisasi.shape[1]} columns")
                self.log_message(f"\nColumns: {', '.join(self.df_realisasi.columns.tolist())}")
                
                # Validate required columns
                required_cols = ['Program Pelatihan', 'Jumlah Peserta', 'Penempatan']
                missing_cols = [col for col in required_cols if col not in self.df_realisasi.columns]
                
                if missing_cols:
                    self.log_message(f"⚠ Warning: Missing columns: {missing_cols}")
                else:
                    self.log_message(f"✓ All required columns present")
                    
                    # Calculate percentage if not present
                    if '% Penempatan' not in self.df_realisasi.columns:
                        self.df_realisasi['% Penempatan'] = (
                            self.df_realisasi['Penempatan'] / self.df_realisasi['Jumlah Peserta'] * 100
                        ).round(2)
                        self.log_message(f"✓ Calculated placement percentages")
                    
                    # Summary statistics
                    total_peserta = self.df_realisasi['Jumlah Peserta'].sum()
                    total_penempatan = self.df_realisasi['Penempatan'].sum()
                    avg_pct = (total_penempatan / total_peserta * 100) if total_peserta > 0 else 0
                    
                    self.log_message(f"\n📊 Summary:")
                    self.log_message(f"  Total Participants: {total_peserta}")
                    self.log_message(f"  Total Placed: {total_penempatan}")
                    self.log_message(f"  Overall Placement Rate: {avg_pct:.2f}%")
                
                self.log_message(f"\nFirst row preview:")
                self.log_message(str(self.df_realisasi.head(1)))
                
            except Exception as e:
                self.log_message(f"✗ Error: {str(e)}")
        
        threading.Thread(target=load, daemon=True).start()

    def show_data_table_view(self):
        """Show data in horizontal table format (Excel-like)"""
        self.view_output.delete(1.0, tk.END)
        
        dataset_type = self.view_dataset_var.get()
        
        if dataset_type == "training":
            df = self.df_pelatihan
            if df is None:
                self.log_message("❌ Please load training data first!", self.view_output)
                return
            title = "TRAINING PROGRAMS DATA - TABLE VIEW"
            display_columns = ['NO', 'PROGRAM PELATIHAN', 'DURASI JP (@45 Menit)', 'Deskripsi Tujuan Program Pelatihan/Kompetensi']
        
        elif dataset_type == "job":
            df = self.df_lowongan
            if df is None:
                self.log_message("❌ Please load job data first!", self.view_output)
                return
            title = "JOB POSITIONS DATA - TABLE VIEW"
            display_columns = ['NO', 'NAMA PERUSAHAAN', 'Nama Jabatan (Sumber Perusahaan)', 'Deskripsi Pekerjaan', 'Perkiraan Lowongan']
        
        else:  # realisasi
            df = self.df_realisasi
            if df is None:
                self.log_message("❌ Please load realisasi penempatan data first!", self.view_output)
                return
            title = "REALISASI PENEMPATAN DATA - TABLE VIEW"
            display_columns = ['No', 'Kejuruan', 'Program Pelatihan', 'Jumlah Peserta', 'Penempatan', '% Penempatan']
        
        # Filter to only existing columns
        columns = [col for col in display_columns if col in df.columns]
        
        if not columns:
            self.log_message("❌ No matching columns found in dataset!", self.view_output)
            return
        
        try:
            n_records = int(self.view_records_spinbox.get())
        except:
            n_records = 20
        
        n_records = min(n_records, len(df))
        
        # Display header
        self.log_message("=" * 150, self.view_output)
        self.log_message(title, self.view_output)
        self.log_message("=" * 150, self.view_output)
        self.log_message(f"\n📊 Total records: {len(df)} | Showing: {n_records} records", self.view_output)
        self.log_message(f"📋 Displaying columns: {len(columns)}\n", self.view_output)
        
        # Create table header
        self.log_message("=" * 150, self.view_output)
        
        # Column headers
        col_width = 30  # Fixed width for each column
        header_line = "│ " + " │ ".join([f"{col[:28]:^28}" for col in columns]) + " │"
        separator = "├" + "┼".join(["─" * 30 for _ in columns]) + "┤"
        top_border = "┌" + "┬".join(["─" * 30 for _ in columns]) + "┐"
        bottom_border = "└" + "┴".join(["─" * 30 for _ in columns]) + "┘"
        
        self.log_message(top_border, self.view_output)
        self.log_message(header_line, self.view_output)
        self.log_message(separator, self.view_output)
        
        # Display rows
        for idx in range(n_records):
            row = df.iloc[idx]
            
            # Truncate long values
            row_values = []
            for col in columns:
                val = str(row[col]) if pd.notna(row[col]) else ""
                # Truncate if too long
                if len(val) > 28:
                    val = val[:25] + "..."
                row_values.append(f"{val:<28}")
            
            row_line = "│ " + " │ ".join(row_values) + " │"
            self.log_message(row_line, self.view_output)
        
        self.log_message(bottom_border, self.view_output)
        
        self.log_message(f"\n{'=' * 150}", self.view_output)
        self.log_message(f"✅ DISPLAYED {n_records} of {len(df)} RECORDS", self.view_output)
        self.log_message(f"{'=' * 150}", self.view_output)
        
        # Show column list
        self.log_message(f"\n📋 Displayed Columns ({len(columns)}):", self.view_output)
        for i, col in enumerate(columns, 1):
            self.log_message(f"  {i}. {col}", self.view_output)
        
        # Add summary statistics for realisasi data
        if dataset_type == "realisasi" and len(df) > 0:
            self.log_message(f"\n📈 SUMMARY STATISTICS:", self.view_output)
            total_peserta = df['Jumlah Peserta'].sum() if 'Jumlah Peserta' in df.columns else 0
            total_penempatan = df['Penempatan'].sum() if 'Penempatan' in df.columns else 0
            avg_pct = (total_penempatan / total_peserta * 100) if total_peserta > 0 else 0
            
            self.log_message(f"  • Total Participants: {total_peserta:,}", self.view_output)
            self.log_message(f"  • Total Placed: {total_penempatan:,}", self.view_output)
            self.log_message(f"  • Overall Placement Rate: {avg_pct:.2f}%", self.view_output)
            
            # Top 3 programs by placement percentage
            if '% Penempatan' in df.columns:
                try:
                    # Convert percentage string to float
                    df_temp = df.copy()
                    df_temp['% Penempatan_float'] = df_temp['% Penempatan'].str.replace('%', '').astype(float)
                    top_programs = df_temp.nlargest(3, '% Penempatan_float')
                    
                    self.log_message(f"\n🏆 TOP 3 PROGRAMS BY PLACEMENT RATE:", self.view_output)
                    for i, (idx, row) in enumerate(top_programs.iterrows(), 1):
                        program = row['Program Pelatihan']
                        rate = row['% Penempatan']
                        self.log_message(f"  {i}. {program}: {rate}", self.view_output)
                except:
                    pass

    def show_data_list_view(self):
        """Show data in vertical list format (detailed)"""
        self.view_output.delete(1.0, tk.END)
        
        dataset_type = self.view_dataset_var.get()
        
        if dataset_type == "training":
            df = self.df_pelatihan
            if df is None:
                self.log_message("❌ Please load training data first!", self.view_output)
                return
            title = "TRAINING PROGRAMS DATA - LIST VIEW"
            display_columns = ['NO', 'PROGRAM PELATIHAN', 'DURASI JP (@45 Menit)', 'Deskripsi Tujuan Program Pelatihan/Kompetensi']
        
        elif dataset_type == "job":
            df = self.df_lowongan
            if df is None:
                self.log_message("❌ Please load job data first!", self.view_output)
                return
            title = "JOB POSITIONS DATA - LIST VIEW"
            display_columns = ['NO', 'NAMA PERUSAHAAN', 'Nama Jabatan (Sumber Perusahaan)', 'Deskripsi Pekerjaan', 'Perkiraan Lowongan']
        
        else:  # realisasi
            df = self.df_realisasi
            if df is None:
                self.log_message("❌ Please load realisasi penempatan data first!", self.view_output)
                return
            title = "REALISASI PENEMPATAN DATA - LIST VIEW"
            display_columns = ['No', 'Kejuruan', 'Program Pelatihan', 'Jumlah Peserta', 'Penempatan', '% Penempatan']
        
        # Filter to only existing columns
        columns = [col for col in display_columns if col in df.columns]
        
        if not columns:
            self.log_message("❌ No matching columns found in dataset!", self.view_output)
            return
        
        try:
            n_records = int(self.view_records_spinbox.get())
        except:
            n_records = 20
        
        n_records = min(n_records, len(df))
        
        # Display header
        self.log_message("=" * 120, self.view_output)
        self.log_message(title, self.view_output)
        self.log_message("=" * 120, self.view_output)
        self.log_message(f"\n📊 Total records: {len(df)} | Showing: {n_records} records", self.view_output)
        self.log_message(f"📋 Displaying columns: {len(columns)}\n", self.view_output)
        
        # Display each record with all columns
        for idx in range(n_records):
            row = df.iloc[idx]
            
            self.log_message("\n" + "─" * 120, self.view_output)
            self.log_message(f"📋 RECORD #{idx}", self.view_output)
            self.log_message("─" * 120, self.view_output)
            
            # Create a table for this record
            self.log_message(f"┌{'─' * 35}┬{'─' * 82}┐", self.view_output)
            self.log_message(f"│ {'Column Name':<33} │ {'Value':<80} │", self.view_output)
            self.log_message(f"├{'─' * 35}┼{'─' * 82}┤", self.view_output)
            
            for col in columns:
                value = str(row[col]) if pd.notna(row[col]) else "(empty)"
                
                # Handle long values - split into multiple lines
                max_width = 80
                if len(value) <= max_width:
                    self.log_message(f"│ {col:<33} │ {value:<80} │", self.view_output)
                else:
                    # First line
                    self.log_message(f"│ {col:<33} │ {value[:max_width]:<80} │", self.view_output)
                    # Continuation lines
                    remaining = value[max_width:]
                    while remaining:
                        chunk = remaining[:max_width]
                        remaining = remaining[max_width:]
                        self.log_message(f"│ {'':<33} │ {chunk:<80} │", self.view_output)
            
            self.log_message(f"└{'─' * 35}┴{'─' * 82}┘", self.view_output)
        
        self.log_message(f"\n{'=' * 120}", self.view_output)
        self.log_message(f"✅ DISPLAYED {n_records} of {len(df)} RECORDS", self.view_output)
        self.log_message(f"{'=' * 120}", self.view_output)
        
        # Show column summary
        self.log_message(f"\n📋 Displayed Columns ({len(columns)}):", self.view_output)
        for i, col in enumerate(columns, 1):
            self.log_message(f"  {i:2d}. {col}", self.view_output)
        
        # Add summary statistics for realisasi data
        if dataset_type == "realisasi" and len(df) > 0:
            self.log_message(f"\n📈 SUMMARY STATISTICS:", self.view_output)
            total_peserta = df['Jumlah Peserta'].sum() if 'Jumlah Peserta' in df.columns else 0
            total_penempatan = df['Penempatan'].sum() if 'Penempatan' in df.columns else 0
            avg_pct = (total_penempatan / total_peserta * 100) if total_peserta > 0 else 0
            
            self.log_message(f"  • Total Participants: {total_peserta:,}", self.view_output)
            self.log_message(f"  • Total Placed: {total_penempatan:,}", self.view_output)
            self.log_message(f"  • Overall Placement Rate: {avg_pct:.2f}%", self.view_output)
            
            # Find highest and lowest placement rates
            if '% Penempatan' in df.columns:
                try:
                    # Convert percentage string to float
                    df_temp = df.copy()
                    df_temp['% Penempatan_float'] = df_temp['% Penempatan'].str.replace('%', '').astype(float)
                    
                    # Highest placement rate
                    highest_idx = df_temp['% Penempatan_float'].idxmax()
                    highest_row = df_temp.loc[highest_idx]
                    
                    # Lowest placement rate (excluding zero)
                    non_zero = df_temp[df_temp['% Penempatan_float'] > 0]
                    if len(non_zero) > 0:
                        lowest_idx = non_zero['% Penempatan_float'].idxmin()
                        lowest_row = df_temp.loc[lowest_idx]
                    
                    self.log_message(f"\n📊 PLACEMENT RATE EXTREMES:", self.view_output)
                    self.log_message(f"  🏆 Highest: {highest_row['Program Pelatihan']} ({highest_row['% Penempatan']})", self.view_output)
                    if len(non_zero) > 0:
                        self.log_message(f"  ⚠️  Lowest: {lowest_row['Program Pelatihan']} ({lowest_row['% Penempatan']})", self.view_output)
                except Exception as e:
                    print(f"Error calculating placement rates: {e}")

    def fill_missing_pelatihan(self):
        """Fill missing values in training data"""
        def fill_tujuan(row):
            if pd.isna(row['Deskripsi Tujuan Program Pelatihan/Kompetensi']) or str(row['Deskripsi Tujuan Program Pelatihan/Kompetensi']).strip() == '':
                program = row['PROGRAM PELATIHAN'].strip()
                return f"Setelah mengikuti pelatihan ini peserta kompeten dalam melaksanakan pekerjaan {program.lower()} sesuai standar dan SOP di tempat kerja."
            return row['Deskripsi Tujuan Program Pelatihan/Kompetensi']
        
        # def fill_deskripsi(row):
        #     if pd.isna(row['Deskripsi Program']) or str(row['Deskripsi Program']).strip() == '':
        #         program = row['PROGRAM PELATIHAN'].strip()
        #         return f"Pelatihan ini adalah pelatihan untuk melaksanakan pekerjaan {program.lower()} sesuai standar dan SOP di tempat kerja."
        #     return row['Deskripsi Program']
        
        self.df_pelatihan['Deskripsi Tujuan Program Pelatihan/Kompetensi'] = self.df_pelatihan.apply(fill_tujuan, axis=1)
        # self.df_pelatihan['Deskripsi Program'] = self.df_pelatihan.apply(fill_deskripsi, axis=1)
        self.log_message("✓ Missing values filled")

    def expand_synonyms(self, text):
        synonym_map = {
            'tata udara': 'ac tata udara',
            'pemasangan': 'instalasi pasang',
            'perbaikan': 'repair baik service',
            'perawatan': 'maintenance rawat service',
        }
        
        for key, value in synonym_map.items():
            if key in text:
                text = text.replace(key, value)
        return text

    def normalize_text(self, text):
        """Normalize text: lowercase, remove punctuation and numbers"""
        if pd.isna(text):
            return ""
        text = str(text).lower()
        # text = self.expand_synonyms(text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', '', text)
        text = ' '.join(text.split())
        return text
    
    def remove_stopwords(self, text):
        """Remove Indonesian stopwords"""
        if not text:
            return ""
        words = text.split()
        filtered_words = [w for w in words if w not in self.stopwords]
        return ' '.join(filtered_words)
    
    def tokenize_text(self, text):
        """Tokenize text into words"""
        if not text:
            return []
        return text.split()
    
    def stem_text(self, text):
        """Stem text using Sastrawi (applied on whole text for backward compatibility)"""
        if not text:
            return ""
        if SASTRAWI_AVAILABLE:
            return stemmer.stem(text)
        else:
            return text  # Return original if Sastrawi not available
    
    def stem_tokens(self, tokens):
        """Stem each token individually using Sastrawi with custom rules"""
        if not tokens:
            return []
        if SASTRAWI_AVAILABLE:
            stemmed = []
            for token in tokens:
                # Apply custom rules first
                if token in self.custom_stem_rules:
                    stemmed.append(self.custom_stem_rules[token])
                else:
                    stemmed.append(stemmer.stem(token))
            return stemmed
        else:
            return tokens
    
    def load_document_options(self):
        """Load available documents into comboboxes"""
        if self.df_pelatihan is None or self.df_lowongan is None:
            messagebox.showwarning("Warning", 
                                 "Please load and preprocess both datasets first!\n"
                                 "Go to 'Import Data' and 'Preprocessing' tabs.")
            return
        
        if 'preprocessed_text' not in self.df_pelatihan.columns:
            messagebox.showwarning("Warning", 
                                 "Please preprocess the data first!\n"
                                 "Go to 'Preprocessing' tab and click 'Process All Data'.")
            return
        
        # Load pelatihan options
        pelatihan_options = [f"{i}: {row['PROGRAM PELATIHAN']}" 
                            for i, row in self.df_pelatihan.iterrows()]
        self.pelatihan_combo['values'] = pelatihan_options
        if pelatihan_options:
            self.pelatihan_combo.current(0)
        
        # Load lowongan options
        lowongan_options = [f"{i}: {row['Nama Jabatan (Sumber Perusahaan)']}" 
                           for i, row in self.df_lowongan.iterrows()]
        self.lowongan_combo['values'] = lowongan_options
        if lowongan_options:
            self.lowongan_combo.current(0)
        
        messagebox.showinfo("Success", "Document options loaded!\nSelect documents and run TF-IDF steps.")
    
    def get_selected_documents(self):
        """Get selected document indices"""
        try:
            pel_idx = int(self.pelatihan_combo.get().split(':')[0])
            low_idx = int(self.lowongan_combo.get().split(':')[0])
            return pel_idx, low_idx
        except:
            messagebox.showerror("Error", "Please select both documents first!")
            return None, None
    
    def show_tokens(self):
        """Step 1: Show tokens from both documents"""
        self.tfidf_output.delete(1.0, tk.END)
        
        pel_idx, low_idx = self.get_selected_documents()
        if pel_idx is None:
            return
        
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("STEP 1: TOKENIZATION", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        # Get documents
        doc1 = self.df_pelatihan.iloc[pel_idx]
        doc2 = self.df_lowongan.iloc[low_idx]
        
        self.log_message(f"\n📄 Document 1 (D1): {doc1['PROGRAM PELATIHAN']}", self.tfidf_output)
        self.log_message(f"Original: {doc1['text_features'][:150]}...", self.tfidf_output)
        tokens1 = doc1['stemmed_tokens'] if 'stemmed_tokens' in doc1 else doc1['tokens']
        self.log_message(f"\nTokens D1: {tokens1}", self.tfidf_output)
        self.log_message(f"Total tokens: {len(tokens1)}", self.tfidf_output)
        
        self.log_message(f"\n📄 Document 2 (D2): {doc2['Nama Jabatan (Sumber Perusahaan)']}", self.tfidf_output)
        self.log_message(f"Original: {doc2['text_features'][:150]}...", self.tfidf_output)
        tokens2 = doc2['stemmed_tokens'] if 'stemmed_tokens' in doc2 else doc2['tokens']
        self.log_message(f"\nTokens D2: {tokens2}", self.tfidf_output)
        self.log_message(f"Total tokens: {len(tokens2)}", self.tfidf_output)
        
        # Get all unique terms
        all_terms = sorted(set(tokens1 + tokens2))
        self.log_message(f"\n📊 Unique terms across both documents: {len(all_terms)}", self.tfidf_output)
        self.log_message(f"Terms: {all_terms}", self.tfidf_output)
        
        # Store for later use
        self.current_doc1_tokens = tokens1
        self.current_doc2_tokens = tokens2
        self.current_all_terms = all_terms
    
    def calculate_tf(self):
        """Step 2: Calculate Term Frequency"""
        if not hasattr(self, 'current_doc1_tokens'):
            messagebox.showwarning("Warning", "Please run Step 1 first!")
            return
        
        self.tfidf_output.delete(1.0, tk.END)
        
        pel_idx, low_idx = self.get_selected_documents()
        doc1_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
        doc2_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan (Sumber Perusahaan)']
        
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("STEP 2: TERM FREQUENCY (TF)", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        self.log_message("\nFormula: TF(t,d) = count of term t in document d / total terms in d", 
                        self.tfidf_output)
        
        tokens1 = self.current_doc1_tokens
        tokens2 = self.current_doc2_tokens
        
        # Calculate TF for D1
        self.log_message(f"\n📄 D1: {doc1_name}", self.tfidf_output)
        self.log_message(f"Total tokens in D1: {len(tokens1)}", self.tfidf_output)
        
        tf_d1 = {}
        for term in self.current_all_terms:
            count = tokens1.count(term)
            tf = count / len(tokens1) if len(tokens1) > 0 else 0
            tf_d1[term] = {'count': count, 'tf': tf}
        
        self.log_message("\nTF Calculation D1:", self.tfidf_output)
        self.log_message(f"{'Term':<20} {'Count':<10} {'TF (÷' + str(len(tokens1)) + ')':<20}", 
                        self.tfidf_output)
        self.log_message("-" * 50, self.tfidf_output)
        for term in self.current_all_terms[:15]:  # Show first 15
            self.log_message(f"{term:<20} {tf_d1[term]['count']:<10} "
                           f"{tf_d1[term]['count']}/{len(tokens1)} = {tf_d1[term]['tf']:.4f}", 
                           self.tfidf_output)
        if len(self.current_all_terms) > 15:
            self.log_message(f"... and {len(self.current_all_terms) - 15} more terms", 
                           self.tfidf_output)
        
        # Calculate TF for D2
        self.log_message(f"\n📄 D2: {doc2_name}", self.tfidf_output)
        self.log_message(f"Total tokens in D2: {len(tokens2)}", self.tfidf_output)
        
        tf_d2 = {}
        for term in self.current_all_terms:
            count = tokens2.count(term)
            tf = count / len(tokens2) if len(tokens2) > 0 else 0
            tf_d2[term] = {'count': count, 'tf': tf}
        
        self.log_message("\nTF Calculation D2:", self.tfidf_output)
        self.log_message(f"{'Term':<20} {'Count':<10} {'TF (÷' + str(len(tokens2)) + ')':<20}", 
                        self.tfidf_output)
        self.log_message("-" * 50, self.tfidf_output)
        for term in self.current_all_terms[:15]:
            self.log_message(f"{term:<20} {tf_d2[term]['count']:<10} "
                           f"{tf_d2[term]['count']}/{len(tokens2)} = {tf_d2[term]['tf']:.4f}", 
                           self.tfidf_output)
        if len(self.current_all_terms) > 15:
            self.log_message(f"... and {len(self.current_all_terms) - 15} more terms", 
                           self.tfidf_output)
        
        # Store results
        self.tf_d1 = tf_d1
        self.tf_d2 = tf_d2
    
    def calculate_df(self):
        """Step 3: Calculate Document Frequency"""
        if not hasattr(self, 'tf_d1'):
            messagebox.showwarning("Warning", "Please run Step 2 first!")
            return
        
        self.tfidf_output.delete(1.0, tk.END)
        
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("STEP 3: DOCUMENT FREQUENCY (DF)", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        self.log_message("\nDF(t) = Number of documents containing term t", self.tfidf_output)
        self.log_message("Total documents N = 2 (D1 + D2)", self.tfidf_output)
        
        # Calculate DF
        df_dict = {}
        for term in self.current_all_terms:
            count = 0
            if self.tf_d1[term]['count'] > 0:
                count += 1
            if self.tf_d2[term]['count'] > 0:
                count += 1
            df_dict[term] = count
        
        self.log_message(f"\n{'Term':<20} {'In D1?':<10} {'In D2?':<10} {'DF':<10}", 
                        self.tfidf_output)
        self.log_message("-" * 50, self.tfidf_output)
        
        for term in self.current_all_terms:
            in_d1 = "Yes" if self.tf_d1[term]['count'] > 0 else "No"
            in_d2 = "Yes" if self.tf_d2[term]['count'] > 0 else "No"
            self.log_message(f"{term:<20} {in_d1:<10} {in_d2:<10} {df_dict[term]:<10}", 
                           self.tfidf_output)
        
        self.df_dict = df_dict
    
    def calculate_idf(self):
        """Step 4: Calculate Inverse Document Frequency"""
        if not hasattr(self, 'df_dict'):
            messagebox.showwarning("Warning", "Please run Step 3 first!")
            return
        
        self.tfidf_output.delete(1.0, tk.END)
        
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("STEP 4: INVERSE DOCUMENT FREQUENCY (IDF)", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        self.log_message("\nFormula: IDF(t) = log(N / DF(t))", self.tfidf_output)
        self.log_message("where N = total documents = 2", self.tfidf_output)
        
        N = 2  # Total documents
        idf_dict = {}
        
        self.log_message(f"\n{'Term':<20} {'DF':<10} {'IDF Calculation':<30} {'IDF':<10}", 
                        self.tfidf_output)
        self.log_message("-" * 70, self.tfidf_output)
        
        for term in self.current_all_terms:
            df = self.df_dict[term]
            # idf = np.log((N + 1) / (df + 1)) + 1 # smoothing
            idf = np.log(N / df)
            idf_dict[term] = idf
            
            calc_str = f"log({N}/{df})" if df > 0 else "0"
            self.log_message(f"{term:<20} {df:<10} {calc_str:<30} {idf:.4f}", 
                           self.tfidf_output)
        
        self.log_message("\n💡 Interpretation:", self.tfidf_output)
        self.log_message("  • Higher IDF = term appears in fewer documents (more unique)", 
                        self.tfidf_output)
        self.log_message("  • Lower IDF = term appears in many documents (more common)", 
                        self.tfidf_output)
        
        self.idf_dict = idf_dict
    
    def calculate_tfidf(self):
        """Step 5: Calculate TF-IDF"""
        if not hasattr(self, 'idf_dict'):
            messagebox.showwarning("Warning", "Please run Step 4 first!")
            return
        
        self.tfidf_output.delete(1.0, tk.END)
        
        pel_idx, low_idx = self.get_selected_documents()
        doc1_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
        doc2_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan (Sumber Perusahaan)']
        
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("STEP 5: TF-IDF CALCULATION", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        self.log_message("\nFormula: TF-IDF(t,d) = TF(t,d) × IDF(t)", self.tfidf_output)
        
        # Calculate TF-IDF for D1
        tfidf_d1 = {}
        self.log_message(f"\n📄 D1: {doc1_name}", self.tfidf_output)
        self.log_message(f"{'Term':<20} {'TF':<15} {'IDF':<15} {'TF-IDF':<15}", 
                        self.tfidf_output)
        self.log_message("-" * 65, self.tfidf_output)
        
        for term in self.current_all_terms:
            tf = self.tf_d1[term]['tf']
            idf = self.idf_dict[term]
            tfidf = tf * idf
            tfidf_d1[term] = tfidf
            
            self.log_message(f"{term:<20} {tf:<15.4f} {idf:<15.4f} {tfidf:<15.4f}", 
                           self.tfidf_output)
        
        # Calculate TF-IDF for D2
        tfidf_d2 = {}
        self.log_message(f"\n📄 D2: {doc2_name}", self.tfidf_output)
        self.log_message(f"{'Term':<20} {'TF':<15} {'IDF':<15} {'TF-IDF':<15}", 
                        self.tfidf_output)
        self.log_message("-" * 65, self.tfidf_output)
        
        for term in self.current_all_terms:
            tf = self.tf_d2[term]['tf']
            idf = self.idf_dict[term]
            tfidf = tf * idf
            tfidf_d2[term] = tfidf
            
            self.log_message(f"{term:<20} {tf:<15.4f} {idf:<15.4f} {tfidf:<15.4f}", 
                           self.tfidf_output)
        
        # Comparison
        self.log_message("\n" + "=" * 80, self.tfidf_output)
        self.log_message("TF-IDF COMPARISON", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message(f"\n{'Term':<20} {'TF-IDF D1':<20} {'TF-IDF D2':<20}", 
                        self.tfidf_output)
        self.log_message("-" * 60, self.tfidf_output)
        
        for term in self.current_all_terms:
            self.log_message(f"{term:<20} {tfidf_d1[term]:<20.4f} {tfidf_d2[term]:<20.4f}", 
                           self.tfidf_output)
        
        self.tfidf_d1 = tfidf_d1
        self.tfidf_d2 = tfidf_d2
    
    def calculate_similarity(self):
        """Step 6: Calculate Cosine Similarity"""
        if not hasattr(self, 'tfidf_d1'):
            messagebox.showwarning("Warning", "Please run Step 5 first!")
            return
        
        self.tfidf_output.delete(1.0, tk.END)
        
        pel_idx, low_idx = self.get_selected_documents()
        doc1_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
        doc2_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan (Sumber Perusahaan)']
        
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("STEP 6: COSINE SIMILARITY", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        self.log_message("\nFormula: Cosine Similarity = (A · B) / (||A|| × ||B||)", 
                        self.tfidf_output)
        self.log_message("where:", self.tfidf_output)
        self.log_message("  • A · B = dot product of vectors A and B", self.tfidf_output)
        self.log_message("  • ||A|| = magnitude (length) of vector A", self.tfidf_output)
        self.log_message("  • ||B|| = magnitude (length) of vector B", self.tfidf_output)
        
        # Create vectors
        vec_d1 = [self.tfidf_d1[term] for term in self.current_all_terms]
        vec_d2 = [self.tfidf_d2[term] for term in self.current_all_terms]
        
        self.log_message(f"\n📊 Vector D1: {[f'{v:.4f}' for v in vec_d1]}", self.tfidf_output)
        self.log_message(f"📊 Vector D2: {[f'{v:.4f}' for v in vec_d2]}", self.tfidf_output)
        
        # Calculate dot product
        self.log_message("\n1️⃣ Calculate Dot Product (A · B):", self.tfidf_output)
        dot_product = sum(a * b for a, b in zip(vec_d1, vec_d2))
        self.log_message("   A · B = " + " + ".join([f"({vec_d1[i]:.4f} × {vec_d2[i]:.4f})" 
                                                     for i in range(min(5, len(vec_d1)))]) + "...", 
                        self.tfidf_output)
        self.log_message(f"   A · B = {dot_product:.6f}", self.tfidf_output)
        
        # Calculate magnitudes
        self.log_message("\n2️⃣ Calculate Magnitude ||A||:", self.tfidf_output)
        mag_d1 = np.sqrt(sum(a * a for a in vec_d1))
        self.log_message(f"   ||A|| = √(" + " + ".join([f"{v:.4f}²" for v in vec_d1[:5]]) + "...)", 
                        self.tfidf_output)
        self.log_message(f"   ||A|| = {mag_d1:.6f}", self.tfidf_output)
        
        self.log_message("\n3️⃣ Calculate Magnitude ||B||:", self.tfidf_output)
        mag_d2 = np.sqrt(sum(b * b for b in vec_d2))
        self.log_message(f"   ||B|| = √(" + " + ".join([f"{v:.4f}²" for v in vec_d2[:5]]) + "...)", 
                        self.tfidf_output)
        self.log_message(f"   ||B|| = {mag_d2:.6f}", self.tfidf_output)
        
        # Calculate cosine similarity
        if mag_d1 > 0 and mag_d2 > 0:
            similarity = dot_product / (mag_d1 * mag_d2)
        else:
            similarity = 0
        
        self.log_message("\n4️⃣ Calculate Cosine Similarity:", self.tfidf_output)
        self.log_message(f"   Similarity = {dot_product:.6f} / ({mag_d1:.6f} × {mag_d2:.6f})", 
                        self.tfidf_output)
        self.log_message(f"   Similarity = {dot_product:.6f} / {mag_d1 * mag_d2:.6f}", 
                        self.tfidf_output)
        self.log_message(f"   Similarity = {similarity:.6f}", self.tfidf_output)
        
        # Interpretation
        self.log_message("\n" + "=" * 80, self.tfidf_output)
        self.log_message("📊 RESULT", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message(f"\nCosine Similarity between:", self.tfidf_output)
        self.log_message(f"  • D1: {doc1_name}", self.tfidf_output)
        self.log_message(f"  • D2: {doc2_name}", self.tfidf_output)
        self.log_message(f"\n  Similarity Score: {similarity:.4f} ({similarity*100:.2f}%)", 
                        self.tfidf_output)
        
        if similarity >= 0.80:
            interpretation = "VERY HIGH - Excellent match!"
        elif similarity >= 0.65:
            interpretation = "HIGH - Good match"
        elif similarity >= 0.50:
            interpretation = "MEDIUM - Moderate match"
        else:
            interpretation = "LOW - Poor match"
        
        self.log_message(f"  Interpretation: {interpretation}", self.tfidf_output)
        
        self.log_message("\n💡 Similarity Range:", self.tfidf_output)
        self.log_message("  • 1.00 = Identical documents", self.tfidf_output)
        self.log_message("  • 0.80-1.00 = Very high similarity", self.tfidf_output)
        self.log_message("  • 0.65-0.80 = High similarity", self.tfidf_output)
        self.log_message("  • 0.50-0.65 = Medium similarity", self.tfidf_output)
        self.log_message("  • 0.00-0.50 = Low similarity", self.tfidf_output)
        
        self.current_similarity = similarity

        pel_idx, low_idx = self.get_selected_documents()
        self.save_tfidf_calculation(pel_idx, low_idx)        
    
    def run_all_tfidf_steps(self):
        """Run all TF-IDF steps sequentially"""
        if not hasattr(self, 'current_doc1_tokens'):
            self.show_tokens()
        
        steps = [
            self.calculate_tf,
            self.calculate_df,
            self.calculate_idf,
            self.calculate_tfidf,
            self.calculate_similarity
        ]
        
        for step in steps:
            step()
            self.root.update()

    def save_tfidf_sample_from_sklearn(self, vectorizer, tfidf_matrix, pel_idx, low_idx, similarity):
        """Save TF-IDF calculation sample from sklearn results"""
        if not self.current_experiment_id or not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            training_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
            job_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan (Sumber Perusahaan)']
            
            # Get feature names (terms)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get TF-IDF vectors for these documents
            n_pelatihan = len(self.df_pelatihan)
            training_vector = tfidf_matrix[pel_idx].toarray()[0]
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
            
            query = """
            INSERT INTO tfidf_calculations 
            (experiment_id, training_index, training_name, job_index, job_name,
            unique_terms_count, terms_json, tfidf_training_json, tfidf_job_json, cosine_similarity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                self.current_experiment_id,
                int(pel_idx),
                training_name,
                int(low_idx),
                job_name,
                len(unique_terms),
                json.dumps(unique_terms),
                json.dumps(tfidf_training),
                json.dumps(tfidf_job),
                float(similarity)
            )
            
            cursor.execute(query, values)
            self.db_connection.commit()
            cursor.close()
            
        except Error as e:
            print(f"✗ Error saving TF-IDF sample: {e}")

    def calculate_all_documents(self):
        """Calculate similarity matrix for all documents"""
        # Check if data is loaded
        if self.df_pelatihan is None or self.df_lowongan is None:
            messagebox.showwarning("Warning", "Please load data first!\nGo to 'Import Data' tab.")
            return
        
        # Check if preprocessing is done
        if 'preprocessed_text' not in self.df_pelatihan.columns or 'preprocessed_text' not in self.df_lowongan.columns:
            messagebox.showwarning("Warning", 
                                "Please preprocess data first!\n\n"
                                "Go to 'Preprocessing' tab and click:\n"
                                "'▶ Process All Data'")
            return
        
        # Check if preprocessed data is not empty
        if self.df_pelatihan['preprocessed_text'].isna().all() or self.df_lowongan['preprocessed_text'].isna().all():
            messagebox.showwarning("Warning", 
                                "Preprocessing data is empty!\n\n"
                                "Please run preprocessing again.")
            return
        
        self.tfidf_output.delete(1.0, tk.END)
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("CALCULATING SIMILARITY MATRIX", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        # Use sklearn for full matrix (more efficient for many documents)
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Combine all texts
        all_texts = list(self.df_pelatihan['preprocessed_text']) + \
                list(self.df_lowongan['preprocessed_text'])
        
        # Calculate TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        self.log_message("✓ TF-IDF vectors created\n", self.tfidf_output)
        
        # Split back
        n_pelatihan = len(self.df_pelatihan)
        pelatihan_vectors = tfidf_matrix[:n_pelatihan]
        lowongan_vectors = tfidf_matrix[n_pelatihan:]
        
        self.log_message("Step 2/3: Calculating cosine similarities...", self.tfidf_output)
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(pelatihan_vectors, lowongan_vectors)
        self.log_message("✓ Similarity matrix calculated\n", self.tfidf_output)
        
        # Display results
        self.log_message("=" * 150, self.tfidf_output)
        self.log_message("SIMILARITY MATRIX - ALL DOCUMENTS", self.tfidf_output)
        self.log_message("=" * 150, self.tfidf_output)
        self.log_message(f"\n📊 Matrix Information:", self.tfidf_output)
        self.log_message(f"   • Total Training Programs: {n_pelatihan}", self.tfidf_output)
        self.log_message(f"   • Total Job Positions: {len(self.df_lowongan)}", self.tfidf_output)
        self.log_message(f"   • Matrix Shape: {similarity_matrix.shape} (rows × columns)", self.tfidf_output)
        self.log_message(f"   • Total Calculations: {similarity_matrix.size} similarity scores", self.tfidf_output)
        self.log_message(f"   • Unique Terms in Vocabulary: {len(vectorizer.vocabulary_)}", self.tfidf_output)
        
        # Statistics
        avg_similarity = similarity_matrix.mean()
        max_similarity = similarity_matrix.max()
        min_similarity = similarity_matrix.min()
        
        self.log_message(f"\n📈 Similarity Statistics:", self.tfidf_output)
        self.log_message(f"   • Average Similarity: {avg_similarity:.4f} ({avg_similarity*100:.2f}%)", self.tfidf_output)
        self.log_message(f"   • Maximum Similarity: {max_similarity:.4f} ({max_similarity*100:.2f}%)", self.tfidf_output)
        self.log_message(f"   • Minimum Similarity: {min_similarity:.4f} ({min_similarity*100:.2f}%)", self.tfidf_output)
        
        # Count by match levels using self.match_thresholds
        excellent = np.sum(similarity_matrix >= self.match_thresholds['excellent'])
        very_good = np.sum((similarity_matrix >= self.match_thresholds['very_good']) & 
                        (similarity_matrix < self.match_thresholds['excellent']))
        good = np.sum((similarity_matrix >= self.match_thresholds['good']) & 
                    (similarity_matrix < self.match_thresholds['very_good']))
        fair = np.sum((similarity_matrix >= self.match_thresholds['fair']) & 
                    (similarity_matrix < self.match_thresholds['good']))
        weak = np.sum(similarity_matrix < self.match_thresholds['fair'])

        self.log_message(f"\n🎯 Match Level Distribution:", self.tfidf_output)
        self.log_message(f"   • 🟢 Excellent (≥{self.match_thresholds['excellent']*100:.0f}%): {excellent} pairs ({excellent/similarity_matrix.size*100:.1f}%)", self.tfidf_output)
        self.log_message(f"   • 🟢 Very Good ({self.match_thresholds['very_good']*100:.0f}-{self.match_thresholds['excellent']*100-1:.0f}%): {very_good} pairs ({very_good/similarity_matrix.size*100:.1f}%)", self.tfidf_output)
        self.log_message(f"   • 🟡 Good ({self.match_thresholds['good']*100:.0f}-{self.match_thresholds['very_good']*100-1:.0f}%): {good} pairs ({good/similarity_matrix.size*100:.1f}%)", self.tfidf_output)
        self.log_message(f"   • 🟡 Fair ({self.match_thresholds['fair']*100:.0f}-{self.match_thresholds['good']*100-1:.0f}%): {fair} pairs ({fair/similarity_matrix.size*100:.1f}%)", self.tfidf_output)
        self.log_message(f"   • 🔴 Weak (<{self.match_thresholds['fair']*100:.0f}%): {weak} pairs ({weak/similarity_matrix.size*100:.1f}%)", self.tfidf_output)     

        # Top matches for each job - SQL TABLE FORMAT
        self.log_message("\n\nStep 3/3: Generating top matches table...", self.tfidf_output)
        self.log_message("\n" + "=" * 150, self.tfidf_output)
        self.log_message("TOP 3 TRAINING PROGRAMS FOR EACH JOB POSITION", self.tfidf_output)
        self.log_message("=" * 150, self.tfidf_output)
        
        # Table header
        self.log_message(
            f"\n┌{'─' * 6}┬{'─' * 45}┬{'─' * 55}┬{'─' * 6}┬{'─' * 13}┬{'─' * 10}┬{'─' * 12}┐",
            self.tfidf_output
        )
        self.log_message(
            f"│ {'Job':<4} │ {'Job Position':<43} │ {'Training Program':<53} │ {'Rank':<4} │ {'Similarity':<11} │ {'Score %':<8} │ {'Match':<10} │",
            self.tfidf_output
        )
        self.log_message(
            f"│ {'Idx':<4} │ {'':<43} │ {'':<53} │ {'':<4} │ {'Score':<11} │ {'':<8} │ {'Level':<10} │",
            self.tfidf_output
        )
        self.log_message(
            f"├{'─' * 6}┼{'─' * 45}┼{'─' * 55}┼{'─' * 6}┼{'─' * 13}┼{'─' * 10}┼{'─' * 12}┤",
            self.tfidf_output
        )
        
        # Process each job with progress
        total_jobs = len(self.df_lowongan)
        for low_idx in range(total_jobs):
            lowongan_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan (Sumber Perusahaan)']
            similarities = similarity_matrix[:, low_idx]
            top_3_indices = np.argsort(similarities)[-3:][::-1]
            
            for rank, pel_idx in enumerate(top_3_indices, 1):
                pelatihan_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
                similarity = similarities[pel_idx]
                
                # Determine match level
                if similarity >= self.match_thresholds['excellent']:
                    match_level = "excellent"
                    match_emoji = "🟢"
                elif similarity >= self.match_thresholds['very_good']:
                    match_level = "very_good"
                    match_emoji = "🟢"
                elif similarity >= self.match_thresholds['good']:
                    match_level = "good"
                    match_emoji = "🟡"
                elif similarity >= self.match_thresholds['fair']:
                    match_level = "fair"
                    match_emoji = "🟡"
                else:
                    match_level = "weak"
                    match_emoji = "🔴"
                
                # Truncate names if too long
                job_display = lowongan_name[:41] + ".." if len(lowongan_name) > 43 else lowongan_name
                program_display = pelatihan_name[:51] + ".." if len(pelatihan_name) > 53 else pelatihan_name
                
                self.log_message(
                    f"│ {low_idx:<4} │ {job_display:<43} │ {program_display:<53} │ {rank:<4} │ {similarity:<11.8f} │ {similarity*100:<8.2f} │ {match_emoji} {match_level:<8} │",
                    self.tfidf_output
                )

        # Table footer
        self.log_message(
            f"└{'─' * 6}┴{'─' * 45}┴{'─' * 55}┴{'─' * 6}┴{'─' * 13}┴{'─' * 10}┴{'─' * 12}┘",
            self.tfidf_output
        )
        
        # Completion message
        self.log_message("\n" + "=" * 150, self.tfidf_output)
        self.log_message("✅ SIMILARITY CALCULATION COMPLETED", self.tfidf_output)
        self.log_message("=" * 150, self.tfidf_output)
        self.log_message(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.tfidf_output)
        self.log_message(f"💡 You can now proceed to the 'Recommendations' tab to get detailed recommendations", self.tfidf_output)
                
        messagebox.showinfo("Complete", 
                        f"Similarity calculation completed!\n\n"
                        f"• {similarity_matrix.size} similarity scores calculated\n"
                        f"• Average similarity: {avg_similarity:.2%}\n"
                        f"• Ready for recommendations")
        
        # Store for later use
        self.similarity_matrix = similarity_matrix
        self.save_similarity_matrix()

        self.log_message("\nSaving sample TF-IDF calculations to database...", self.tfidf_output)
        sample_count = min(5, len(self.df_lowongan))
        
        for low_idx in range(sample_count):
            similarities = similarity_matrix[:, low_idx]
            top_pel_idx = np.argmax(similarities)
            self.save_tfidf_sample_from_sklearn(
                vectorizer, 
                tfidf_matrix, 
                top_pel_idx, 
                low_idx, 
                similarities[top_pel_idx]
            )
        
        self.log_message(f"\n✓ Saved {sample_count} TF-IDF calculation samples", self.tfidf_output)

    def show_preprocessing_step(self, step):
        """Show specific preprocessing step for selected row"""
        self.preprocess_output.delete(1.0, tk.END)
        
        # Get selected dataset
        if self.dataset_var.get() == "pelatihan":
            df = self.df_pelatihan
            if df is None:
                self.log_message("Please load Training Data first!", self.preprocess_output)
                return
            text_col = 'PROGRAM PELATIHAN'
        else:
            df = self.df_lowongan
            if df is None:
                self.log_message("Please load Job Data first!", self.preprocess_output)
                return
            text_col = 'Nama Jabatan (Sumber Perusahaan)'
        
        # Get row index
        try:
            row_idx = int(self.row_spinbox.get())
            if row_idx >= len(df):
                self.log_message(f"Row index out of range! Max: {len(df)-1}", 
                               self.preprocess_output)
                return
        except:
            self.log_message("Invalid row index!", self.preprocess_output)
            return
        
        row = df.iloc[row_idx]
        
        # Create combined text
        if self.dataset_var.get() == "pelatihan":
            original = (# f"{row['PROGRAM PELATIHAN']}" 
                        f"{row['Deskripsi Tujuan Program Pelatihan/Kompetensi']} "
                       # f"{row['Deskripsi Program']}"
                       )
        else:
            original = (# f"{row['Nama Jabatan (Sumber Perusahaan)']} {row.get('Nama KBJI Resmi (Mengacu ke KBJI)', '')} "
                       f"{row.get('Deskripsi Pekerjaan', '')} " 
                       # f"{row.get('Kompetensi', '')}"
                       )
        
        # Process based on step
        if step == 0:  # Original
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message(f"ORIGINAL TEXT - Row {row_idx}", self.preprocess_output)
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message(f"\n{text_col}: {row[text_col]}\n", self.preprocess_output)
            self.log_message("Text:", self.preprocess_output)
            self.log_message(original, self.preprocess_output)
            
        elif step == 1:  # Normalization
            normalized = self.normalize_text(original)
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message(f"STEP 1: NORMALIZATION - Row {row_idx}", self.preprocess_output)
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message("\nOriginal:", self.preprocess_output)
            self.log_message(original[:200] + "...", self.preprocess_output)
            self.log_message("\n→ After Normalization:", self.preprocess_output)
            self.log_message(normalized[:200] + "...", self.preprocess_output)
            self.log_message("\nChanges: Lowercase, removed punctuation & numbers", 
                           self.preprocess_output)
            
        elif step == 2:  # Stopword Removal
            normalized = self.normalize_text(original)
            no_stopwords = self.remove_stopwords(normalized)
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message(f"STEP 2: STOPWORD REMOVAL - Row {row_idx}", self.preprocess_output)
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message("\nAfter Normalization:", self.preprocess_output)
            self.log_message(normalized[:200] + "...", self.preprocess_output)
            self.log_message("\n→ After Stopword Removal:", self.preprocess_output)
            self.log_message(no_stopwords[:200] + "...", self.preprocess_output)
            
        elif step == 3:  # Tokenization
            normalized = self.normalize_text(original)
            no_stopwords = self.remove_stopwords(normalized)
            tokens = self.tokenize_text(no_stopwords)
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message(f"STEP 3: TOKENIZATION - Row {row_idx}", self.preprocess_output)
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message("\nAfter Stopword Removal:", self.preprocess_output)
            self.log_message(no_stopwords[:200] + "...", self.preprocess_output)
            self.log_message("\n→ Tokens (Words):", self.preprocess_output)
            self.log_message(str(tokens[:20]) + "...", self.preprocess_output)
            self.log_message(f"\nTotal tokens: {len(tokens)}", self.preprocess_output)
            
        elif step == 4:  # Stemming
            normalized = self.normalize_text(original)
            no_stopwords = self.remove_stopwords(normalized)
            tokens = self.tokenize_text(no_stopwords)
            if SASTRAWI_AVAILABLE:
                stemmed_tokens = self.stem_tokens(tokens)
                stemmed_text = ' '.join(stemmed_tokens)
                self.log_message("=" * 80, self.preprocess_output)
                self.log_message(f"STEP 4: STEMMING - Row {row_idx}", self.preprocess_output)
                self.log_message("=" * 80, self.preprocess_output)
                self.log_message("\nTokens Before Stemming:", self.preprocess_output)
                self.log_message(str(tokens[:20]) + "...", self.preprocess_output)
                self.log_message("\n→ Tokens After Stemming:", self.preprocess_output)
                self.log_message(str(stemmed_tokens[:20]) + "...", self.preprocess_output)
                self.log_message("\n\nStemming Results (word by word) (displayed max 99):", self.preprocess_output)
                self.log_message("\n┌──────┬─────────────────────┬─────────────────────┬─────────────┐", self.preprocess_output)
                self.log_message("│  No  │   Before Stemming   │   After Stemming    │   Status    │", self.preprocess_output)
                self.log_message("├──────┼─────────────────────┼─────────────────────┼─────────────┤", self.preprocess_output)
                for i, (before, after) in enumerate(zip(tokens[:99], stemmed_tokens[:99]), 1):
                    status = " Changed " if before != after else "Unchanged"
                    self.log_message(f"│ {i:4d} │ {before:19s} │ {after:19s} │ {status:11s} │", 
                                   self.preprocess_output)
                self.log_message("└──────┴─────────────────────┴─────────────────────┴─────────────┘", self.preprocess_output)
                self.log_message(f"\n\nFinal text after stemming:", self.preprocess_output)
                self.log_message(stemmed_text[:200] + "...", self.preprocess_output)
            else:
                self.log_message("Sastrawi library not available. Stemming skipped.", 
                               self.preprocess_output)
                
        elif step == 5:  # Show all steps
            self.log_message("=" * 80, self.preprocess_output)
            self.log_message(f"ALL PREPROCESSING STEPS - Row {row_idx}", self.preprocess_output)
            self.log_message("=" * 80, self.preprocess_output)
            
            self.log_message(f"\n[ORIGINAL] {text_col}:", self.preprocess_output)
            self.log_message(original[:150] + "...\n", self.preprocess_output)
            
            normalized = self.normalize_text(original)
            self.log_message("[STEP 1: NORMALIZATION]", self.preprocess_output)
            self.log_message(normalized[:150] + "...\n", self.preprocess_output)
            
            no_stopwords = self.remove_stopwords(normalized)
            self.log_message("[STEP 2: STOPWORD REMOVAL]", self.preprocess_output)
            self.log_message(no_stopwords[:150] + "...\n", self.preprocess_output)
            
            tokens = self.tokenize_text(no_stopwords)
            self.log_message("[STEP 3: TOKENIZATION]", self.preprocess_output)
            self.log_message(f"Tokens: {tokens[:15]}...", self.preprocess_output)
            self.log_message(f"Total: {len(tokens)} tokens\n", self.preprocess_output)
            
            if SASTRAWI_AVAILABLE:
                stemmed_tokens = self.stem_tokens(tokens)
                stemmed_text = ' '.join(stemmed_tokens)
                self.log_message("[STEP 4: STEMMING (per token) (displayed max 99)]", self.preprocess_output)
                self.log_message("Stemming results:\n", self.preprocess_output)
                self.log_message("┌──────┬─────────────────────┬─────────────────────┬─────────────┐", self.preprocess_output)
                self.log_message("│  No  │   Before Stemming   │   After Stemming    │   Status    │", self.preprocess_output)
                self.log_message("├──────┼─────────────────────┼─────────────────────┼─────────────┤", self.preprocess_output)
                for i, (before, after) in enumerate(zip(tokens[:99], stemmed_tokens[:99]), 1):
                    status = " Changed " if before != after else "Unchanged"
                    self.log_message(f"│ {i:4d} │ {before:19s} │ {after:19s} │ {status:11s} │", 
                                   self.preprocess_output)
                self.log_message("└──────┴─────────────────────┴─────────────────────┴─────────────┘", self.preprocess_output)
                self.log_message(f"\nStemmed text: {stemmed_text[:150]}...", self.preprocess_output)
                self.log_message(f"\nFinal tokens: {stemmed_tokens[:15]}...", self.preprocess_output)
                self.log_message(f"Total: {len(stemmed_tokens)} tokens", self.preprocess_output)

    def process_all_data(self):
        """Process all data through all preprocessing steps with caching"""
        self.preprocess_output.delete(1.0, tk.END)
        self.log_message("Processing all data...", self.preprocess_output)
        
        def process():
            # Process Training Data
            if self.df_pelatihan is not None:
                self.log_message("\n" + "=" * 80, self.preprocess_output)
                self.log_message("PROCESSING TRAINING DATA (PELATIHAN)", self.preprocess_output)
                self.log_message("=" * 80 + "\n", self.preprocess_output)
                
                # Generate cache key
                cache_key = f"training_{self.get_cache_key(self.df_pelatihan, 'pelatihan')}"
                
                # Try to load from cache
                self.log_message("Checking cache...", self.preprocess_output)
                cached_data = self.load_from_cache(cache_key)
                
                if cached_data is not None:
                    self.log_message("Cache found! Loading preprocessed data...", self.preprocess_output)
                    # Restore cached columns
                    for col in ['text_features', 'normalized', 'no_stopwords', 'tokens', 
                               'stemmed_tokens', 'stemmed', 'token_count', 'preprocessed_text']:
                        if col in cached_data:
                            self.df_pelatihan[col] = cached_data[col]
                    self.log_message(f"Loaded {len(self.df_pelatihan)} training programs from cache\n", 
                                self.preprocess_output)
                else:
                    self.log_message("No cache found. Processing from scratch...\n", self.preprocess_output)
                    
                    # Combine text features
                    self.df_pelatihan['text_features'] = (
                        self.df_pelatihan['Deskripsi Tujuan Program Pelatihan/Kompetensi'].fillna('')
                    )
                    
                    # Apply preprocessing
                    self.log_message("Step 1/5: Normalizing...", self.preprocess_output)
                    self.df_pelatihan['normalized'] = self.df_pelatihan['text_features'].apply(
                        self.normalize_text)
                    self.log_message("Normalization completed\n", self.preprocess_output)
                    
                    self.log_message("Step 2/5: Removing stopwords...", self.preprocess_output)
                    self.df_pelatihan['no_stopwords'] = self.df_pelatihan['normalized'].apply(
                        self.remove_stopwords)
                    self.log_message("Stopword removal completed\n", self.preprocess_output)
                    
                    self.log_message("Step 3/5: Tokenizing...", self.preprocess_output)
                    self.df_pelatihan['tokens'] = self.df_pelatihan['no_stopwords'].apply(
                        self.tokenize_text)
                    self.log_message("Tokenization completed\n", self.preprocess_output)
                    
                    self.log_message("Step 4/5: Stemming (per token) - this may take a while...", self.preprocess_output)
                    
                    # Progress bar for stemming
                    stemmed_tokens_list = []
                    for idx, tokens in enumerate(self.df_pelatihan['tokens']):
                        stemmed = self.stem_tokens(tokens)
                        stemmed_tokens_list.append(stemmed)
                        
                        if idx % 10 == 0 or idx == len(self.df_pelatihan) - 1:
                            self.update_progress(idx + 1, len(self.df_pelatihan), 
                                            "Stemming training data", self.preprocess_output)
                    
                    self.df_pelatihan['stemmed_tokens'] = stemmed_tokens_list
                    self.log_message("\nStemming (per token) completed\n", self.preprocess_output)
                    
                    self.log_message("Step 5/5: Finalizing...", self.preprocess_output)
                    self.df_pelatihan['stemmed'] = self.df_pelatihan['stemmed_tokens'].apply(
                        lambda x: ' '.join(x))
                    self.df_pelatihan['token_count'] = self.df_pelatihan['stemmed_tokens'].apply(len)
                    self.df_pelatihan['preprocessed_text'] = self.df_pelatihan['stemmed']
                    
                    # Save to cache
                    self.log_message("Saving to cache for future use...", self.preprocess_output)
                    cache_data = {
                        'text_features': self.df_pelatihan['text_features'],
                        'normalized': self.df_pelatihan['normalized'],
                        'no_stopwords': self.df_pelatihan['no_stopwords'],
                        'tokens': self.df_pelatihan['tokens'],
                        'stemmed_tokens': self.df_pelatihan['stemmed_tokens'],
                        'stemmed': self.df_pelatihan['stemmed'],
                        'token_count': self.df_pelatihan['token_count'],
                        'preprocessed_text': self.df_pelatihan['preprocessed_text']
                    }
                    if self.save_to_cache(cache_key, cache_data):
                        self.log_message("Cache saved successfully\n", self.preprocess_output)
                    
                    self.log_message(f"Processed {len(self.df_pelatihan)} training programs", 
                                self.preprocess_output)
                
                self.log_message(f"Average tokens: {self.df_pelatihan['token_count'].mean():.1f}\n", 
                            self.preprocess_output)
            
            # Process Job Data (similar structure)
            if self.df_lowongan is not None:
                self.log_message("\n" + "=" * 80, self.preprocess_output)
                self.log_message("PROCESSING JOB DATA (LOWONGAN)", self.preprocess_output)
                self.log_message("=" * 80 + "\n", self.preprocess_output)
                
                # Generate cache key
                cache_key = f"job_{self.get_cache_key(self.df_lowongan, 'lowongan')}"
                
                # Try to load from cache
                self.log_message("Checking cache...", self.preprocess_output)
                cached_data = self.load_from_cache(cache_key)
                
                if cached_data is not None:
                    self.log_message("Cache found! Loading preprocessed data...", self.preprocess_output)
                    # Restore cached columns
                    for col in ['text_features', 'normalized', 'no_stopwords', 'tokens', 
                               'stemmed_tokens', 'stemmed', 'token_count', 'preprocessed_text']:
                        if col in cached_data:
                            self.df_lowongan[col] = cached_data[col]
                    self.log_message(f"Loaded {len(self.df_lowongan)} job positions from cache\n", 
                                self.preprocess_output)
                else:
                    self.log_message("No cache found. Processing from scratch...\n", self.preprocess_output)
                    
                    # Combine text features
                    self.df_lowongan['text_features'] = (
                        self.df_lowongan['Deskripsi Pekerjaan'].fillna('')
                    )
                    
                    # Apply preprocessing
                    self.log_message("Step 1/5: Normalizing...", self.preprocess_output)
                    self.df_lowongan['normalized'] = self.df_lowongan['text_features'].apply(
                        self.normalize_text)
                    self.log_message("Normalization completed\n", self.preprocess_output)
                    
                    self.log_message("Step 2/5: Removing stopwords...", self.preprocess_output)
                    self.df_lowongan['no_stopwords'] = self.df_lowongan['normalized'].apply(
                        self.remove_stopwords)
                    self.log_message("Stopword removal completed\n", self.preprocess_output)
                    
                    self.log_message("Step 3/5: Tokenizing...", self.preprocess_output)
                    self.df_lowongan['tokens'] = self.df_lowongan['no_stopwords'].apply(
                        self.tokenize_text)
                    self.log_message("Tokenization completed\n", self.preprocess_output)
                    
                    self.log_message("Step 4/5: Stemming (per token) - this may take a while...", self.preprocess_output)
                    
                    # Progress bar for stemming
                    stemmed_tokens_list = []
                    for idx, tokens in enumerate(self.df_lowongan['tokens']):
                        stemmed = self.stem_tokens(tokens)
                        stemmed_tokens_list.append(stemmed)
                        
                        if idx % 10 == 0 or idx == len(self.df_lowongan) - 1:
                            self.update_progress(idx + 1, len(self.df_lowongan), 
                                            "Stemming job data", self.preprocess_output)
                    
                    self.df_lowongan['stemmed_tokens'] = stemmed_tokens_list
                    self.log_message("\nStemming (per token) completed\n", self.preprocess_output)
                    
                    self.log_message("Step 5/5: Finalizing...", self.preprocess_output)
                    self.df_lowongan['stemmed'] = self.df_lowongan['stemmed_tokens'].apply(
                        lambda x: ' '.join(x))
                    self.df_lowongan['token_count'] = self.df_lowongan['stemmed_tokens'].apply(len)
                    self.df_lowongan['preprocessed_text'] = self.df_lowongan['stemmed']
                    
                    # Save to cache
                    self.log_message("Saving to cache for future use...", self.preprocess_output)
                    cache_data = {
                        'text_features': self.df_lowongan['text_features'],
                        'normalized': self.df_lowongan['normalized'],
                        'no_stopwords': self.df_lowongan['no_stopwords'],
                        'tokens': self.df_lowongan['tokens'],
                        'stemmed_tokens': self.df_lowongan['stemmed_tokens'],
                        'stemmed': self.df_lowongan['stemmed'],
                        'token_count': self.df_lowongan['token_count'],
                        'preprocessed_text': self.df_lowongan['preprocessed_text']
                    }
                    if self.save_to_cache(cache_key, cache_data):
                        self.log_message("Cache saved successfully\n", self.preprocess_output)
                    
                    self.log_message(f"Processed {len(self.df_lowongan)} job positions", 
                                self.preprocess_output)
                
                self.log_message(f"Average tokens: {self.df_lowongan['token_count'].mean():.1f}\n", 
                            self.preprocess_output)
            
            self.log_message("\n" + "=" * 80, self.preprocess_output)
            self.log_message("ALL DATA PROCESSING COMPLETED!", self.preprocess_output)
            self.log_message("=" * 80, self.preprocess_output)
        
            if self.df_pelatihan is not None:
                self.log_message("\nSaving preprocessing samples...", self.preprocess_output)
                for idx in range(min(self.total_saved_sample, len(self.df_pelatihan))):
                    self.save_preprocessing_sample('training', idx, self.df_pelatihan.iloc[idx])
                    self.update_progress(idx + 1, self.total_saved_sample, 
                                    "Saving training samples", self.preprocess_output)

            if self.df_lowongan is not None:
                self.log_message("\n", self.preprocess_output)
                for idx in range(min(self.total_saved_sample, len(self.df_lowongan))):
                    self.save_preprocessing_sample('job', idx, self.df_lowongan.iloc[idx])
                    self.update_progress(idx + 1, self.total_saved_sample, 
                                    "Saving job samples", self.preprocess_output)

            self.log_message("\n✓ Preprocessing samples saved to database", self.preprocess_output)
        threading.Thread(target=process, daemon=True).start()

    def load_recommendation_options(self):
        """Load job options for recommendations"""
        success_job = False
        success_training = False
        
        if self.df_lowongan is not None:
            job_options = [f"{i}: {row['Nama Jabatan (Sumber Perusahaan)']}" 
                        for i, row in self.df_lowongan.iterrows()]
            self.rec_job_combo['values'] = job_options
            if job_options:
                self.rec_job_combo.current(0)
            success_job = True
        
        if self.df_pelatihan is not None:
            training_options = [f"{i}: {row['PROGRAM PELATIHAN']}" 
                        for i, row in self.df_pelatihan.iterrows()]
            self.rec_training_combo['values'] = training_options
            if training_options:
                self.rec_training_combo.current(0)
            success_training = True
        
        return success_job or success_training

    def show_all_trainings_recommendations(self):
        """Show recommendations for all training programs"""
        self.rec_output.delete(1.0, tk.END)
        
        if not hasattr(self, 'similarity_matrix') or self.similarity_matrix is None:
            messagebox.showwarning("Warning", 
                                "Please calculate similarity matrix first!\n"
                                "Go to 'TF-IDF & Cosine Similarity' tab and click "
                                "'Calculate All Documents'")
            return
        
        try:
            n_recommendations = int(self.rec_all_count_spinbox.get())
            threshold = float(self.rec_threshold_var.get())
        except:
            messagebox.showerror("Error", "Invalid parameters!")
            return
        
        # Display header
        self.log_message("=" * 170, self.rec_output)
        self.log_message("JOB POSITION RECOMMENDATIONS - ALL TRAINING PROGRAMS", self.rec_output)
        self.log_message("=" * 170, self.rec_output)
        self.log_message(f"\n📊 Configuration: Top N = {n_recommendations} per training | Threshold = {threshold:.2f} | Training = {len(self.df_pelatihan)} | Jobs = {len(self.df_lowongan)}", self.rec_output)
        
        # Store all recommendations for export
        self.all_recommendations = []
        
        # SQL-style table header with Company column
        self.log_message("\n" + "=" * 170, self.rec_output)
        self.log_message(
            f"┌{'─' * 8}┬{'─' * 50}┬{'─' * 40}┬{'─' * 35}┬{'─' * 6}┬{'─' * 13}┬{'─' * 12}┐",
            self.rec_output
        )
        self.log_message(
            f"│ {'Train':<6} │ {'Training Program':<48} │ {'Company':<38} │ {'Job Position':<33} │ {'Rank':<4} │ {'Similarity':<11} │ {'Match':<10} │",
            self.rec_output
        )
        self.log_message(
            f"│ {'Idx':<6} │ {'':<48} │ {'':<38} │ {'':<33} │ {'':<4} │ {'Score':<11} │ {'Level':<10} │",
            self.rec_output
        )
        self.log_message(
            f"├{'─' * 8}┼{'─' * 50}┼{'─' * 40}┼{'─' * 35}┼{'─' * 6}┼{'─' * 13}┼{'─' * 12}┤",
            self.rec_output
        )
        
        # Process each training program
        for training_idx in range(len(self.df_pelatihan)):
            training_name = self.df_pelatihan.iloc[training_idx]['PROGRAM PELATIHAN']
            similarities = self.similarity_matrix[training_idx, :]
            
            # Get top N that meet threshold
            top_indices = np.argsort(similarities)[::-1]
            filtered_indices = [idx for idx in top_indices 
                            if similarities[idx] >= threshold][:n_recommendations]
            
            if not filtered_indices:
                continue
            
            for rank, job_idx in enumerate(filtered_indices, 1):
                similarity = similarities[job_idx]
                
                # NEW: Get company name and handle NO_MATCH
                company_name = self.df_lowongan.iloc[job_idx].get('NAMA PERUSAHAAN', '-')
                is_no_match = similarity == 0
                
                if is_no_match:
                    job_name = ''  # Blank if NO_MATCH
                    match_level = "NO_MATCH"
                    match_emoji = "❌"
                else:
                    job_name = self.df_lowongan.iloc[job_idx]['Nama Jabatan (Sumber Perusahaan)']
                    # Determine match level
                    if similarity >= self.match_thresholds['excellent']:
                        match_level = "excellent"
                        match_emoji = "🟢"
                    elif similarity >= self.match_thresholds['very_good']:
                        match_level = "very_good"
                        match_emoji = "🟢"
                    elif similarity >= self.match_thresholds['good']:
                        match_level = "good"
                        match_emoji = "🟡"
                    elif similarity >= self.match_thresholds['fair']:
                        match_level = "fair"
                        match_emoji = "🟡"
                    else:
                        match_level = "weak"
                        match_emoji = "🔴"
                
                # Truncate names if too long
                training_display = training_name[:46] + ".." if len(training_name) > 48 else training_name
                company_display = company_name[:36] + ".." if len(company_name) > 38 else company_name
                job_display = job_name[:31] + ".." if len(job_name) > 33 else job_name
                
                self.log_message(
                    f"│ {training_idx:<6} │ {training_display:<48} │ {company_display:<38} │ {job_display:<33} │ {rank:<4} │ {similarity:<11.8f} │ {match_emoji} {match_level:<8} │",
                    self.rec_output
                )
                
                # Store for export
                self.all_recommendations.append({
                    'Training_Index': training_idx,
                    'Training_Program': training_name,
                    'Rank': rank,
                    'Job_Index': int(job_idx) if not is_no_match else None,
                    'Job_Name': job_name,
                    'Company_Name': company_name,
                    'Similarity_Score': similarity,
                    'Similarity_Percentage': similarity * 100,
                    'Status': 'NO_MATCH' if is_no_match else 'MATCH',
                    'Recommendation': 'Rekomendasi dibuka pelatihan baru' if is_no_match else ''
                })
        
        # Table footer
        self.log_message(
            f"└{'─' * 8}┴{'─' * 50}┴{'─' * 40}┴{'─' * 35}┴{'─' * 6}┴{'─' * 13}┴{'─' * 12}┘",
            self.rec_output
        )
                
        self.save_recommendations()
        self.complete_experiment()

        self.log_message("\n" + "=" * 170, self.rec_output)
        self.log_message("✅ ALL RECOMMENDATIONS COMPLETE", self.rec_output)
        self.log_message("=" * 170, self.rec_output)
        self.log_message(f"\nTotal: {len(self.all_recommendations)} recommendations | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                    self.rec_output)
        self.log_message(f"💡 Export available via buttons above", self.rec_output)

    def show_single_training_recommendations(self):
        """Show job recommendations for a single selected training program"""
        self.rec_output.delete(1.0, tk.END)
        
        # Check if data is ready
        if not hasattr(self, 'similarity_matrix') or self.similarity_matrix is None:
            messagebox.showwarning("Warning", 
                                "Please calculate similarity matrix first!\n"
                                "Go to 'TF-IDF & Cosine Similarity' tab and click "
                                "'Calculate All Documents'")
            return
        
        # Load options if not loaded
        if not self.rec_training_combo['values']:
            if not self.load_training_recommendation_options():
                messagebox.showerror("Error", "Training data not available!")
                return
        
        # Get selected training program
        try:
            training_idx = int(self.rec_training_combo.get().split(':')[0])
            n_recommendations = int(self.rec_training_count_spinbox.get())
            threshold = float(self.rec_training_threshold_var.get())
        except:
            messagebox.showerror("Error", "Please select a training program!")
            return
        
        training_name = self.df_pelatihan.iloc[training_idx]['PROGRAM PELATIHAN']
        training_desc = self.df_pelatihan.iloc[training_idx].get('Deskripsi Tujuan Program Pelatihan/Kompetensi', 'N/A')
                
        # Get similarities for this training program (row in matrix)
        similarities = self.similarity_matrix[training_idx, :]
        
        # Filter by threshold first, then get top N
        filtered_indices = [i for i in range(len(similarities)) if similarities[i] >= threshold]
        
        if not filtered_indices:
            self.log_message("=" * 150, self.rec_output)
            self.log_message("NO RECOMMENDATIONS FOUND", self.rec_output)
            self.log_message("=" * 150, self.rec_output)
            self.log_message(f"\n❌ No job positions found with similarity >= {threshold:.2f}", 
                            self.rec_output)
            self.log_message(f"\nTry lowering the minimum similarity threshold.", self.rec_output)
            return
        
        # Sort filtered indices by similarity and take top N
        filtered_indices.sort(key=lambda i: similarities[i], reverse=True)
        top_indices = filtered_indices[:n_recommendations]
        
        # Display header
        self.log_message("=" * 150, self.rec_output)
        self.log_message("JOB POSITION RECOMMENDATIONS - SINGLE TRAINING PROGRAM", self.rec_output)
        self.log_message("=" * 150, self.rec_output)
        
        self.log_message(f"\n🎯 TRAINING PROGRAM: {training_name}", self.rec_output)
        self.log_message(f"📄 Description: {training_desc[:120]}...", self.rec_output)
        
        self.log_message(f"\n⚙️ Settings: Top N = {n_recommendations} | Threshold = {threshold:.2f} | Found = {len(filtered_indices)} jobs", self.rec_output)
        
        # Display as SQL-style table
        self.log_message(f"\n\n📊 RECOMMENDATION RESULTS (Showing {len(top_indices)} of {len(filtered_indices)} matches):", self.rec_output)
        self.log_message("=" * 150, self.rec_output)
        
        # Table header (without Note column)
        self.log_message(
            f"┌{'─' * 8}┬{'─' * 50}┬{'─' * 50}┬{'─' * 6}┬{'─' * 13}┬{'─' * 10}┬{'─' * 12}┐",
            self.rec_output
        )
        self.log_message(
            f"│ {'Train':<6} │ {'Training Program':<48} │ {'Recommended Job Position':<48} │ {'Rank':<4} │ {'Similarity':<11} │ {'Score %':<8} │ {'Match':<10} │",
            self.rec_output
        )
        self.log_message(
            f"│ {'Idx':<6} │ {'':<48} │ {'':<48} │ {'':<4} │ {'Score':<11} │ {'':<8} │ {'Level':<10} │",
            self.rec_output
        )
        self.log_message(
            f"├{'─' * 8}┼{'─' * 50}┼{'─' * 50}┼{'─' * 6}┼{'─' * 13}┼{'─' * 10}┼{'─' * 12}┤",
            self.rec_output
        )
        
        # Store for export
        self.all_recommendations = []
        
        # Table rows
        for rank, job_idx in enumerate(top_indices, 1):
            job_name = self.df_lowongan.iloc[job_idx]['Nama Jabatan (Sumber Perusahaan)']
            company_name = self.df_lowongan.iloc[job_idx].get('NAMA PERUSAHAAN', '-')  
            similarity = similarities[job_idx]
            
            # Determine match level
            is_no_match = similarity == 0
            
            if is_no_match:
                job_name_display = ''  # Blank if NO_MATCH
                match_level = "NO_MATCH"
                match_emoji = "❌"
            else:
                job_name_display = job_name
                # Determine match level using self.match_thresholds
                if similarity >= self.match_thresholds['excellent']:
                    match_level = "excellent"
                    match_emoji = "🟢"
                elif similarity >= self.match_thresholds['very_good']:
                    match_level = "very_good"
                    match_emoji = "🟢"
                elif similarity >= self.match_thresholds['good']:
                    match_level = "good"
                    match_emoji = "🟡"
                elif similarity >= self.match_thresholds['fair']:
                    match_level = "fair"
                    match_emoji = "🟡"
                else:
                    match_level = "weak"
                    match_emoji = "🔴"
            
            # Truncate names if too long
            training_display = training_name[:46] + ".." if len(training_name) > 48 else training_name
            job_display = job_name_display[:46] + ".." if len(job_name_display) > 48 else job_name_display
            company_display = company_name[:26] + ".." if len(company_name) > 28 else company_name
            
            self.log_message(
                f"│ {training_idx:<6} │ {training_display:<48} │ {job_display:<48} │ {rank:<4} │ {similarity:<11.8f} │ {similarity*100:<8.2f} │ {match_emoji} {match_level:<8} │",
                self.rec_output
            )
            
            # Store for export
            self.all_recommendations.append({
                'Training_Index': training_idx,
                'Training_Program': training_name,
                'Rank': rank,
                'Job_Index': int(job_idx) if not is_no_match else None,
                'Job_Name': job_name if not is_no_match else '',
                'Company_Name': company_name,
                'Similarity_Score': similarity,
                'Similarity_Percentage': similarity * 100,
                'Status': 'NO_MATCH' if is_no_match else 'MATCH',
                'Recommendation': 'Rekomendasi dibuka pelatihan baru' if is_no_match else ''
            })
        
        # Table footer
        self.log_message(
            f"└{'─' * 8}┴{'─' * 50}┴{'─' * 50}┴{'─' * 6}┴{'─' * 13}┴{'─' * 10}┴{'─' * 12}┘",
            self.rec_output
        )
        
        # Save recommendations
        self.save_recommendations()
        
        # Summary
        self.log_message("\n" + "=" * 150, self.rec_output)
        self.log_message("✅ RECOMMENDATION COMPLETE", self.rec_output)
        self.log_message("=" * 150, self.rec_output)
        self.log_message(f"\n💡 Results: {len(top_indices)} recommendations displayed | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                        self.rec_output)

    def load_training_recommendation_options(self):
        """Load training program options for recommendations"""
        if self.df_pelatihan is None:
            return False
        
        training_options = [f"{i}: {row['PROGRAM PELATIHAN']}" 
                    for i, row in self.df_pelatihan.iterrows()]
        self.rec_training_combo['values'] = training_options
        if training_options:
            self.rec_training_combo.current(0)
        return True

    def show_single_job_recommendations(self):
        """Show recommendations for a single selected job"""
        self.rec_output.delete(1.0, tk.END)
        
        # Check if data is ready
        if not hasattr(self, 'similarity_matrix') or self.similarity_matrix is None:
            messagebox.showwarning("Warning", 
                                "Please calculate similarity matrix first!\n"
                                "Go to 'TF-IDF & Cosine Similarity' tab and click "
                                "'Calculate All Documents'")
            return
        
        # Load options if not loaded
        if not self.rec_job_combo['values']:
            if not self.load_recommendation_options():
                messagebox.showerror("Error", "Job data not available!")
                return
        
        # Get selected job
        try:
            job_idx = int(self.rec_job_combo.get().split(':')[0])
            n_recommendations = int(self.rec_count_spinbox.get())
            threshold = float(self.rec_single_threshold_var.get())
        except:
            messagebox.showerror("Error", "Please select a job position!")
            return
        
        job_name = self.df_lowongan.iloc[job_idx]['Nama Jabatan (Sumber Perusahaan)']
        company_name = self.df_lowongan.iloc[job_idx].get('NAMA PERUSAHAAN', '-')  
        job_desc = self.df_lowongan.iloc[job_idx].get('Deskripsi Pekerjaan', 'N/A')
                
        # Get similarities for this job
        similarities = self.similarity_matrix[:, job_idx]
        
        # Filter by threshold first, then get top N
        filtered_indices = [i for i in range(len(similarities)) if similarities[i] >= threshold]
        
        if not filtered_indices:
            self.log_message("=" * 150, self.rec_output)
            self.log_message("NO RECOMMENDATIONS FOUND", self.rec_output)
            self.log_message("=" * 150, self.rec_output)
            self.log_message(f"\n❌ No training programs found with similarity >= {threshold:.2f}", 
                            self.rec_output)
            self.log_message(f"\nTry lowering the minimum similarity threshold.", self.rec_output)
            return
        
        # Sort filtered indices by similarity and take top N
        filtered_indices.sort(key=lambda i: similarities[i], reverse=True)
        top_indices = filtered_indices[:n_recommendations]
        
        # Display header
        self.log_message("=" * 150, self.rec_output)
        self.log_message("TRAINING PROGRAM RECOMMENDATIONS - SINGLE JOB", self.rec_output)
        self.log_message("=" * 150, self.rec_output)
        
        self.log_message(f"\n🎯 JOB POSITION: {job_name}", self.rec_output)
        self.log_message(f"🏢 COMPANY: {company_name}", self.rec_output)  
        self.log_message(f"📄 Description: {job_desc[:120]}...", self.rec_output)
        
        self.log_message(f"\n⚙️  Settings: Top N = {n_recommendations} | Threshold = {threshold:.2f} | Found = {len(filtered_indices)} programs", self.rec_output)
        
        # Display as SQL-style table
        self.log_message(f"\n\n📊 RECOMMENDATION RESULTS (Showing {len(top_indices)} of {len(filtered_indices)} matches):", self.rec_output)
        self.log_message("=" * 150, self.rec_output)
        
        # Table header (without Note column)
        self.log_message(
            f"┌{'─' * 6}┬{'─' * 45}┬{'─' * 55}┬{'─' * 6}┬{'─' * 13}┬{'─' * 10}┬{'─' * 12}┐",
            self.rec_output
        )
        self.log_message(
            f"│ {'Job':<4} │ {'Job Name':<43} │ {'Training Program':<53} │ {'Rank':<4} │ {'Similarity':<11} │ {'Score %':<8} │ {'Match':<10} │",
            self.rec_output
        )
        self.log_message(
            f"│ {'Idx':<4} │ {'':<43} │ {'':<53} │ {'':<4} │ {'Score':<11} │ {'':<8} │ {'Level':<10} │",
            self.rec_output
        )
        self.log_message(
            f"├{'─' * 6}┼{'─' * 45}┼{'─' * 55}┼{'─' * 6}┼{'─' * 13}┼{'─' * 10}┼{'─' * 12}┤",
            self.rec_output
        )
        
        # Store for export
        self.all_recommendations = []
        
        # Table rows
        for rank, pel_idx in enumerate(top_indices, 1):
            program_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
            similarity = similarities[pel_idx]
            
            # Determine match level
            is_no_match = similarity == 0
            
            if is_no_match:
                program_name_display = ''  # Blank if NO_MATCH
                match_level = "NO_MATCH"
                match_emoji = "❌"
            else:
                program_name_display = program_name
                # Determine match level using fixed thresholds (or use self.match_thresholds if available)
                if similarity >= 0.80:
                    match_level = "excellent"
                    match_emoji = "🟢"
                elif similarity >= 0.65:
                    match_level = "very_good"
                    match_emoji = "🟢"
                elif similarity >= 0.50:
                    match_level = "good"
                    match_emoji = "🟡"
                elif similarity >= 0.35:
                    match_level = "fair"
                    match_emoji = "🟡"
                else:
                    match_level = "weak"
                    match_emoji = "🔴"
            
            # Truncate names if too long
            job_display = job_name[:41] + ".." if len(job_name) > 43 else job_name
            program_display = program_name_display[:51] + ".." if len(program_name_display) > 53 else program_name_display
            
            self.log_message(
                f"│ {job_idx:<4} │ {job_display:<43} │ {program_display:<53} │ {rank:<4} │ {similarity:<11.8f} │ {similarity*100:<8.2f} │ {match_emoji} {match_level:<8} │",
                self.rec_output
            )
            
            # Store for export
            self.all_recommendations.append({
                'Job_Index': job_idx,
                'Job_Name': job_name,
                'Company_Name': company_name,
                'Rank': rank,
                'Training_Index': int(pel_idx) if not is_no_match else None,
                'Training_Program': program_name if not is_no_match else '',
                'Similarity_Score': similarity,
                'Similarity_Percentage': similarity * 100,
                'Status': 'NO_MATCH' if is_no_match else 'MATCH',
                'Recommendation': 'Rekomendasi dibuka pelatihan baru' if is_no_match else ''
            })
        
        # Table footer
        self.log_message(
            f"└{'─' * 6}┴{'─' * 45}┴{'─' * 55}┴{'─' * 6}┴{'─' * 13}┴{'─' * 10}┴{'─' * 12}┘",
            self.rec_output
        )
        
        # Save recommendations
        self.save_recommendations()
        
        # Summary
        self.log_message("\n" + "=" * 150, self.rec_output)
        self.log_message("✅ RECOMMENDATION COMPLETE", self.rec_output)
        self.log_message("=" * 150, self.rec_output)
        self.log_message(f"\n💡 Results: {len(top_indices)} recommendations displayed | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                        self.rec_output)

    def show_all_jobs_recommendations(self):
        """Show recommendations for all jobs"""
        self.rec_output.delete(1.0, tk.END)
        
        if not hasattr(self, 'similarity_matrix') or self.similarity_matrix is None:
            messagebox.showwarning("Warning", 
                                "Please calculate similarity matrix first!\n"
                                "Go to 'TF-IDF & Cosine Similarity' tab and click "
                                "'Calculate All Documents'")
            return
        
        try:
            n_recommendations = int(self.rec_all_count_spinbox.get())
            threshold = float(self.rec_threshold_var.get())
        except:
            messagebox.showerror("Error", "Invalid parameters!")
            return
        
        # Display header
        self.log_message("=" * 170, self.rec_output)
        self.log_message("TRAINING PROGRAM RECOMMENDATIONS - ALL JOBS", self.rec_output)
        self.log_message("=" * 170, self.rec_output)
        self.log_message(f"\n📊 Configuration: Top N = {n_recommendations} per job | Threshold = {threshold:.2f} | Jobs = {len(self.df_lowongan)} | Programs = {len(self.df_pelatihan)}", self.rec_output)
        
        # Store all recommendations for export
        self.all_recommendations = []
        
        # SQL-style table header with Company column
        self.log_message("\n" + "=" * 170, self.rec_output)
        self.log_message(
            f"┌{'─' * 6}┬{'─' * 40}┬{'─' * 35}┬{'─' * 50}┬{'─' * 6}┬{'─' * 13}┬{'─' * 12}┐",
            self.rec_output
        )
        self.log_message(
            f"│ {'Job':<4} │ {'Company':<38} │ {'Job Name':<33} │ {'Training Program':<48} │ {'Rank':<4} │ {'Similarity':<11} │ {'Match':<10} │",
            self.rec_output
        )
        self.log_message(
            f"│ {'Idx':<4} │ {'':<38} │ {'':<33} │ {'':<48} │ {'':<4} │ {'Score':<11} │ {'Level':<10} │",
            self.rec_output
        )
        self.log_message(
            f"├{'─' * 6}┼{'─' * 40}┼{'─' * 35}┼{'─' * 50}┼{'─' * 6}┼{'─' * 13}┼{'─' * 12}┤",
            self.rec_output
        )
        
        # Process each job
        for job_idx in range(len(self.df_lowongan)):
            job_name = self.df_lowongan.iloc[job_idx]['Nama Jabatan (Sumber Perusahaan)']
            company_name = self.df_lowongan.iloc[job_idx].get('NAMA PERUSAHAAN', '-')
            similarities = self.similarity_matrix[:, job_idx]
            
            # Get top N that meet threshold
            top_indices = np.argsort(similarities)[::-1]
            filtered_indices = [idx for idx in top_indices 
                            if similarities[idx] >= threshold][:n_recommendations]
            
            if not filtered_indices:
                continue
            
            for rank, pel_idx in enumerate(filtered_indices, 1):
                similarity = similarities[pel_idx]
                
                # NEW: Handle NO_MATCH
                is_no_match = similarity == 0
                
                if is_no_match:
                    program_name = ''  # Blank if NO_MATCH
                    match_level = "NO_MATCH"
                    match_emoji = "❌"
                else:
                    program_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
                    # Determine match level
                    if similarity >= self.match_thresholds['excellent']:
                        match_level = "excellent"
                        match_emoji = "🟢"
                    elif similarity >= self.match_thresholds['very_good']:
                        match_level = "very_good"
                        match_emoji = "🟢"
                    elif similarity >= self.match_thresholds['good']:
                        match_level = "good"
                        match_emoji = "🟡"
                    elif similarity >= self.match_thresholds['fair']:
                        match_level = "fair"
                        match_emoji = "🟡"
                    else:
                        match_level = "weak"
                        match_emoji = "🔴"
                
                # Truncate names if too long
                company_display = company_name[:36] + ".." if len(company_name) > 38 else company_name
                job_display = job_name[:31] + ".." if len(job_name) > 33 else job_name
                program_display = program_name[:46] + ".." if len(program_name) > 48 else program_name
                
                self.log_message(
                    f"│ {job_idx:<4} │ {company_display:<38} │ {job_display:<33} │ {program_display:<48} │ {rank:<4} │ {similarity:<11.8f} │ {match_emoji} {match_level:<8} │",
                    self.rec_output
                )
                
                # Store for export
                self.all_recommendations.append({
                    'Job_Index': job_idx,
                    'Job_Name': job_name,
                    'Company_Name': company_name,
                    'Rank': rank,
                    'Training_Index': int(pel_idx) if not is_no_match else None,
                    'Training_Program': program_name,
                    'Similarity_Score': similarity,
                    'Similarity_Percentage': similarity * 100,
                    'Status': 'NO_MATCH' if is_no_match else 'MATCH',
                    'Recommendation': 'Rekomendasi dibuka pelatihan baru' if is_no_match else ''
                })
        
        # Table footer
        self.log_message(
            f"└{'─' * 6}┴{'─' * 40}┴{'─' * 35}┴{'─' * 50}┴{'─' * 6}┴{'─' * 13}┴{'─' * 12}┘",
            self.rec_output
        )
                
        self.save_recommendations()
        self.complete_experiment()

        self.log_message("\n" + "=" * 170, self.rec_output)
        self.log_message("✅ ALL RECOMMENDATIONS COMPLETE", self.rec_output)
        self.log_message("=" * 170, self.rec_output)
        self.log_message(f"\nTotal: {len(self.all_recommendations)} recommendations | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                    self.rec_output)
        self.log_message(f"💡 Export available via buttons above", self.rec_output)

    def export_recommendations_excel(self):
        """Export all recommendations to Excel"""
        if not hasattr(self, 'all_recommendations') or not self.all_recommendations:
            messagebox.showwarning("Warning", 
                                "No recommendations to export!\n"
                                "Please generate recommendations for all jobs first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="job_training_recommendations.xlsx"
        )
        
        if filename:
            try:
                df_export = pd.DataFrame(self.all_recommendations)
                df_export.to_excel(filename, index=False, sheet_name='Recommendations')
                messagebox.showinfo("Success", 
                                f"Recommendations exported successfully!\n"
                                f"File: {filename}\n"
                                f"Total records: {len(self.all_recommendations)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export:\n{str(e)}")

    def export_recommendations_csv(self):
        """Export all recommendations to CSV"""
        if not hasattr(self, 'all_recommendations') or not self.all_recommendations:
            messagebox.showwarning("Warning", 
                                "No recommendations to export!\n"
                                "Please generate recommendations for all jobs first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="job_training_recommendations.csv"
        )
        
        if filename:
            try:
                df_export = pd.DataFrame(self.all_recommendations)
                df_export.to_csv(filename, index=False, encoding='utf-8-sig')
                messagebox.showinfo("Success", 
                                f"Recommendations exported successfully!\n"
                                f"File: {filename}\n"
                                f"Total records: {len(self.all_recommendations)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export:\n{str(e)}")

    def generate_statistics(self):
        """Generate statistics and visualizations"""
        self.stats_text.delete(1.0, tk.END)
        
        if self.df_pelatihan is None and self.df_lowongan is None:
            self.log_message("Please load and process data first!", self.stats_text)
            return
        
        # Clear previous visualization
        for widget in self.viz_canvas_frame.winfo_children():
            widget.destroy()
        
        # Statistics
        self.log_message("=" * 80 + "\n", self.stats_text)
        self.log_message("DATASET STATISTICS\n", self.stats_text)
        self.log_message("=" * 80 + "\n", self.stats_text)
        
        if self.df_pelatihan is not None and 'token_count' in self.df_pelatihan.columns:
            self.log_message("\n📊 TRAINING PROGRAMS (PELATIHAN):", self.stats_text)
            self.log_message(f"  Total records: {len(self.df_pelatihan)}", self.stats_text)
            self.log_message(f"  Avg tokens: {self.df_pelatihan['token_count'].mean():.2f}", 
                           self.stats_text)
            self.log_message(f"  Min tokens: {self.df_pelatihan['token_count'].min()}", 
                           self.stats_text)
            self.log_message(f"  Max tokens: {self.df_pelatihan['token_count'].max()}", 
                           self.stats_text)
            self.log_message(f"  Median tokens: {self.df_pelatihan['token_count'].median():.2f}\n", 
                           self.stats_text)
        
        if self.df_lowongan is not None and 'token_count' in self.df_lowongan.columns:
            self.log_message("\n📊 JOB POSITIONS (LOWONGAN):", self.stats_text)
            self.log_message(f"  Total records: {len(self.df_lowongan)}", self.stats_text)
            self.log_message(f"  Avg tokens: {self.df_lowongan['token_count'].mean():.2f}", 
                           self.stats_text)
            self.log_message(f"  Min tokens: {self.df_lowongan['token_count'].min()}", 
                           self.stats_text)
            self.log_message(f"  Max tokens: {self.df_lowongan['token_count'].max()}", 
                           self.stats_text)
            self.log_message(f"  Median tokens: {self.df_lowongan['token_count'].median():.2f}\n", 
                           self.stats_text)
        
        # Create visualization
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        
        if self.df_pelatihan is not None and 'token_count' in self.df_pelatihan.columns:
            axes[0].hist(self.df_pelatihan['token_count'], bins=20, 
                        color='skyblue', edgecolor='black', alpha=0.7)
            axes[0].set_title('Token Distribution - Training Programs', fontsize=12, fontweight='bold')
            axes[0].set_xlabel('Number of Tokens')
            axes[0].set_ylabel('Frequency')
            axes[0].grid(axis='y', alpha=0.3)
        
        if self.df_lowongan is not None and 'token_count' in self.df_lowongan.columns:
            axes[1].hist(self.df_lowongan['token_count'], bins=20, 
                        color='lightcoral', edgecolor='black', alpha=0.7)
            axes[1].set_title('Token Distribution - Job Positions', fontsize=12, fontweight='bold')
            axes[1].set_xlabel('Number of Tokens')
            axes[1].set_ylabel('Frequency')
            axes[1].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.viz_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_experiment(self, name, description=""):
        """Create new experiment in database"""
        if not self.db_connection or not self.db_connection.is_connected():
            return None

        try:
            cursor = self.db_connection.cursor()
            training_count = len(self.df_pelatihan) if self.df_pelatihan is not None else 0
            job_count = len(self.df_lowongan) if self.df_lowongan is not None else 0

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            experiment_name = f"{name} ({timestamp})"

            query = """
            INSERT INTO experiments 
            (experiment_name, description, dataset_training_count, dataset_job_count)
            VALUES (%s, %s, %s, %s)
            """

            cursor.execute(query, (experiment_name, description, training_count, job_count))
            self.db_connection.commit()

            self.current_experiment_id = cursor.lastrowid
            cursor.close()

            print(f"✓ Experiment created: {experiment_name}")
            return self.current_experiment_id

        except Error as e:
            print(f"✗ Error creating experiment: {e}")
            return None

    def save_preprocessing_sample(self, dataset_type, record_index, row):
        """Save preprocessing sample to database"""
        if not self.current_experiment_id or not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            record_name = row['PROGRAM PELATIHAN'] if dataset_type == 'training' else row['Nama Jabatan (Sumber Perusahaan)']
            
            query = """
            INSERT INTO preprocessing_samples 
            (experiment_id, dataset_type, record_index, record_name, 
            original_text, normalized_text, stopwords_removed, 
            tokenized, stemmed_text, token_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            token_count = int(row.get('token_count', 0)) if pd.notna(row.get('token_count', 0)) else 0
            
            values = (
                self.current_experiment_id,
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
            self.db_connection.commit()
            cursor.close()
        except Error as e:
            print(f"✗ Error saving preprocessing sample: {e}")

    def save_tfidf_calculation(self, pel_idx, low_idx):
        """Save TF-IDF calculation to database"""
        if not self.current_experiment_id or not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            training_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
            job_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan (Sumber Perusahaan)']
            
            query = """
            INSERT INTO tfidf_calculations 
            (experiment_id, training_index, training_name, job_index, job_name,
            unique_terms_count, terms_json, tf_training_json, tf_job_json,
            idf_json, tfidf_training_json, tfidf_job_json, cosine_similarity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                self.current_experiment_id,
                int(pel_idx), 
                training_name,
                int(low_idx),
                job_name,
                int(len(self.current_all_terms)),
                json.dumps(self.current_all_terms),
                json.dumps(self.tf_d1),
                json.dumps(self.tf_d2),
                json.dumps(self.idf_dict),
                json.dumps(self.tfidf_d1),
                json.dumps(self.tfidf_d2),
                float(self.current_similarity)
            )         

            cursor.execute(query, values)
            self.db_connection.commit()
            cursor.close()
            print("✓ TF-IDF calculation saved to database")
        except Error as e:
            print(f"✗ Error saving TF-IDF: {e}")

    def save_similarity_matrix(self):
        """Save full similarity matrix to database"""
        if not self.current_experiment_id or not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            query = """
            INSERT INTO similarity_matrix 
            (experiment_id, training_index, training_name, job_index, job_name, similarity_score)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            batch_data = []
            for job_idx in range(len(self.df_lowongan)):
                job_name = self.df_lowongan.iloc[job_idx]['Nama Jabatan (Sumber Perusahaan)']
                for pel_idx in range(len(self.df_pelatihan)):
                    training_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
                    similarity = float(self.similarity_matrix[pel_idx, job_idx])
                    
                batch_data.append((
                    self.current_experiment_id,
                    int(pel_idx),
                    training_name,
                    int(job_idx),
                    job_name,
                    float(similarity)
                ))
            
            cursor.executemany(query, batch_data)
            self.db_connection.commit()
            cursor.close()
            print(f"✓ Saved {len(batch_data)} similarity scores to database")
        except Error as e:
            print(f"✗ Error saving similarity matrix: {e}")

    def save_recommendations(self):
        """Save recommendations to database"""
        if not self.current_experiment_id or not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor()
            
            query = """
            INSERT INTO recommendations 
            (experiment_id, job_index, job_name, training_index, training_name,
            rank_position, similarity_score, similarity_percentage, match_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch_data = []
            for rec in self.all_recommendations:
                # Determine match level
                similarity = rec['Similarity_Score']
                if similarity >= self.match_thresholds['excellent']:
                    match_level = 'excellent'
                elif similarity >= self.match_thresholds['very_good']:
                    match_level = 'very_good'
                elif similarity >= self.match_thresholds['good']:
                    match_level = 'good'
                elif similarity >= self.match_thresholds['fair']:
                    match_level = 'fair'
                else:
                    match_level = 'weak'
                
                batch_data.append((
                    self.current_experiment_id,
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
            self.db_connection.commit()
            cursor.close()
            print(f"✓ Saved {len(batch_data)} recommendations to database")
        except Error as e:
            print(f"✗ Error saving recommendations: {e}")

    def complete_experiment(self):
        """Mark experiment as completed"""
        if not self.current_experiment_id or not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor()
            cursor.callproc('sp_complete_experiment', [self.current_experiment_id])
            self.db_connection.commit()
            cursor.close()
            print("✓ Experiment marked as completed")
        except Error as e:
            print(f"✗ Error completing experiment: {e}")

    # ============================================================================
    # JACCARD SIMILARITY FUNCTIONS
    # ============================================================================

    def calculate_jaccard_similarity(self, tokens1, tokens2):
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

    def calculate_jaccard_matrix(self):
        """
        Calculate Jaccard similarity matrix for all document pairs
        
        Returns:
            numpy array of shape (n_training, n_jobs)
        """
        if self.df_pelatihan is None or self.df_lowongan is None:
            return None
        
        if 'stemmed_tokens' not in self.df_pelatihan.columns:
            return None
        
        n_training = len(self.df_pelatihan)
        n_jobs = len(self.df_lowongan)
        
        jaccard_matrix = np.zeros((n_training, n_jobs))
        
        for i in range(n_training):
            tokens1 = self.df_pelatihan.iloc[i]['stemmed_tokens']
            for j in range(n_jobs):
                tokens2 = self.df_lowongan.iloc[j]['stemmed_tokens']
                result = self.calculate_jaccard_similarity(tokens1, tokens2)
                jaccard_matrix[i, j] = result['jaccard_similarity']
        
        return jaccard_matrix

    # ============================================================================
    # UI CREATION - Add to create_widgets() tabs_config
    # ============================================================================

    def create_jaccard_tab(self, parent):
        """Create Jaccard Similarity tab"""
        # Main frame with left-right layout
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls
        left_frame = ttk.Frame(main_frame, width=350)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        left_frame.pack_propagate(False)
        
        title = ttk.Label(left_frame, text="Jaccard Similarity", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Document selection
        doc_frame = ttk.LabelFrame(left_frame, text="Select Documents", padding="10")
        doc_frame.pack(fill='x', pady=10)
        
        ttk.Button(doc_frame, text="Load Document Options", 
                command=self.load_jaccard_document_options, width=30).pack(pady=5)

        ttk.Label(doc_frame, text="Training Program:").pack(anchor='w', pady=2)
        self.jaccard_pelatihan_combo = ttk.Combobox(doc_frame, state='readonly', width=35)
        self.jaccard_pelatihan_combo.pack(fill='x', pady=5)
        
        ttk.Label(doc_frame, text="Job Position:").pack(anchor='w', pady=2)
        self.jaccard_lowongan_combo = ttk.Combobox(doc_frame, state='readonly', width=35)
        self.jaccard_lowongan_combo.pack(fill='x', pady=5)
        
        # Step buttons
        step_frame = ttk.LabelFrame(left_frame, text="Jaccard Steps", padding="10")
        step_frame.pack(fill='x', pady=10)
        
        steps = [
            ("1. Show Tokens & Sets", lambda: self.show_jaccard_step(1)),
            ("2. Calculate Intersection", lambda: self.show_jaccard_step(2)),
            ("3. Calculate Union", lambda: self.show_jaccard_step(3)),
            ("4. Calculate Jaccard", lambda: self.show_jaccard_step(4)),
            ("5. Show All Steps", lambda: self.show_jaccard_step(5)),
        ]
        
        for step_name, command in steps:
            ttk.Button(step_frame, text=step_name, command=command, 
                    width=30).pack(pady=2)
        
        ttk.Separator(step_frame, orient='horizontal').pack(fill='x', pady=8)
        
        ttk.Button(step_frame, text="▶ Run All Steps", 
                command=self.run_all_jaccard_steps,
                style='Accent.TButton', width=30).pack(pady=5)
        
        # Calculate all button
        ttk.Separator(left_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(left_frame, text="Calculate All Documents\n(Full Jaccard Matrix)", 
                command=self.calculate_all_jaccard_documents,
                style='Accent.TButton', width=30).pack(pady=10)
        
        # Info
        info_frame = ttk.LabelFrame(left_frame, text="ℹ️ About Jaccard", padding="10")
        info_frame.pack(fill='x', pady=10)
        
        info_text = tk.Text(info_frame, height=6, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill='x')
        info_text.insert(1.0, 
            "Jaccard Similarity Formula:\n"
            "J(A,B) = |A ∩ B| / |A ∪ B|\n\n"
            "Where:\n"
            "• A ∩ B = Intersection (common terms)\n"
            "• A ∪ B = Union (all unique terms)"
        )
        info_text.config(state='disabled')
        
        # Right panel - Output
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Jaccard Calculation Output", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.jaccard_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                    font=('Consolas', 9))
        self.jaccard_output.pack(fill='both', expand=True)

    def create_comparison_tab(self, parent):
        """Create Cosine vs Jaccard Comparison tab"""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls
        left_frame = ttk.Frame(main_frame, width=350)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        left_frame.pack_propagate(False)
        
        title = ttk.Label(left_frame, text="Similarity Comparison", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Configuration
        config_frame = ttk.LabelFrame(left_frame, text="Configuration", padding="10")
        config_frame.pack(fill='x', pady=10)
        
        ttk.Label(config_frame, text="Comparison Mode:").pack(anchor='w', pady=3)
        self.comparison_mode_var = tk.StringVar(value="all")
        ttk.Radiobutton(config_frame, text="All Pairs (Non-Zero)", 
                    variable=self.comparison_mode_var, value="all",
                    command=self.toggle_comparison_mode).pack(anchor='w', pady=2)
        ttk.Radiobutton(config_frame, text="Single Pair", 
                    variable=self.comparison_mode_var, value="single",
                    command=self.toggle_comparison_mode).pack(anchor='w', pady=2)
        
        # Single Pair Selection (initially hidden)
        self.single_pair_frame = ttk.LabelFrame(left_frame, text="Single Pair Selection", padding="10")
        self.single_pair_frame.pack(fill='x', pady=10)
        
        ttk.Label(self.single_pair_frame, text="Training Program:").pack(anchor='w', pady=2)
        self.comparison_training_combo = ttk.Combobox(self.single_pair_frame, state='readonly', width=35)
        self.comparison_training_combo.pack(fill='x', pady=5)
        
        ttk.Label(self.single_pair_frame, text="Job Position:").pack(anchor='w', pady=2)
        self.comparison_job_combo = ttk.Combobox(self.single_pair_frame, state='readonly', width=35)
        self.comparison_job_combo.pack(fill='x', pady=5)
        
        # Initially hide single pair frame
        self.single_pair_frame.pack_forget()
        
        ttk.Label(config_frame, text="Minimum Threshold:").pack(anchor='w', pady=3)
        threshold_frame = ttk.Frame(config_frame)
        threshold_frame.pack(fill='x', pady=5)
        
        self.comparison_threshold_var = tk.DoubleVar(value=0.01)
        self.comparison_threshold_scale = ttk.Scale(threshold_frame, from_=0.0, to=1.0, 
                                            variable=self.comparison_threshold_var, 
                                            orient='horizontal')
        self.comparison_threshold_scale.pack(side='left', fill='x', expand=True)
        self.comparison_threshold_label = ttk.Label(threshold_frame, text="0.01", width=6)
        self.comparison_threshold_label.pack(side='right', padx=5)
        
        def update_threshold_label(*args):
            self.comparison_threshold_label.config(text=f"{self.comparison_threshold_var.get():.2f}")
        self.comparison_threshold_var.trace('w', update_threshold_label)
        
        # Buttons
        button_frame = ttk.LabelFrame(left_frame, text="Actions", padding="10")
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="📊 Generate Comparison", 
                command=self.generate_comparison,
                style='Accent.TButton', width=30).pack(pady=5)
        
        ttk.Button(button_frame, text="💾 Export to Excel", 
                command=self.export_comparison,
                width=30).pack(pady=5)
        
        # Right panel - Output
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Comparison Results", 
                font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.comparison_output = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                        font=('Consolas', 9))
        self.comparison_output.pack(fill='both', expand=True)

    # ============================================================================
    # JACCARD STEP FUNCTIONS
    # ============================================================================

    def load_jaccard_document_options(self):
        """Load available documents for Jaccard calculation"""
        if self.df_pelatihan is None or self.df_lowongan is None:
            messagebox.showwarning("Warning", "Please load and preprocess both datasets first!")
            return
        
        if 'preprocessed_text' not in self.df_pelatihan.columns:
            messagebox.showwarning("Warning", "Please preprocess the data first!")
            return
        
        # Load pelatihan options
        pelatihan_options = [f"{i}: {row['PROGRAM PELATIHAN']}" 
                            for i, row in self.df_pelatihan.iterrows()]
        self.jaccard_pelatihan_combo['values'] = pelatihan_options
        if pelatihan_options:
            self.jaccard_pelatihan_combo.current(0)
        
        # Load lowongan options
        lowongan_options = [f"{i}: {row['Nama Jabatan (Sumber Perusahaan)']}" 
                        for i, row in self.df_lowongan.iterrows()]
        self.jaccard_lowongan_combo['values'] = lowongan_options
        if lowongan_options:
            self.jaccard_lowongan_combo.current(0)
        
        messagebox.showinfo("Success", "Document options loaded!")

    def show_jaccard_step(self, step):
        """Show specific Jaccard calculation step"""
        self.jaccard_output.delete(1.0, tk.END)
        
        try:
            pel_idx = int(self.jaccard_pelatihan_combo.get().split(':')[0])
            low_idx = int(self.jaccard_lowongan_combo.get().split(':')[0])
        except:
            messagebox.showerror("Error", "Please select both documents first!")
            return
        
        # Get documents
        doc1 = self.df_pelatihan.iloc[pel_idx]
        doc2 = self.df_lowongan.iloc[low_idx]
        
        training_name = doc1['PROGRAM PELATIHAN']
        job_name = doc2['Nama Jabatan (Sumber Perusahaan)']
        
        tokens1 = doc1['stemmed_tokens']
        tokens2 = doc2['stemmed_tokens']
        
        # Calculate Jaccard
        jaccard_result = self.calculate_jaccard_similarity(tokens1, tokens2)
        
        self.log_message("=" * 120, self.jaccard_output)
        self.log_message(f"JACCARD SIMILARITY - STEP {step}", self.jaccard_output)
        self.log_message("=" * 120, self.jaccard_output)
        self.log_message(f"\n📄 Document 1: {training_name}", self.jaccard_output)
        self.log_message(f"📄 Document 2: {job_name}\n", self.jaccard_output)
        
        if step == 1:  # Show Tokens & Sets
            self.log_message("STEP 1: TOKENS & SETS\n", self.jaccard_output)
            self.log_message(f"Tokens D1 ({len(tokens1)}): {tokens1}\n", self.jaccard_output)
            self.log_message(f"Unique Set D1 ({len(jaccard_result['set1'])}): {jaccard_result['set1']}\n", self.jaccard_output)
            self.log_message(f"Tokens D2 ({len(tokens2)}): {tokens2}\n", self.jaccard_output)
            self.log_message(f"Unique Set D2 ({len(jaccard_result['set2'])}): {jaccard_result['set2']}\n", self.jaccard_output)
            
        elif step == 2:  # Intersection
            self.log_message("STEP 2: INTERSECTION (A ∩ B)\n", self.jaccard_output)
            self.log_message(f"Set A: {jaccard_result['set1']}\n", self.jaccard_output)
            self.log_message(f"Set B: {jaccard_result['set2']}\n", self.jaccard_output)
            self.log_message(f"Intersection: {jaccard_result['intersection']}", self.jaccard_output)
            self.log_message(f"Count: {jaccard_result['intersection_count']}\n", self.jaccard_output)
            
        elif step == 3:  # Union
            self.log_message("STEP 3: UNION (A ∪ B)\n", self.jaccard_output)
            self.log_message(f"Set A: {jaccard_result['set1']}\n", self.jaccard_output)
            self.log_message(f"Set B: {jaccard_result['set2']}\n", self.jaccard_output)
            self.log_message(f"Union: {jaccard_result['union']}", self.jaccard_output)
            self.log_message(f"Count: {jaccard_result['union_count']}\n", self.jaccard_output)
            
        elif step == 4:  # Calculate Jaccard
            self.log_message("STEP 4: JACCARD SIMILARITY\n", self.jaccard_output)
            self.log_message("Formula: J(A,B) = |A ∩ B| / |A ∪ B|\n", self.jaccard_output)
            self.log_message(f"Intersection Size: {jaccard_result['intersection_count']}", self.jaccard_output)
            self.log_message(f"Union Size: {jaccard_result['union_count']}", self.jaccard_output)
            self.log_message(f"\nJaccard = {jaccard_result['intersection_count']} / {jaccard_result['union_count']}", self.jaccard_output)
            self.log_message(f"       = {jaccard_result['jaccard_similarity']:.6f}", self.jaccard_output)
            self.log_message(f"       = {jaccard_result['jaccard_similarity']*100:.2f}%\n", self.jaccard_output)
            
        elif step == 5:  # Show All Steps
            self.log_message("ALL STEPS\n", self.jaccard_output)
            self.log_message(f"1. Tokens & Sets:", self.jaccard_output)
            self.log_message(f"   Set A: {len(jaccard_result['set1'])} unique terms", self.jaccard_output)
            self.log_message(f"   Set B: {len(jaccard_result['set2'])} unique terms\n", self.jaccard_output)
            self.log_message(f"2. Intersection: {jaccard_result['intersection_count']} common terms", self.jaccard_output)
            self.log_message(f"   {jaccard_result['intersection']}\n", self.jaccard_output)
            self.log_message(f"3. Union: {jaccard_result['union_count']} total unique terms", self.jaccard_output)
            self.log_message(f"   {jaccard_result['union']}\n", self.jaccard_output)
            self.log_message(f"4. Jaccard Similarity = {jaccard_result['jaccard_similarity']:.6f} ({jaccard_result['jaccard_similarity']*100:.2f}%)\n", self.jaccard_output)

    def run_all_jaccard_steps(self):
        """Run all Jaccard steps sequentially"""
        for step in range(1, 6):
            self.show_jaccard_step(step)
            self.root.update()

    def calculate_all_jaccard_documents(self):
        """Calculate Jaccard similarity matrix for all documents"""
        self.jaccard_output.delete(1.0, tk.END)
        
        if self.df_pelatihan is None or self.df_lowongan is None:
            messagebox.showwarning("Warning", "Please load data first!")
            return
        
        if 'preprocessed_text' not in self.df_pelatihan.columns:
            messagebox.showwarning("Warning", "Please preprocess data first!")
            return
        
        self.log_message("=" * 120, self.jaccard_output)
        self.log_message("CALCULATING JACCARD SIMILARITY MATRIX", self.jaccard_output)
        self.log_message("=" * 120, self.jaccard_output)
        
        def calculate():
            try:
                self.log_message("\nCalculating Jaccard similarities...", self.jaccard_output)
                jaccard_matrix = self.calculate_jaccard_matrix()
                
                if jaccard_matrix is None:
                    self.log_message("Error: Failed to calculate matrix", self.jaccard_output)
                    return
                
                # Store matrix
                self.jaccard_matrix = jaccard_matrix
                
                # Statistics
                avg_similarity = jaccard_matrix.mean()
                max_similarity = jaccard_matrix.max()
                min_similarity = jaccard_matrix.min()
                non_zero_count = np.count_nonzero(jaccard_matrix)
                total_count = jaccard_matrix.size
                
                self.log_message("\n" + "=" * 120, self.jaccard_output)
                self.log_message("✅ JACCARD MATRIX CALCULATED", self.jaccard_output)
                self.log_message("=" * 120, self.jaccard_output)
                self.log_message(f"\n📊 Matrix Shape: {jaccard_matrix.shape}", self.jaccard_output)
                self.log_message(f"📊 Total Calculations: {total_count:,}", self.jaccard_output)
                self.log_message(f"\n📈 Statistics:", self.jaccard_output)
                self.log_message(f"   Average: {avg_similarity:.4f} ({avg_similarity*100:.2f}%)", self.jaccard_output)
                self.log_message(f"   Maximum: {max_similarity:.4f} ({max_similarity*100:.2f}%)", self.jaccard_output)
                self.log_message(f"   Minimum: {min_similarity:.4f} ({min_similarity*100:.2f}%)", self.jaccard_output)
                self.log_message(f"   Non-Zero: {non_zero_count:,} ({non_zero_count/total_count*100:.1f}%)", self.jaccard_output)
                
                messagebox.showinfo("Complete", 
                                f"Jaccard similarity matrix calculated!\n\n"
                                f"Average: {avg_similarity:.2%}")
                
            except Exception as e:
                self.log_message(f"\n✗ Error: {str(e)}", self.jaccard_output)
                messagebox.showerror("Error", f"Calculation failed:\n{str(e)}")
        
        threading.Thread(target=calculate, daemon=True).start()

    # ============================================================================
    # COMPARISON FUNCTIONS
    # ============================================================================

    def toggle_comparison_mode(self):
        """Toggle between all pairs and single pair mode"""
        mode = self.comparison_mode_var.get()
        
        if mode == "single":
            # Show single pair frame
            self.single_pair_frame.pack(fill='x', pady=10, after=self.single_pair_frame.master.winfo_children()[1])
            # Load options if not already loaded
            self.load_comparison_document_options()
        else:
            # Hide single pair frame
            self.single_pair_frame.pack_forget()

    def load_comparison_document_options(self):
        """Load document options for single pair comparison"""
        if self.df_pelatihan is None or self.df_lowongan is None:
            return
        
        # Load training options
        if not self.comparison_training_combo['values']:
            training_options = [f"{i}: {row['PROGRAM PELATIHAN']}" 
                                for i, row in self.df_pelatihan.iterrows()]
            self.comparison_training_combo['values'] = training_options
            if training_options:
                self.comparison_training_combo.current(0)
        
        # Load job options
        if not self.comparison_job_combo['values']:
            job_options = [f"{i}: {row['Nama Jabatan (Sumber Perusahaan)']}" 
                        for i, row in self.df_lowongan.iterrows()]
            self.comparison_job_combo['values'] = job_options
            if job_options:
                self.comparison_job_combo.current(0)

    def generate_comparison(self):
        """Generate comparison between Cosine and Jaccard similarities"""
        self.comparison_output.delete(1.0, tk.END)
        
        # Check if both matrices exist
        if not hasattr(self, 'similarity_matrix') or self.similarity_matrix is None:
            messagebox.showwarning("Warning", "Please calculate Cosine similarity matrix first!")
            return
        
        if not hasattr(self, 'jaccard_matrix') or self.jaccard_matrix is None:
            messagebox.showwarning("Warning", "Please calculate Jaccard similarity matrix first!")
            return
        
        mode = self.comparison_mode_var.get()
        threshold = self.comparison_threshold_var.get()
        
        self.log_message("=" * 150, self.comparison_output)
        self.log_message("COSINE VS JACCARD SIMILARITY COMPARISON", self.comparison_output)
        self.log_message("=" * 150, self.comparison_output)
        self.log_message(f"\n⚙️ Mode: {mode} | Threshold: {threshold:.2f}\n", self.comparison_output)
        
        comparisons = []
        
        if mode == "single":
            # Single pair comparison
            try:
                training_idx = int(self.comparison_training_combo.get().split(':')[0])
                job_idx = int(self.comparison_job_combo.get().split(':')[0])
            except:
                messagebox.showerror("Error", "Please select both training and job!")
                return
            
            cosine_score = float(self.similarity_matrix[training_idx, job_idx])
            jaccard_score = float(self.jaccard_matrix[training_idx, job_idx])
            
            if cosine_score > 0 and jaccard_score > 0:
                comparisons.append({
                    'training_idx': training_idx,
                    'training_name': self.df_pelatihan.iloc[training_idx]['PROGRAM PELATIHAN'],
                    'job_idx': job_idx,
                    'job_name': self.df_lowongan.iloc[job_idx]['Nama Jabatan (Sumber Perusahaan)'],
                    'cosine': cosine_score,
                    'jaccard': jaccard_score,
                    'difference': abs(cosine_score - jaccard_score)
                })
        else:
            # All pairs comparison
            for i in range(len(self.df_pelatihan)):
                for j in range(len(self.df_lowongan)):
                    cosine_score = float(self.similarity_matrix[i, j])
                    jaccard_score = float(self.jaccard_matrix[i, j])
                    
                    # Only include if BOTH are > threshold
                    if cosine_score >= threshold and jaccard_score >= threshold:
                        comparisons.append({
                            'training_idx': i,
                            'training_name': self.df_pelatihan.iloc[i]['PROGRAM PELATIHAN'],
                            'job_idx': j,
                            'job_name': self.df_lowongan.iloc[j]['Nama Jabatan (Sumber Perusahaan)'],
                            'cosine': cosine_score,
                            'jaccard': jaccard_score,
                            'difference': abs(cosine_score - jaccard_score)
                        })
        
        if not comparisons:
            self.log_message("No comparisons found above threshold.", self.comparison_output)
            return
        
        # Display table
        self.log_message(f"📊 Found {len(comparisons)} comparisons\n", self.comparison_output)
        self.log_message("=" * 150, self.comparison_output)
        
        # Table header
        self.log_message(
            f"┌{'─' * 45}┬{'─' * 45}┬{'─' * 13}┬{'─' * 13}┬{'─' * 13}┬{'─' * 15}┐",
            self.comparison_output
        )
        self.log_message(
            f"│ {'Training Program':<43} │ {'Job Position':<43} │ {'Cosine':<11} │ {'Jaccard':<11} │ {'Diff':<11} │ {'Higher':<13} │",
            self.comparison_output
        )
        self.log_message(
            f"├{'─' * 45}┼{'─' * 45}┼{'─' * 13}┼{'─' * 13}┼{'─' * 13}┼{'─' * 15}┤",
            self.comparison_output
        )
        
        for comp in comparisons[:100]:  # Show first 100
            training = comp['training_name'][:41] + ".." if len(comp['training_name']) > 43 else comp['training_name']
            job = comp['job_name'][:41] + ".." if len(comp['job_name']) > 43 else comp['job_name']
            
            higher = "Cosine" if comp['cosine'] > comp['jaccard'] else "Jaccard" if comp['jaccard'] > comp['cosine'] else "Equal"
            
            self.log_message(
                f"│ {training:<43} │ {job:<43} │ {comp['cosine']:>11.4f} │ {comp['jaccard']:>11.4f} │ {comp['difference']:>11.4f} │ {higher:<13} │",
                self.comparison_output
            )
        
        self.log_message(
            f"└{'─' * 45}┴{'─' * 45}┴{'─' * 13}┴{'─' * 13}┴{'─' * 13}┴{'─' * 15}┘",
            self.comparison_output
        )
        
        # Statistics
        cosine_values = [c['cosine'] for c in comparisons]
        jaccard_values = [c['jaccard'] for c in comparisons]
        correlation = np.corrcoef(cosine_values, jaccard_values)[0, 1]
        
        self.log_message("\n" + "=" * 150, self.comparison_output)
        self.log_message("📈 STATISTICS", self.comparison_output)
        self.log_message("=" * 150, self.comparison_output)
        self.log_message(f"\nTotal Comparisons: {len(comparisons)}", self.comparison_output)
        self.log_message(f"Average Cosine: {np.mean(cosine_values):.4f}", self.comparison_output)
        self.log_message(f"Average Jaccard: {np.mean(jaccard_values):.4f}", self.comparison_output)
        self.log_message(f"Average Difference: {np.mean([c['difference'] for c in comparisons]):.4f}", self.comparison_output)
        self.log_message(f"Correlation: {correlation:.4f}\n", self.comparison_output)
        
        # Store for export
        self.comparison_results = comparisons

    def export_comparison(self):
        """Export comparison to Excel"""
        if not hasattr(self, 'comparison_results') or not self.comparison_results:
            messagebox.showwarning("Warning", "No comparison results to export!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="cosine_vs_jaccard_comparison.xlsx"
        )
        
        if filename:
            try:
                df = pd.DataFrame(self.comparison_results)
                df.to_excel(filename, index=False, sheet_name='Comparison')
                messagebox.showinfo("Success", 
                                f"Comparison exported successfully!\n"
                                f"File: {filename}\n"
                                f"Records: {len(self.comparison_results)}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed:\n{str(e)}")


def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    app = BBPVPMatchingGUI(root)
    
    def on_closing():
        if app.db_connection and app.db_connection.is_connected():
            app.db_connection.close()
            print("✓ Database connection closed")
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()