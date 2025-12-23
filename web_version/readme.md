# BBPVP Job Matching System - Flask Web Application

A modern, beautiful web-based system for matching job positions with training programs using TF-IDF and Cosine Similarity algorithms.

## 🌟 Features

- **Beautiful Bootstrap 5 UI** - Modern, responsive design with gradient cards and smooth animations
- **Text Preprocessing** - Normalization, stopword removal, tokenization, and stemming (Sastrawi)
- **TF-IDF Calculation** - Full TF-IDF vectorization with detailed step-by-step calculations
- **Similarity Matching** - Cosine similarity-based recommendation engine
- **Database Integration** - MySQL storage for experiments and analysis
- **Export Options** - Export recommendations to Excel or CSV
- **Interactive Tables** - DataTables integration for searching and filtering
- **Real-time Processing** - AJAX-based operations with loading indicators

## 📋 Requirements

```
Python 3.8+
MySQL 5.7+ or MySQL 8.0+
```

## 🚀 Installation

### 1. Clone or Download the Project

```bash
# Create project directory
mkdir bbpvp-flask
cd bbpvp-flask
```

### 2. Install Python Dependencies

```bash
pip install flask pandas numpy scikit-learn mysql-connector-python openpyxl Sastrawi
```

Or use req.txt:

```bash
pip install -r req.txt
```

**req.txt:**
```
Flask==3.0.0
pandas==2.1.0
numpy==1.25.0
scikit-learn==1.3.0
mysql-connector-python==8.1.0
openpyxl==3.1.2
Sastrawi==1.2.0
```

### 3. Setup MySQL Database

**Option A: Using MySQL Workbench or phpMyAdmin**
1. Import the `bbpvp.sql` file
2. This will create the database and all tables

**Option B: Using Command Line**
```bash
mysql -u root -p < bbpvp.sql
```

**Default Database Configuration:**
- Host: `localhost`
- Port: `3307` (or `3306` for default MySQL)
- Database: `bbpvp_thesis`
- User: `root`
- Password: (empty)

### 4. Project Structure

Create the following directory structure:

```
bbpvp-flask/
â"œâ"€â"€ app.py                 # Main Flask application
â"œâ"€â"€ bbpvp.sql              # Database schema
â"œâ"€â"€ requirements.txt       # Python dependencies
â""â"€â"€ templates/             # HTML templates
    â"œâ"€â"€ base.html          # Base template with Bootstrap
    â"œâ"€â"€ index.html         # Home page
    â"œâ"€â"€ database.html      # Database configuration
    â"œâ"€â"€ import.html        # Data import page
    â"œâ"€â"€ preprocessing.html # Preprocessing page
    â"œâ"€â"€ tfidf.html         # TF-IDF calculation page
    â""â"€â"€ recommendations.html # Recommendations page
```

### 5. Configure Database Connection

Edit `app.py` and update the database configuration if needed:

```python
DB_CONFIG = {
    'host': 'localhost',      # Your MySQL host
    'port': 3307,             # Your MySQL port
    'database': 'bbpvp_thesis',
    'user': 'root',           # Your MySQL username
    'password': '',           # Your MySQL password
    'charset': 'utf8mb4',
    'use_unicode': True
}
```

## â–¶ï¸ Running the Application

### 1. Start MySQL Server

Make sure your MySQL server is running:
- **XAMPP**: Start MySQL from XAMPP Control Panel
- **Standalone MySQL**: Service should be running
- **Docker**: `docker start mysql-container`

### 2. Run Flask Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

### 3. Access the Application

Open your web browser and navigate to:
```
http://localhost:5000
```

## 📖 Usage Guide

### Step 1: Configure Database
1. Go to **Database** page
2. Verify connection settings
3. Click "Test Connection"
4. Configuration is saved automatically

### Step 2: Import Data
1. Go to **Import** page
2. Select "Load from GitHub" (default)
3. Click "Load BOTH Data"
4. Wait for data to load

### Step 3: Preprocess Data
1. Go to **Preprocessing** page
2. Click "Process All Data"
3. Wait for processing to complete
4. View sample preprocessing steps if needed

### Step 4: Calculate Similarity
1. Go to **TF-IDF** page
2. Click "Calculate All Documents"
3. Similarity matrix will be computed

### Step 5: Get Recommendations
1. Go to **Recommendations** page
2. Choose recommendation mode:
   - **Single Job**: Get recommendations for one job
   - **All Jobs**: Get recommendations for all jobs
3. Set parameters:
   - Top N: Number of recommendations per job
   - Threshold: Minimum similarity score
4. Click "Get Recommendations"
5. Export results to Excel or CSV

## 🎨 Additional Templates to Create

You'll need to create these additional templates based on the pattern shown:

### templates/database.html
- Database configuration form
- Connection testing
- Status display

### templates/import.html
- Data source selection (GitHub/Upload)
- Load buttons for training and job data
- Status and preview display

### templates/preprocessing.html
- Dataset selection
- Row selection for step-by-step view
- Process all button
- Output display

### templates/tfidf.html
- Document selection
- TF-IDF calculation steps
- Calculate all documents button
- Results display

## 🔧 Troubleshooting

### Database Connection Error
```
Error: Can't connect to MySQL server
```
**Solution:**
- Check MySQL is running
- Verify port number (3306 or 3307)
- Check username and password
- Ensure database `bbpvp_thesis` exists

### Port Already in Use
```
Error: Address already in use
```
**Solution:**
```bash
# Change port in app.py
app.run(debug=True, port=5001)  # Use different port
```

### Sastrawi Not Found
```
Warning: Sastrawi not available
```
**Solution:**
```bash
pip install Sastrawi
```

### Module Not Found
```
ModuleNotFoundError: No module named 'flask'
```
**Solution:**
```bash
pip install -r requirements.txt
```

## 📊 Database Schema

The system uses 6 main tables:
- **experiments** - Track analysis sessions
- **preprocessing_samples** - Store preprocessing examples
- **tfidf_calculations** - Store TF-IDF calculations
- **similarity_matrix** - Store all similarity scores
- **recommendations** - Store final recommendations
- **statistics** - Store dataset statistics

## 🎯 Key Technologies

- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5, jQuery
- **Database**: MySQL
- **ML Libraries**: scikit-learn (TF-IDF, Cosine Similarity)
- **NLP**: Sastrawi (Indonesian Stemmer)
- **Tables**: DataTables
- **Charts**: Chart.js
- **Icons**: Font Awesome

## 📝 Notes

- Data is loaded from GitHub by default
- File upload feature can be implemented for local files
- Session storage is used for temporary data
- All experiments are saved to database for analysis
- Export functions generate Excel/CSV files

## 🔐 Security Notes

**For Production:**
1. Change the secret key in `app.py`
2. Use environment variables for sensitive data
3. Enable HTTPS
4. Implement user authentication
5. Add CSRF protection
6. Validate all inputs

## 📄 License

This project is for educational/thesis purposes.

## 👥 Support

For issues or questions:
1. Check troubleshooting section
2. Verify all dependencies are installed
3. Ensure MySQL is running
4. Check console for error messages

---

**Developed for BBPVP Training Program Matching System**