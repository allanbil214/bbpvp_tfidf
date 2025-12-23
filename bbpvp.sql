-- ============================================================================
-- BBPVP Job Matching System - Thesis Database Schema
-- Purpose: Store preprocessing steps, calculations, and results for S2 thesis
-- Database: MySQL 5.7+
-- ============================================================================

-- Create database
CREATE DATABASE IF NOT EXISTS bbpvp_thesis 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE bbpvp_thesis;

-- ============================================================================
-- TABLE 1: experiments
-- Purpose: Track each analysis session/run for thesis documentation
-- ============================================================================
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_name VARCHAR(255) NOT NULL,
    description TEXT,
    dataset_training_count INT,
    dataset_job_count INT,
    similarity_threshold DECIMAL(5,4) DEFAULT 0.0000,
    top_n_recommendations INT DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    status ENUM('running', 'completed', 'failed') DEFAULT 'running',
    notes TEXT,
    INDEX idx_created (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 2: preprocessing_samples
-- Purpose: Store sample preprocessing steps for thesis methodology chapter
-- ============================================================================
CREATE TABLE IF NOT EXISTS preprocessing_samples (
    sample_id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_id INT NOT NULL,
    dataset_type ENUM('training', 'job') NOT NULL,
    record_index INT NOT NULL,
    record_name VARCHAR(500),
    
    -- Preprocessing steps
    original_text TEXT,
    normalized_text TEXT,
    stopwords_removed TEXT,
    tokenized TEXT,
    stemmed_text TEXT,
    token_count INT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    INDEX idx_experiment (experiment_id),
    INDEX idx_dataset_type (dataset_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 3: tfidf_calculations
-- Purpose: Store sample TF-IDF calculations for thesis examples
-- ============================================================================
CREATE TABLE IF NOT EXISTS tfidf_calculations (
    calculation_id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_id INT NOT NULL,
    training_index INT NOT NULL,
    training_name VARCHAR(500),
    job_index INT NOT NULL,
    job_name VARCHAR(500),
    
    -- Calculation details (stored as JSON for flexibility)
    unique_terms_count INT,
    terms_json JSON COMMENT 'Array of unique terms',
    tf_training_json JSON COMMENT 'TF values for training document',
    tf_job_json JSON COMMENT 'TF values for job document',
    idf_json JSON COMMENT 'IDF values',
    tfidf_training_json JSON COMMENT 'TF-IDF values for training',
    tfidf_job_json JSON COMMENT 'TF-IDF values for job',
    
    -- Final similarity
    cosine_similarity DECIMAL(10,8) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    INDEX idx_experiment (experiment_id),
    INDEX idx_similarity (cosine_similarity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 4: similarity_matrix
-- Purpose: Store all similarity scores for analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS similarity_matrix (
    similarity_id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_id INT NOT NULL,
    training_index INT NOT NULL,
    training_name VARCHAR(500),
    job_index INT NOT NULL,
    job_name VARCHAR(500),
    similarity_score DECIMAL(10,8) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    INDEX idx_experiment (experiment_id),
    INDEX idx_training (training_index),
    INDEX idx_job (job_index),
    INDEX idx_score (similarity_score DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 5: recommendations
-- Purpose: Store final recommendations for each job position
-- ============================================================================
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_id INT NOT NULL,
    job_index INT NOT NULL,
    job_name VARCHAR(500),
    training_index INT NOT NULL,
    training_name VARCHAR(500),
    rank_position INT NOT NULL,
    similarity_score DECIMAL(10,8) NOT NULL,
    similarity_percentage DECIMAL(5,2) NOT NULL,
    match_level ENUM('excellent', 'very_good', 'good', 'fair', 'weak') NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    INDEX idx_experiment (experiment_id),
    INDEX idx_job (job_index),
    INDEX idx_rank (rank_position),
    INDEX idx_match_level (match_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 6: statistics
-- Purpose: Store dataset statistics for thesis analysis chapter
-- ============================================================================
CREATE TABLE IF NOT EXISTS statistics (
    stat_id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_id INT NOT NULL,
    dataset_type ENUM('training', 'job') NOT NULL,
    
    -- Statistics
    total_records INT NOT NULL,
    avg_tokens DECIMAL(10,2),
    min_tokens INT,
    max_tokens INT,
    median_tokens DECIMAL(10,2),
    std_dev_tokens DECIMAL(10,2),
    
    -- Additional metrics
    total_unique_terms INT,
    avg_similarity_score DECIMAL(10,8),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    INDEX idx_experiment (experiment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- VIEWS: Useful queries for thesis analysis
-- ============================================================================

-- View: Summary of all experiments
CREATE OR REPLACE VIEW v_experiment_summary AS
SELECT 
    e.experiment_id,
    e.experiment_name,
    e.created_at,
    e.completed_at,
    e.status,
    e.dataset_training_count,
    e.dataset_job_count,
    COUNT(DISTINCT r.recommendation_id) as total_recommendations,
    AVG(r.similarity_score) as avg_similarity
FROM experiments e
LEFT JOIN recommendations r ON e.experiment_id = r.experiment_id
GROUP BY e.experiment_id;

-- View: Top recommendations per job
CREATE OR REPLACE VIEW v_top_recommendations AS
SELECT 
    r.experiment_id,
    r.job_name,
    r.training_name,
    r.rank_position,
    r.similarity_score,
    r.similarity_percentage,
    r.match_level
FROM recommendations r
WHERE r.rank_position <= 5
ORDER BY r.experiment_id, r.job_index, r.rank_position;

-- View: Preprocessing statistics
CREATE OR REPLACE VIEW v_preprocessing_stats AS
SELECT 
    ps.experiment_id,
    ps.dataset_type,
    COUNT(*) as sample_count,
    AVG(ps.token_count) as avg_tokens,
    MIN(ps.token_count) as min_tokens,
    MAX(ps.token_count) as max_tokens
FROM preprocessing_samples ps
GROUP BY ps.experiment_id, ps.dataset_type;

-- ============================================================================
-- STORED PROCEDURES: Helper functions for common operations
-- ============================================================================

DELIMITER //

-- Procedure: Create new experiment
CREATE PROCEDURE sp_create_experiment(
    IN p_name VARCHAR(255),
    IN p_description TEXT,
    IN p_training_count INT,
    IN p_job_count INT,
    OUT p_experiment_id INT
)
BEGIN
    INSERT INTO experiments (
        experiment_name, 
        description, 
        dataset_training_count, 
        dataset_job_count
    ) VALUES (
        p_name, 
        p_description, 
        p_training_count, 
        p_job_count
    );
    
    SET p_experiment_id = LAST_INSERT_ID();
END //

-- Procedure: Complete experiment
CREATE PROCEDURE sp_complete_experiment(
    IN p_experiment_id INT
)
BEGIN
    UPDATE experiments 
    SET status = 'completed',
        completed_at = CURRENT_TIMESTAMP
    WHERE experiment_id = p_experiment_id;
END //

-- Procedure: Get experiment statistics
CREATE PROCEDURE sp_get_experiment_stats(
    IN p_experiment_id INT
)
BEGIN
    SELECT 
        e.experiment_name,
        e.dataset_training_count,
        e.dataset_job_count,
        COUNT(DISTINCT r.recommendation_id) as total_recommendations,
        AVG(r.similarity_score) as avg_similarity,
        MAX(r.similarity_score) as max_similarity,
        MIN(r.similarity_score) as min_similarity,
        COUNT(DISTINCT CASE WHEN r.match_level = 'excellent' THEN r.recommendation_id END) as excellent_matches,
        COUNT(DISTINCT CASE WHEN r.match_level = 'very_good' THEN r.recommendation_id END) as very_good_matches,
        COUNT(DISTINCT CASE WHEN r.match_level = 'good' THEN r.recommendation_id END) as good_matches
    FROM experiments e
    LEFT JOIN recommendations r ON e.experiment_id = r.experiment_id
    WHERE e.experiment_id = p_experiment_id
    GROUP BY e.experiment_id;
END //

DELIMITER ;

-- ============================================================================
-- SAMPLE DATA: For testing (optional)
-- ============================================================================

-- Insert a sample experiment
INSERT INTO experiments (
    experiment_name, 
    description, 
    dataset_training_count, 
    dataset_job_count,
    status
) VALUES (
    'Initial Test Run',
    'First test of the matching system for thesis development',
    50,
    30,
    'completed'
);

-- ============================================================================
-- USEFUL QUERIES FOR THESIS
-- ============================================================================

-- Query 1: Get all recommendations for a specific experiment
-- SELECT * FROM recommendations WHERE experiment_id = 1 ORDER BY job_index, rank_position;

-- Query 2: Get preprocessing examples for methodology chapter
-- SELECT * FROM preprocessing_samples WHERE experiment_id = 1 LIMIT 10;

-- Query 3: Get TF-IDF calculation examples
-- SELECT * FROM tfidf_calculations WHERE experiment_id = 1 LIMIT 5;

-- Query 4: Get match level distribution (for thesis charts)
-- SELECT match_level, COUNT(*) as count 
-- FROM recommendations 
-- WHERE experiment_id = 1 
-- GROUP BY match_level;

-- Query 5: Get similarity score distribution
-- SELECT 
--     CASE 
--         WHEN similarity_score >= 0.80 THEN '0.80-1.00'
--         WHEN similarity_score >= 0.65 THEN '0.65-0.79'
--         WHEN similarity_score >= 0.50 THEN '0.50-0.64'
--         WHEN similarity_score >= 0.35 THEN '0.35-0.49'
--         ELSE '0.00-0.34'
--     END as score_range,
--     COUNT(*) as count
-- FROM recommendations
-- WHERE experiment_id = 1
-- GROUP BY score_range
-- ORDER BY score_range DESC;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Grant privileges (adjust username/password as needed)
-- CREATE USER IF NOT EXISTS 'bbpvp_user'@'localhost' IDENTIFIED BY 'your_password_here';
-- GRANT ALL PRIVILEGES ON bbpvp_thesis.* TO 'bbpvp_user'@'localhost';
-- FLUSH PRIVILEGES;

SELECT 'Database schema created successfully!' as Status;