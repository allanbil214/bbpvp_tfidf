"""
BBPVP Job Matching System - GUI Application
A complete GUI for text preprocessing and TF-IDF based job matching
"""
# pip install pandas numpy scikit-learn matplotlib Sastrawi openpyxl

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
import threading

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
        self.root.geometry("1200x800")
        
        # Data storage
        self.df_pelatihan = None
        self.df_lowongan = None
        self.current_step = 0
        
        # GitHub URLs
        self.github_training_url = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/2.%20data%20bersih%20Program%20Pelatihan%20Tahun.xlsx"
        self.github_jobs_url = "https://github.com/allanbil214/bbpvp_tfidf/raw/refs/heads/main/data/3%20.%20databersih-%20Rekap%20Surat%20Masuk%20dan%20Lowongan%202025.xlsx"
        
        # Indonesian stopwords
        self.stopwords = {
            'dan', 'di', 'ke', 'dari', 'yang', 'untuk', 'pada', 'dengan',
            'dalam', 'adalah', 'ini', 'itu', 'atau', 'oleh', 'sebagai',
            'juga', 'akan', 'telah', 'dapat', 'ada', 'tidak', 'hal',
            'tersebut', 'serta', 'bagi', 'hanya', 'sangat', 'bila',
            'saat', 'kini', 'yaitu', 'dll', 'dsb', 'dst', 'setelah', 'mengikuti', 'sesuai', 'pelatihan'
        }

        self.custom_stem_rules = {
            'peserta': 'peserta',     
            'perawatan': 'rawat',
        }
        
        self.tabs_config = {
            "import": {
                "title": "1. Import Data",
                "visible": True,
                "builder": self.create_import_tab
            },
            "preprocess": {
                "title": "2. Preprocessing",
                "visible": True,
                "builder": self.create_preprocess_tab
            },
            "tfidf": {
                "title": "3. TF-IDF & Cosine Similarity",
                "visible": True,
                "builder": self.create_tfidf_tab
            },
            "recommendations": {
                "title": "4. Recommendations",
                "visible": True,
                "builder": self.create_recommendations_tab
            },
            "results": {
                "title": "5. Results & Analysis (WIP)",
                "visible": False,
                "builder": self.create_results_tab
            }
        }

        self.create_widgets()
        
    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        for cfg in self.tabs_config.values():
            if not cfg["visible"]:
                continue

            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=cfg["title"])
            cfg["builder"](frame)
        
    def create_import_tab(self, parent):
        # Main frame
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Data Import", font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Data source selection
        source_frame = ttk.LabelFrame(main_frame, text="Select Data Source", padding="10")
        source_frame.pack(fill='x', pady=10)
        
        self.data_source_var = tk.StringVar(value="github")
        
        ttk.Radiobutton(source_frame, text="Load from GitHub", 
                       variable=self.data_source_var, value="github").pack(anchor='w')
        ttk.Radiobutton(source_frame, text="Upload from Local Files", 
                       variable=self.data_source_var, value="upload").pack(anchor='w')
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Load BOTH Data (Training + Job)", 
                  command=self.load_both_data, width=35,
                  style='Accent.TButton').pack(pady=5)
        
        ttk.Separator(button_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(button_frame, text="Or load individually:", 
                 font=('Arial', 9, 'italic')).pack(pady=5)
        
        ttk.Button(button_frame, text="Load Training Data (Pelatihan)", 
                  command=self.load_training_data, width=30).pack(pady=5)
        ttk.Button(button_frame, text="Load Job Data (Lowongan)", 
                  command=self.load_job_data, width=30).pack(pady=5)
        
        # Status text
        self.import_status = scrolledtext.ScrolledText(main_frame, height=15, width=80)
        self.import_status.pack(pady=10, fill='both', expand=True)
        
    def create_preprocess_tab(self, parent):
        # Main frame with two columns
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls
        left_frame = ttk.Frame(main_frame, width=300)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        
        title = ttk.Label(left_frame, text="Preprocessing Steps", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Dataset selection
        dataset_frame = ttk.LabelFrame(left_frame, text="Select Dataset", padding="10")
        dataset_frame.pack(fill='x', pady=10)
        
        self.dataset_var = tk.StringVar(value="pelatihan")
        ttk.Radiobutton(dataset_frame, text="Training Programs (Pelatihan)", 
                       variable=self.dataset_var, value="pelatihan").pack(anchor='w')
        ttk.Radiobutton(dataset_frame, text="Job Positions (Lowongan)", 
                       variable=self.dataset_var, value="lowongan").pack(anchor='w')
        
        # Row selection
        row_frame = ttk.LabelFrame(left_frame, text="Select Row", padding="10")
        row_frame.pack(fill='x', pady=10)
        
        ttk.Label(row_frame, text="Row Index:").pack()
        self.row_spinbox = ttk.Spinbox(row_frame, from_=0, to=100, width=10)
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
                      width=25).pack(pady=2)
        
        # Process all button
        ttk.Button(left_frame, text="Process All Data", 
                  command=self.process_all_data,
                  style='Accent.TButton', width=25).pack(pady=20)
        
        # Right panel - Display
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(right_frame, text="Preprocessing Output", 
                 font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.preprocess_output = scrolledtext.ScrolledText(right_frame, height=30, 
                                                           wrap=tk.WORD, font=('Consolas', 10))
        self.preprocess_output.pack(fill='both', expand=True)
        
    def create_results_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        title = ttk.Label(main_frame, text="Analysis Results", font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(main_frame, text="Dataset Statistics", padding="10")
        stats_frame.pack(fill='x', pady=10)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=10, width=80)
        self.stats_text.pack(fill='both', expand=True)
        
        # Visualization frame
        viz_frame = ttk.LabelFrame(main_frame, text="Token Distribution", padding="10")
        viz_frame.pack(fill='both', expand=True, pady=10)
        
        self.viz_canvas_frame = ttk.Frame(viz_frame)
        self.viz_canvas_frame.pack(fill='both', expand=True)
        
        # Generate button
        ttk.Button(main_frame, text="Generate Statistics & Visualization", 
                  command=self.generate_statistics,
                  style='Accent.TButton').pack(pady=10)
    
    def create_tfidf_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="TF-IDF Calculation & Similarity", 
                         font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=10)
        
        # Left controls
        left_control = ttk.Frame(control_frame)
        left_control.pack(side='left', fill='x', expand=True)
        
        # Document selection
        doc_frame = ttk.LabelFrame(left_control, text="Select Documents", padding="10")
        doc_frame.pack(fill='x', pady=5)
        
        ttk.Label(doc_frame, text="Pelatihan (Document 1):").grid(row=0, column=0, sticky='w', pady=2)
        self.pelatihan_combo = ttk.Combobox(doc_frame, width=40, state='readonly')
        self.pelatihan_combo.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(doc_frame, text="Lowongan (Document 2):").grid(row=1, column=0, sticky='w', pady=2)
        self.lowongan_combo = ttk.Combobox(doc_frame, width=40, state='readonly')
        self.lowongan_combo.grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Button(doc_frame, text="Load Document Options", 
                  command=self.load_document_options).grid(row=2, column=0, columnspan=2, pady=5)
        
        # Step buttons
        step_frame = ttk.LabelFrame(left_control, text="TF-IDF Steps", padding="10")
        step_frame.pack(fill='x', pady=5)
        
        steps = [
            ("Step 1: Show Tokens", self.show_tokens),
            ("Step 2: Calculate TF (Term Frequency)", self.calculate_tf),
            ("Step 3: Calculate DF (Document Frequency)", self.calculate_df),
            ("Step 4: Calculate IDF", self.calculate_idf),
            ("Step 5: Calculate TF-IDF", self.calculate_tfidf),
            ("Step 6: Calculate Cosine Similarity", self.calculate_similarity),
        ]
        
        for i, (step_name, command) in enumerate(steps):
            ttk.Button(step_frame, text=step_name, command=command, 
                      width=40).grid(row=i, column=0, pady=2, sticky='ew')
        
        ttk.Button(step_frame, text="▶ Run All Steps", 
                  command=self.run_all_tfidf_steps,
                  style='Accent.TButton', width=40).grid(row=len(steps), column=0, pady=10, sticky='ew')
        
        # Right side - Calculate All button
        right_control = ttk.Frame(control_frame)
        right_control.pack(side='right', padx=10)
        
        ttk.Button(right_control, text="Calculate All Documents\n(Full Matrix)", 
                  command=self.calculate_all_documents,
                  style='Accent.TButton', width=25).pack(pady=5)
        
        # Output area
        output_frame = ttk.LabelFrame(main_frame, text="TF-IDF Calculation Output", padding="10")
        output_frame.pack(fill='both', expand=True, pady=10)
        
        self.tfidf_output = scrolledtext.ScrolledText(output_frame, height=25, 
                                                      wrap=tk.WORD, font=('Consolas', 9))
        self.tfidf_output.pack(fill='both', expand=True)

    def create_recommendations_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Training Program Recommendations", 
                        font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=10)
        
        # Left side - Single Job Recommendation
        left_frame = ttk.LabelFrame(control_frame, text="Option 1: Single Job Recommendation", 
                                    padding="10")
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        ttk.Label(left_frame, text="Select Job Position:").pack(anchor='w', pady=5)
        self.rec_job_combo = ttk.Combobox(left_frame, width=50, state='readonly')
        self.rec_job_combo.pack(fill='x', pady=5)
        
        ttk.Label(left_frame, text="Number of Recommendations:").pack(anchor='w', pady=5)
        self.rec_count_spinbox = ttk.Spinbox(left_frame, from_=1, to=20, width=10)
        self.rec_count_spinbox.set(5)
        self.rec_count_spinbox.pack(anchor='w', pady=5)
        
        ttk.Button(left_frame, text="Get Recommendations for Selected Job", 
                command=self.show_single_job_recommendations,
                style='Accent.TButton', width=40).pack(pady=10)
        
        # Right side - All Jobs Recommendation
        right_frame = ttk.LabelFrame(control_frame, text="Option 2: All Jobs Recommendation", 
                                    padding="10")
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        ttk.Label(right_frame, text="Top N recommendations per job:").pack(anchor='w', pady=5)
        self.rec_all_count_spinbox = ttk.Spinbox(right_frame, from_=1, to=10, width=10)
        self.rec_all_count_spinbox.set(3)
        self.rec_all_count_spinbox.pack(anchor='w', pady=5)
        
        ttk.Label(right_frame, text="Minimum Similarity Threshold:").pack(anchor='w', pady=5)
        threshold_frame = ttk.Frame(right_frame)
        threshold_frame.pack(fill='x', pady=5)
        self.rec_threshold_var = tk.DoubleVar(value=0.0)
        self.rec_threshold_scale = ttk.Scale(threshold_frame, from_=0.0, to=1.0, 
                                            variable=self.rec_threshold_var, 
                                            orient='horizontal')
        self.rec_threshold_scale.pack(side='left', fill='x', expand=True)
        self.rec_threshold_label = ttk.Label(threshold_frame, text="0.00", width=6)
        self.rec_threshold_label.pack(side='right', padx=5)
        
        # Update label when scale changes
        def update_threshold_label(*args):
            self.rec_threshold_label.config(text=f"{self.rec_threshold_var.get():.2f}")
        self.rec_threshold_var.trace('w', update_threshold_label)
        
        ttk.Button(right_frame, text="Get Recommendations for ALL Jobs", 
                command=self.show_all_jobs_recommendations,
                style='Accent.TButton', width=40).pack(pady=10)
        
        # Buttons frame
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text="Export to Excel", 
                command=self.export_recommendations_excel,
                width=19).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Export to CSV", 
                command=self.export_recommendations_csv,
                width=19).pack(side='right', padx=2)
        
        # Output area with scrollbar
        output_frame = ttk.LabelFrame(main_frame, text="Recommendation Results", padding="10")
        output_frame.pack(fill='both', expand=True, pady=10)
        
        # Create text widget with scrollbar
        self.rec_output = scrolledtext.ScrolledText(output_frame, height=25, 
                                                    wrap=tk.WORD, font=('Consolas', 9))
        self.rec_output.pack(fill='both', expand=True)
        
        # Info label
        info_label = ttk.Label(main_frame, 
                            text="💡 Tip: Process data in tabs 1-2, then calculate similarity in tab 3 before getting recommendations",
                            font=('Arial', 9, 'italic'))
        info_label.pack(pady=5)

    def log_message(self, message, widget=None):
        """Log message to specified widget or import_status"""
        if widget is None:
            widget = self.import_status
        widget.insert(tk.END, message + "\n")
        widget.see(tk.END)
        self.root.update()
    
    def load_both_data(self):
        """Load both training and job data at once"""
        if self.data_source_var.get() != "github":
            messagebox.showinfo("Info", 
                              "Load Both Data option is only available for GitHub source.\n"
                              "Please select 'Load from GitHub' or load files individually.")
            return
        
        self.import_status.delete(1.0, tk.END)
        self.log_message("=" * 80)
        self.log_message("LOADING BOTH DATASETS FROM GITHUB")
        self.log_message("=" * 80)
        
        def load():
            try:
                # Load Training Data
                self.log_message("\n[1/2] Loading Training Data (Pelatihan)...")
                self.log_message(f"URL: {self.github_training_url}")
                self.df_pelatihan = pd.read_excel(self.github_training_url, 
                                                 sheet_name="Versi Ringkas Untuk Tesis")
                self.log_message(f"✓ Training Data loaded: {self.df_pelatihan.shape[0]} rows, "
                               f"{self.df_pelatihan.shape[1]} columns")
                
                # Fill missing values
                self.fill_missing_pelatihan()
                
                # Load Job Data
                self.log_message("\n[2/2] Loading Job Data (Lowongan)...")
                self.log_message(f"URL: {self.github_jobs_url}")
                self.df_lowongan = pd.read_excel(self.github_jobs_url, 
                                                sheet_name="petakan ke KBJI")
                self.log_message(f"✓ Job Data loaded: {self.df_lowongan.shape[0]} rows, "
                               f"{self.df_lowongan.shape[1]} columns")
                
                # Summary
                self.log_message("\n" + "=" * 80)
                self.log_message("✓ BOTH DATASETS LOADED SUCCESSFULLY!")
                self.log_message("=" * 80)
                self.log_message(f"\n📊 Summary:")
                self.log_message(f"  • Training Programs: {len(self.df_pelatihan)} records")
                self.log_message(f"  • Job Positions: {len(self.df_lowongan)} records")
                self.log_message(f"  • Total: {len(self.df_pelatihan) + len(self.df_lowongan)} records")
                
                self.log_message(f"\n📋 Training Data Columns:")
                self.log_message(f"  {', '.join(self.df_pelatihan.columns.tolist())}")
                
                self.log_message(f"\n📋 Job Data Columns:")
                self.log_message(f"  {', '.join(self.df_lowongan.columns.tolist())}")
                
                self.log_message(f"\n✨ Ready for preprocessing! Go to 'Preprocessing' tab.")
                
                messagebox.showinfo("Success", 
                                  f"Both datasets loaded successfully!\n\n"
                                  f"Training: {len(self.df_pelatihan)} records\n"
                                  f"Jobs: {len(self.df_lowongan)} records")
                
            except Exception as e:
                self.log_message(f"\n✗ Error: {str(e)}")
                messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
        
        threading.Thread(target=load, daemon=True).start()
    
    def load_training_data(self):
        self.import_status.delete(1.0, tk.END)
        self.log_message("Loading Training Data (Pelatihan)...")
        
        def load():
            try:
                if self.data_source_var.get() == "github":
                    self.log_message(f"Fetching from GitHub...")
                    self.df_pelatihan = pd.read_excel(self.github_training_url, 
                                                     sheet_name="Versi Ringkas Untuk Tesis")
                else:
                    filename = filedialog.askopenfilename(
                        title="Select Training Data File",
                        filetypes=[("Excel files", "*.xlsx *.xls")]
                    )
                    if filename:
                        self.log_message(f"Loading from: {filename}")
                        self.df_pelatihan = pd.read_excel(filename, 
                                                         sheet_name="Versi Ringkas Untuk Tesis")
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
                    self.df_lowongan = pd.read_excel(self.github_jobs_url, 
                                                    sheet_name="petakan ke KBJI")
                else:
                    filename = filedialog.askopenfilename(
                        title="Select Job Data File",
                        filetypes=[("Excel files", "*.xlsx *.xls")]
                    )
                    if filename:
                        self.log_message(f"Loading from: {filename}")
                        self.df_lowongan = pd.read_excel(filename, 
                                                        sheet_name="petakan ke KBJI")
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
    
    def fill_missing_pelatihan(self):
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
        
        self.df_pelatihan['Tujuan/Kompetensi'] = self.df_pelatihan.apply(fill_tujuan, axis=1)
        self.df_pelatihan['Deskripsi Program'] = self.df_pelatihan.apply(fill_deskripsi, axis=1)
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
        lowongan_options = [f"{i}: {row['Nama Jabatan']}" 
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
        
        self.log_message(f"\n📄 Document 2 (D2): {doc2['Nama Jabatan']}", self.tfidf_output)
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
        doc2_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan']
        
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
            idf = np.log((N + 1) / (df + 1)) + 1 # smoothing
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
        doc2_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan']
        
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
        doc2_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan']
        
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
    
    def calculate_all_documents(self):
        """Calculate similarity matrix for all documents"""
        if self.df_pelatihan is None or self.df_lowongan is None:
            messagebox.showwarning("Warning", "Please load and preprocess data first!")
            return
        
        if 'preprocessed_text' not in self.df_pelatihan.columns:
            messagebox.showwarning("Warning", "Please preprocess data first!")
            return
        
        self.tfidf_output.delete(1.0, tk.END)
        self.log_message("Calculating similarity matrix for all documents...", self.tfidf_output)
        self.log_message("This may take a moment...\n", self.tfidf_output)
        
        # Use sklearn for full matrix (more efficient for many documents)
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Combine all texts
        all_texts = list(self.df_pelatihan['preprocessed_text']) + \
                   list(self.df_lowongan['preprocessed_text'])
        
        # Calculate TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        # Split back
        n_pelatihan = len(self.df_pelatihan)
        pelatihan_vectors = tfidf_matrix[:n_pelatihan]
        lowongan_vectors = tfidf_matrix[n_pelatihan:]
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(pelatihan_vectors, lowongan_vectors)
        
        # Display results
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message("SIMILARITY MATRIX - ALL DOCUMENTS", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        self.log_message(f"\nTotal Pelatihan: {n_pelatihan}", self.tfidf_output)
        self.log_message(f"Total Lowongan: {len(self.df_lowongan)}", self.tfidf_output)
        self.log_message(f"Matrix shape: {similarity_matrix.shape}", self.tfidf_output)
        
        # Top matches for each lowongan
        self.log_message("\n" + "=" * 80, self.tfidf_output)
        self.log_message("TOP RECOMMENDATIONS FOR EACH JOB POSITION", self.tfidf_output)
        self.log_message("=" * 80, self.tfidf_output)
        
        for low_idx in range(len(self.df_lowongan)):
            lowongan_name = self.df_lowongan.iloc[low_idx]['Nama Jabatan']
            similarities = similarity_matrix[:, low_idx]
            top_3_indices = np.argsort(similarities)[-3:][::-1]
            
            self.log_message(f"\n📋 {lowongan_name}", self.tfidf_output)
            self.log_message("   Recommended training programs:", self.tfidf_output)
            for rank, pel_idx in enumerate(top_3_indices, 1):
                pelatihan_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
                sim_score = similarities[pel_idx]
                self.log_message(f"   {rank}. {pelatihan_name} (Similarity: {sim_score:.4f})", 
                               self.tfidf_output)
        
        messagebox.showinfo("Complete", "Similarity calculation completed!")
        
        # Store for later use
        self.similarity_matrix = similarity_matrix
    
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
            text_col = 'Nama Jabatan'
        
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
                        f"{row['Tujuan/Kompetensi']} "
                       # f"{row['Deskripsi Program']}"
                       )
        else:
            original = (# f"{row['Nama Jabatan']} {row.get('Nama KBJI Resmi', '')} "
                       f"{row.get('Deskripsi KBJI', '')} " 
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
        """Process all data through all preprocessing steps"""
        self.preprocess_output.delete(1.0, tk.END)
        self.log_message("Processing all data...", self.preprocess_output)
        
        def process():
            # Process Training Data
            if self.df_pelatihan is not None:
                self.log_message("\n" + "=" * 80, self.preprocess_output)
                self.log_message("PROCESSING TRAINING DATA (PELATIHAN)", self.preprocess_output)
                self.log_message("=" * 80, self.preprocess_output)
                
                # Combine text features
                self.df_pelatihan['text_features'] = (
                    # self.df_pelatihan['PROGRAM PELATIHAN'].fillna('') + ' ' +
                    self.df_pelatihan['Tujuan/Kompetensi'].fillna('') 
                    # + ' ' +
                    # self.df_pelatihan['Deskripsi Program'].fillna('')
                )
                
                # Apply preprocessing
                self.df_pelatihan['normalized'] = self.df_pelatihan['text_features'].apply(
                    self.normalize_text)
                self.log_message("✓ Normalization completed", self.preprocess_output)
                
                self.df_pelatihan['no_stopwords'] = self.df_pelatihan['normalized'].apply(
                    self.remove_stopwords)
                self.log_message("✓ Stopword removal completed", self.preprocess_output)
                
                self.df_pelatihan['tokens'] = self.df_pelatihan['no_stopwords'].apply(
                    self.tokenize_text)
                self.log_message("✓ Tokenization completed", self.preprocess_output)
                
                self.df_pelatihan['stemmed_tokens'] = self.df_pelatihan['tokens'].apply(
                    self.stem_tokens)
                self.log_message("✓ Stemming (per token) completed", self.preprocess_output)
                
                self.df_pelatihan['stemmed'] = self.df_pelatihan['stemmed_tokens'].apply(
                    lambda x: ' '.join(x))
                self.df_pelatihan['token_count'] = self.df_pelatihan['stemmed_tokens'].apply(len)
                self.df_pelatihan['preprocessed_text'] = self.df_pelatihan['stemmed']
                
                self.log_message(f"\n✓ Processed {len(self.df_pelatihan)} training programs", 
                               self.preprocess_output)
                self.log_message(f"Average tokens: {self.df_pelatihan['token_count'].mean():.1f}", 
                               self.preprocess_output)
            
            # Process Job Data
            if self.df_lowongan is not None:
                self.log_message("\n" + "=" * 80, self.preprocess_output)
                self.log_message("PROCESSING JOB DATA (LOWONGAN)", self.preprocess_output)
                self.log_message("=" * 80, self.preprocess_output)
                
                # Combine text features
                self.df_lowongan['text_features'] = (
                    # self.df_lowongan['Nama Jabatan'].fillna('') + ' ' +
                    # self.df_lowongan['Nama KBJI Resmi'].fillna('') + ' ' +
                    self.df_lowongan['Deskripsi KBJI'].fillna('') 
                    # + ' ' +
                    # self.df_lowongan['Kompetensi'].fillna('')
                )
                
                # Apply preprocessing
                self.df_lowongan['normalized'] = self.df_lowongan['text_features'].apply(
                    self.normalize_text)
                self.log_message("✓ Normalization completed", self.preprocess_output)
                
                self.df_lowongan['no_stopwords'] = self.df_lowongan['normalized'].apply(
                    self.remove_stopwords)
                self.log_message("✓ Stopword removal completed", self.preprocess_output)
                
                self.df_lowongan['tokens'] = self.df_lowongan['no_stopwords'].apply(
                    self.tokenize_text)
                self.log_message("✓ Tokenization completed", self.preprocess_output)
                
                self.df_lowongan['stemmed_tokens'] = self.df_lowongan['tokens'].apply(
                    self.stem_tokens)
                self.log_message("✓ Stemming (per token) completed", self.preprocess_output)
                
                self.df_lowongan['stemmed'] = self.df_lowongan['stemmed_tokens'].apply(
                    lambda x: ' '.join(x))
                self.df_lowongan['token_count'] = self.df_lowongan['stemmed_tokens'].apply(len)
                self.df_lowongan['preprocessed_text'] = self.df_lowongan['stemmed']
                
                self.log_message(f"\n✓ Processed {len(self.df_lowongan)} job positions", 
                               self.preprocess_output)
                self.log_message(f"Average tokens: {self.df_lowongan['token_count'].mean():.1f}", 
                               self.preprocess_output)
            
            self.log_message("\n" + "=" * 80, self.preprocess_output)
            self.log_message("ALL DATA PROCESSING COMPLETED!", self.preprocess_output)
            self.log_message("=" * 80, self.preprocess_output)
            # self.log_message("\nYou can now view statistics in the 'Results & Analysis' tab.", 
            #                self.preprocess_output)
        
        threading.Thread(target=process, daemon=True).start()

    def load_recommendation_options(self):
        """Load job options for recommendations"""
        if self.df_lowongan is None:
            return False
        
        job_options = [f"{i}: {row['Nama Jabatan']}" 
                    for i, row in self.df_lowongan.iterrows()]
        self.rec_job_combo['values'] = job_options
        if job_options:
            self.rec_job_combo.current(0)
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
        except:
            messagebox.showerror("Error", "Please select a job position!")
            return
        
        job_name = self.df_lowongan.iloc[job_idx]['Nama Jabatan']
        job_desc = self.df_lowongan.iloc[job_idx].get('Deskripsi KBJI', 'N/A')
        
        # Get similarities for this job
        similarities = self.similarity_matrix[:, job_idx]
        
        # Get top N recommendations
        top_indices = np.argsort(similarities)[-n_recommendations:][::-1]
        
        # Display results
        self.log_message("=" * 100, self.rec_output)
        self.log_message("TRAINING PROGRAM RECOMMENDATIONS - SINGLE JOB", self.rec_output)
        self.log_message("=" * 100, self.rec_output)
        
        self.log_message(f"\n🎯 JOB POSITION:", self.rec_output)
        self.log_message(f"   {job_name}", self.rec_output)
        self.log_message(f"\n📄 Job Description:", self.rec_output)
        self.log_message(f"   {job_desc[:200]}...", self.rec_output)
        
        self.log_message(f"\n\n📊 TOP {n_recommendations} RECOMMENDED TRAINING PROGRAMS:", self.rec_output)
        self.log_message("=" * 100, self.rec_output)
        
        for rank, pel_idx in enumerate(top_indices, 1):
            program_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
            similarity = similarities[pel_idx]
            tujuan = self.df_pelatihan.iloc[pel_idx].get('Tujuan/Kompetensi', 'N/A')
            
            # Similarity interpretation
            if similarity >= 0.80:
                match_level = "⭐⭐⭐⭐⭐ EXCELLENT MATCH"
                color_marker = "🟢"
            elif similarity >= 0.65:
                match_level = "⭐⭐⭐⭐ VERY GOOD MATCH"
                color_marker = "🟢"
            elif similarity >= 0.50:
                match_level = "⭐⭐⭐ GOOD MATCH"
                color_marker = "🟡"
            elif similarity >= 0.35:
                match_level = "⭐⭐ FAIR MATCH"
                color_marker = "🟡"
            else:
                match_level = "⭐ WEAK MATCH"
                color_marker = "🔴"
            
            self.log_message(f"\n{color_marker} RANK #{rank}", self.rec_output)
            self.log_message(f"{'─' * 100}", self.rec_output)
            self.log_message(f"Program      : {program_name}", self.rec_output)
            self.log_message(f"Similarity   : {similarity:.4f} ({similarity*100:.2f}%)", self.rec_output)
            self.log_message(f"Match Level  : {match_level}", self.rec_output)
            self.log_message(f"Objective    : {tujuan[:150]}...", self.rec_output)
        
        self.log_message("\n" + "=" * 100, self.rec_output)
        self.log_message("✅ RECOMMENDATION COMPLETE", self.rec_output)
        self.log_message("=" * 100, self.rec_output)

    def show_all_jobs_recommendations(self):
        """Show recommendations for all jobs"""
        self.rec_output.delete(1.0, tk.END)
        
        # Check if data is ready
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
        self.log_message("=" * 100, self.rec_output)
        self.log_message("TRAINING PROGRAM RECOMMENDATIONS - ALL JOBS", self.rec_output)
        self.log_message("=" * 100, self.rec_output)
        self.log_message(f"\n📊 Settings:", self.rec_output)
        self.log_message(f"   • Top N recommendations per job: {n_recommendations}", self.rec_output)
        self.log_message(f"   • Minimum similarity threshold: {threshold:.2f}", self.rec_output)
        self.log_message(f"   • Total job positions: {len(self.df_lowongan)}", self.rec_output)
        self.log_message(f"   • Total training programs: {len(self.df_pelatihan)}", self.rec_output)
        
        # Store all recommendations for export
        self.all_recommendations = []
        
        # Process each job
        for job_idx in range(len(self.df_lowongan)):
            job_name = self.df_lowongan.iloc[job_idx]['Nama Jabatan']
            similarities = self.similarity_matrix[:, job_idx]
            
            # Get top N that meet threshold
            top_indices = np.argsort(similarities)[::-1]
            filtered_indices = [idx for idx in top_indices 
                            if similarities[idx] >= threshold][:n_recommendations]
            
            if not filtered_indices:
                continue
            
            self.log_message(f"\n\n{'═' * 100}", self.rec_output)
            self.log_message(f"🎯 JOB #{job_idx + 1}: {job_name}", self.rec_output)
            self.log_message(f"{'═' * 100}", self.rec_output)
            
            for rank, pel_idx in enumerate(filtered_indices, 1):
                program_name = self.df_pelatihan.iloc[pel_idx]['PROGRAM PELATIHAN']
                similarity = similarities[pel_idx]
                
                # Match level indicator
                if similarity >= 0.80:
                    indicator = "🟢"
                elif similarity >= 0.50:
                    indicator = "🟡"
                else:
                    indicator = "🔴"
                
                self.log_message(f"\n   {indicator} {rank}. {program_name}", self.rec_output)
                self.log_message(f"      Similarity: {similarity:.4f} ({similarity*100:.2f}%)", 
                            self.rec_output)
                
                # Store for export
                self.all_recommendations.append({
                    'Job_Index': job_idx,
                    'Job_Name': job_name,
                    'Rank': rank,
                    'Training_Index': pel_idx,
                    'Training_Program': program_name,
                    'Similarity_Score': similarity,
                    'Similarity_Percentage': similarity * 100
                })
        
        self.log_message(f"\n\n{'═' * 100}", self.rec_output)
        self.log_message("✅ ALL RECOMMENDATIONS COMPLETE", self.rec_output)
        self.log_message(f"{'═' * 100}", self.rec_output)
        self.log_message(f"\nTotal recommendations generated: {len(self.all_recommendations)}", 
                    self.rec_output)
        self.log_message(f"\n💡 You can now export these recommendations using the export buttons above.", 
                    self.rec_output)

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


def main():
    root = tk.Tk()
    
    # Set style
    style = ttk.Style()
    style.theme_use('clam')
    
    app = BBPVPMatchingGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()