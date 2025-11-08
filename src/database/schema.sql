-- Quiz System Database Schema
-- This script creates the complete database structure for the Online Quiz System

-- Create database
CREATE DATABASE IF NOT EXISTS quiz_system;
USE quiz_system;

-- Users table for authentication and user management
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role ENUM('student', 'admin') DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Subjects/Categories for organizing questions
CREATE TABLE subjects (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL,
    subject_code VARCHAR(10) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Questions bank with difficulty levels
CREATE TABLE questions (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    question_text TEXT NOT NULL,
    difficulty ENUM('Easy', 'Medium', 'Hard') NOT NULL,
    points INT DEFAULT 1,
    explanation TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Multiple choice options for questions
CREATE TABLE question_options (
    option_id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    option_order INT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

-- Quizzes/Exams configuration
CREATE TABLE quizzes (
    quiz_id INT AUTO_INCREMENT PRIMARY KEY,
    quiz_title VARCHAR(200) NOT NULL,
    quiz_description TEXT,
    subject_id INT NOT NULL,
    total_questions INT NOT NULL,
    time_limit INT NOT NULL, -- in minutes
    difficulty_mix JSON, -- JSON object storing Easy:Medium:Hard ratio
    passing_score INT DEFAULT 60, -- percentage
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Quiz-Question mapping (for dynamic quiz generation)
CREATE TABLE quiz_questions (
    quiz_question_id INT AUTO_INCREMENT PRIMARY KEY,
    quiz_id INT NOT NULL,
    question_id INT NOT NULL,
    question_order INT NOT NULL,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    UNIQUE KEY unique_quiz_question (quiz_id, question_id)
);

-- Quiz attempts by students
CREATE TABLE quiz_attempts (
    attempt_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    quiz_id INT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    total_score INT DEFAULT 0,
    max_possible_score INT NOT NULL,
    percentage DECIMAL(5,2) DEFAULT 0.00,
    time_taken INT DEFAULT 0, -- in seconds
    status ENUM('in_progress', 'completed', 'abandoned') DEFAULT 'in_progress',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
);

-- Individual question responses
CREATE TABLE question_responses (
    response_id INT AUTO_INCREMENT PRIMARY KEY,
    attempt_id INT NOT NULL,
    question_id INT NOT NULL,
    selected_option_id INT,
    is_correct BOOLEAN DEFAULT FALSE,
    points_earned INT DEFAULT 0,
    time_spent INT DEFAULT 0, -- in seconds
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(attempt_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    FOREIGN KEY (selected_option_id) REFERENCES question_options(option_id),
    UNIQUE KEY unique_attempt_question (attempt_id, question_id)
);

-- Performance analytics cache table
CREATE TABLE performance_analytics (
    analytics_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subject_id INT,
    difficulty_level ENUM('Easy', 'Medium', 'Hard'),
    total_questions INT DEFAULT 0,
    correct_answers INT DEFAULT 0,
    accuracy_percentage DECIMAL(5,2) DEFAULT 0.00,
    avg_time_per_question DECIMAL(8,2) DEFAULT 0.00,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
    UNIQUE KEY unique_user_subject_difficulty (user_id, subject_id, difficulty_level)
);

-- Question effectiveness analytics
CREATE TABLE question_analytics (
    question_id INT PRIMARY KEY,
    total_attempts INT DEFAULT 0,
    correct_attempts INT DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    avg_time_spent DECIMAL(8,2) DEFAULT 0.00,
    difficulty_validation ENUM('Too Easy', 'Appropriate', 'Too Hard', 'Needs Review') DEFAULT 'Needs Review',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

-- Indexes for better performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_questions_subject ON questions(subject_id);
CREATE INDEX idx_questions_difficulty ON questions(difficulty);
CREATE INDEX idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX idx_question_responses_attempt ON question_responses(attempt_id);
CREATE INDEX idx_question_responses_question ON question_responses(question_id);
CREATE INDEX idx_performance_analytics_user ON performance_analytics(user_id);

-- Views for common queries
-- Student performance summary view
CREATE VIEW student_performance_summary AS
SELECT 
    u.user_id,
    u.username,
    u.first_name,
    u.last_name,
    COUNT(qa.attempt_id) as total_attempts,
    AVG(qa.percentage) as avg_percentage,
    MAX(qa.percentage) as best_score,
    MIN(qa.percentage) as lowest_score,
    AVG(qa.time_taken) as avg_time_taken
FROM users u
LEFT JOIN quiz_attempts qa ON u.user_id = qa.user_id
WHERE u.role = 'student' AND qa.status = 'completed'
GROUP BY u.user_id;

-- Question difficulty analysis view
CREATE VIEW question_difficulty_analysis AS
SELECT 
    q.question_id,
    q.question_text,
    q.difficulty,
    s.subject_name,
    qa_stats.total_attempts,
    qa_stats.success_rate,
    CASE 
        WHEN q.difficulty = 'Easy' AND qa_stats.success_rate < 70 THEN 'Too Hard'
        WHEN q.difficulty = 'Medium' AND qa_stats.success_rate < 50 THEN 'Too Hard'
        WHEN q.difficulty = 'Hard' AND qa_stats.success_rate < 30 THEN 'Too Hard'
        WHEN q.difficulty = 'Easy' AND qa_stats.success_rate > 90 THEN 'Too Easy'
        WHEN q.difficulty = 'Medium' AND qa_stats.success_rate > 80 THEN 'Too Easy'
        WHEN q.difficulty = 'Hard' AND qa_stats.success_rate > 70 THEN 'Too Easy'
        ELSE 'Appropriate'
    END as difficulty_assessment
FROM questions q
JOIN subjects s ON q.subject_id = s.subject_id
LEFT JOIN question_analytics qa_stats ON q.question_id = qa_stats.question_id;

-- Subject-wise performance view
CREATE VIEW subject_performance AS
SELECT 
    s.subject_id,
    s.subject_name,
    COUNT(DISTINCT qa.user_id) as students_attempted,
    COUNT(qa.attempt_id) as total_attempts,
    AVG(qa.percentage) as avg_performance,
    COUNT(CASE WHEN qa.percentage >= 80 THEN 1 END) as excellent_scores,
    COUNT(CASE WHEN qa.percentage >= 60 AND qa.percentage < 80 THEN 1 END) as good_scores,
    COUNT(CASE WHEN qa.percentage < 60 THEN 1 END) as needs_improvement
FROM subjects s
LEFT JOIN quizzes qz ON s.subject_id = qz.subject_id
LEFT JOIN quiz_attempts qa ON qz.quiz_id = qa.quiz_id
WHERE qa.status = 'completed'
GROUP BY s.subject_id;