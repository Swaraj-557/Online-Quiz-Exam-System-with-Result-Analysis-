"""
Database connection and management module for Quiz System
"""
import mysql.connector
from mysql.connector import Error
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
import os
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Centralized database manager for the Quiz System
    Handles connections, transactions, and common database operations
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database manager with configuration
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self.connection_pool = None
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Initialize MySQL connection pool"""
        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="quiz_system_pool",
                pool_size=10,
                pool_reset_session=True,
                **self.config
            )
            logger.info("Database connection pool initialized successfully")
        except Error as e:
            logger.error(f"Error creating connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        
        Yields:
            MySQL connection object
        """
        connection = None
        try:
            connection = self.connection_pool.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    @contextmanager
    def get_cursor(self, dictionary=True):
        """
        Context manager for database cursor with automatic connection management
        
        Args:
            dictionary: Return results as dictionaries if True
            
        Yields:
            Tuple of (connection, cursor)
        """
        with self.get_connection() as connection:
            cursor = connection.cursor(dictionary=dictionary)
            try:
                yield connection, cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Tuple = None, fetch_one: bool = False) -> Any:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return single row if True, all rows if False
            
        Returns:
            Query results
        """
        try:
            with self.get_cursor() as (connection, cursor):
                cursor.execute(query, params or ())
                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()
        except Error as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def execute_update(self, query: str, params: Tuple = None) -> int:
        """
        Execute INSERT, UPDATE, or DELETE query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        try:
            with self.get_cursor() as (connection, cursor):
                cursor.execute(query, params or ())
                connection.commit()
                return cursor.rowcount
        except Error as e:
            logger.error(f"Update execution error: {e}")
            raise
    
    def execute_insert(self, query: str, params: Tuple = None) -> int:
        """
        Execute INSERT query and return last insert ID
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Last inserted row ID
        """
        try:
            with self.get_cursor() as (connection, cursor):
                cursor.execute(query, params or ())
                connection.commit()
                return cursor.lastrowid
        except Error as e:
            logger.error(f"Insert execution error: {e}")
            raise
    
    def execute_transaction(self, queries: List[Tuple[str, Tuple]]) -> bool:
        """
        Execute multiple queries in a transaction
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            True if transaction successful, False otherwise
        """
        try:
            with self.get_cursor() as (connection, cursor):
                connection.start_transaction()
                for query, params in queries:
                    cursor.execute(query, params or ())
                connection.commit()
                return True
        except Error as e:
            logger.error(f"Transaction error: {e}")
            connection.rollback()
            return False
    
    def check_connection(self) -> bool:
        """
        Check if database connection is working
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            with self.get_cursor() as (connection, cursor):
                cursor.execute("SELECT 1")
                return True
        except Error:
            return False

class QuizDatabase:
    """
    Quiz-specific database operations
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    # User management methods
    def create_user(self, username: str, email: str, password_hash: str, 
                   first_name: str, last_name: str, role: str = 'student') -> int:
        """Create a new user"""
        query = """
        INSERT INTO users (username, email, password_hash, first_name, last_name, role)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(query, (username, email, password_hash, 
                                            first_name, last_name, role))
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = %s AND is_active = TRUE"
        return self.db.execute_query(query, (username,), fetch_one=True)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE user_id = %s AND is_active = TRUE"
        return self.db.execute_query(query, (user_id,), fetch_one=True)
    
    # Subject management methods
    def create_subject(self, subject_name: str, subject_code: str, 
                      description: str = None) -> int:
        """Create a new subject"""
        query = """
        INSERT INTO subjects (subject_name, subject_code, description)
        VALUES (%s, %s, %s)
        """
        return self.db.execute_insert(query, (subject_name, subject_code, description))
    
    def get_all_subjects(self) -> List[Dict]:
        """Get all subjects"""
        query = "SELECT * FROM subjects ORDER BY subject_name"
        return self.db.execute_query(query)
    
    # Question management methods
    def create_question(self, subject_id: int, question_text: str, difficulty: str,
                       options: List[Dict], points: int = 1, explanation: str = None,
                       created_by: int = 1) -> int:
        """
        Create a new question with options
        
        Args:
            subject_id: Subject ID
            question_text: Question text
            difficulty: Easy, Medium, or Hard
            options: List of {'text': str, 'is_correct': bool} dictionaries
            points: Points for correct answer
            explanation: Optional explanation
            created_by: User ID who created the question
            
        Returns:
            Question ID
        """
        # Insert question
        question_query = """
        INSERT INTO questions (subject_id, question_text, difficulty, points, 
                             explanation, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        question_id = self.db.execute_insert(question_query, 
                                           (subject_id, question_text, difficulty,
                                            points, explanation, created_by))
        
        # Insert options
        for i, option in enumerate(options, 1):
            option_query = """
            INSERT INTO question_options (question_id, option_text, is_correct, option_order)
            VALUES (%s, %s, %s, %s)
            """
            self.db.execute_insert(option_query, 
                                 (question_id, option['text'], 
                                  option['is_correct'], i))
        
        return question_id
    
    def get_questions_by_subject(self, subject_id: int, difficulty: str = None,
                               limit: int = None) -> List[Dict]:
        """Get questions by subject and optional difficulty"""
        query = """
        SELECT q.*, s.subject_name,
               GROUP_CONCAT(
                   CONCAT(qo.option_id, ':', qo.option_text, ':', qo.is_correct)
                   ORDER BY qo.option_order
                   SEPARATOR '|'
               ) as options
        FROM questions q
        JOIN subjects s ON q.subject_id = s.subject_id
        LEFT JOIN question_options qo ON q.question_id = qo.question_id
        WHERE q.subject_id = %s AND q.is_active = TRUE
        """
        
        params = [subject_id]
        
        if difficulty:
            query += " AND q.difficulty = %s"
            params.append(difficulty)
        
        query += " GROUP BY q.question_id ORDER BY q.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        questions = self.db.execute_query(query, tuple(params))
        
        # Parse options for each question
        for question in questions:
            if question['options']:
                options = []
                for option_str in question['options'].split('|'):
                    option_id, option_text, is_correct = option_str.split(':', 2)
                    options.append({
                        'option_id': int(option_id),
                        'text': option_text,
                        'is_correct': bool(int(is_correct))
                    })
                question['parsed_options'] = options
            else:
                question['parsed_options'] = []
        
        return questions
    
    # Quiz management methods
    def create_quiz(self, quiz_title: str, quiz_description: str, subject_id: int,
                   total_questions: int, time_limit: int, difficulty_mix: Dict,
                   created_by: int, passing_score: int = 60) -> int:
        """Create a new quiz"""
        query = """
        INSERT INTO quizzes (quiz_title, quiz_description, subject_id, total_questions,
                           time_limit, difficulty_mix, passing_score, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(query, 
                                    (quiz_title, quiz_description, subject_id,
                                     total_questions, time_limit, 
                                     json.dumps(difficulty_mix), passing_score, created_by))
    
    def get_active_quizzes(self) -> List[Dict]:
        """Get all active quizzes"""
        query = """
        SELECT q.*, s.subject_name, u.username as created_by_name
        FROM quizzes q
        JOIN subjects s ON q.subject_id = s.subject_id
        JOIN users u ON q.created_by = u.user_id
        WHERE q.is_active = TRUE
        ORDER BY q.created_at DESC
        """
        return self.db.execute_query(query)
    
    # Quiz attempt methods
    def start_quiz_attempt(self, user_id: int, quiz_id: int) -> int:
        """Start a new quiz attempt"""
        # Get quiz info for max possible score
        quiz_query = "SELECT total_questions FROM quizzes WHERE quiz_id = %s"
        quiz_info = self.db.execute_query(quiz_query, (quiz_id,), fetch_one=True)
        
        if not quiz_info:
            raise ValueError("Quiz not found")
        
        max_score = quiz_info['total_questions']  # Assuming 1 point per question
        
        query = """
        INSERT INTO quiz_attempts (user_id, quiz_id, max_possible_score)
        VALUES (%s, %s, %s)
        """
        return self.db.execute_insert(query, (user_id, quiz_id, max_score))
    
    def submit_answer(self, attempt_id: int, question_id: int, selected_option_id: int,
                     time_spent: int = 0) -> bool:
        """Submit an answer for a question"""
        # Check if the selected option is correct
        option_query = """
        SELECT is_correct, qo.question_id, q.points
        FROM question_options qo
        JOIN questions q ON qo.question_id = q.question_id
        WHERE qo.option_id = %s
        """
        option_info = self.db.execute_query(option_query, (selected_option_id,), fetch_one=True)
        
        if not option_info:
            return False
        
        is_correct = option_info['is_correct']
        points_earned = option_info['points'] if is_correct else 0
        
        # Insert response
        response_query = """
        INSERT INTO question_responses 
        (attempt_id, question_id, selected_option_id, is_correct, points_earned, time_spent)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        selected_option_id = VALUES(selected_option_id),
        is_correct = VALUES(is_correct),
        points_earned = VALUES(points_earned),
        time_spent = VALUES(time_spent),
        answered_at = CURRENT_TIMESTAMP
        """
        
        return self.db.execute_update(response_query, 
                                    (attempt_id, question_id, selected_option_id,
                                     is_correct, points_earned, time_spent)) > 0
    
    def complete_quiz_attempt(self, attempt_id: int) -> Dict:
        """Complete quiz attempt and calculate final score"""
        # Calculate total score
        score_query = """
        SELECT SUM(points_earned) as total_score, COUNT(*) as questions_answered,
               SUM(time_spent) as total_time
        FROM question_responses
        WHERE attempt_id = %s
        """
        score_info = self.db.execute_query(score_query, (attempt_id,), fetch_one=True)
        
        if not score_info:
            return None
        
        total_score = score_info['total_score'] or 0
        total_time = score_info['total_time'] or 0
        
        # Get max possible score
        attempt_query = """
        SELECT max_possible_score FROM quiz_attempts WHERE attempt_id = %s
        """
        attempt_info = self.db.execute_query(attempt_query, (attempt_id,), fetch_one=True)
        max_score = attempt_info['max_possible_score']
        
        # Calculate percentage
        percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        # Update attempt record
        update_query = """
        UPDATE quiz_attempts 
        SET total_score = %s, percentage = %s, time_taken = %s,
            end_time = CURRENT_TIMESTAMP, status = 'completed'
        WHERE attempt_id = %s
        """
        self.db.execute_update(update_query, (total_score, percentage, total_time, attempt_id))
        
        return {
            'total_score': total_score,
            'max_possible_score': max_score,
            'percentage': percentage,
            'time_taken': total_time,
            'questions_answered': score_info['questions_answered']
        }
    
    # Analytics methods
    def get_student_performance(self, user_id: int) -> Dict:
        """Get comprehensive student performance data"""
        # Overall performance
        overall_query = """
        SELECT 
            COUNT(*) as total_attempts,
            AVG(percentage) as avg_percentage,
            MAX(percentage) as best_score,
            MIN(percentage) as lowest_score,
            AVG(time_taken) as avg_time
        FROM quiz_attempts
        WHERE user_id = %s AND status = 'completed'
        """
        overall = self.db.execute_query(overall_query, (user_id,), fetch_one=True)
        
        # Performance by difficulty
        difficulty_query = """
        SELECT 
            q.difficulty,
            COUNT(*) as questions_attempted,
            SUM(qr.is_correct) as correct_answers,
            AVG(qr.time_spent) as avg_time_per_question
        FROM question_responses qr
        JOIN questions q ON qr.question_id = q.question_id
        JOIN quiz_attempts qa ON qr.attempt_id = qa.attempt_id
        WHERE qa.user_id = %s AND qa.status = 'completed'
        GROUP BY q.difficulty
        """
        difficulty_stats = self.db.execute_query(difficulty_query, (user_id,))
        
        # Performance by subject
        subject_query = """
        SELECT 
            s.subject_name,
            COUNT(DISTINCT qa.attempt_id) as quiz_attempts,
            AVG(qa.percentage) as avg_percentage
        FROM quiz_attempts qa
        JOIN quizzes qz ON qa.quiz_id = qz.quiz_id
        JOIN subjects s ON qz.subject_id = s.subject_id
        WHERE qa.user_id = %s AND qa.status = 'completed'
        GROUP BY s.subject_id
        """
        subject_stats = self.db.execute_query(subject_query, (user_id,))
        
        return {
            'overall': overall,
            'by_difficulty': difficulty_stats,
            'by_subject': subject_stats
        }
    
    def get_question_effectiveness(self, question_id: int = None) -> List[Dict]:
        """Get question effectiveness analytics"""
        base_query = """
        SELECT 
            q.question_id,
            q.question_text,
            q.difficulty,
            s.subject_name,
            COUNT(qr.response_id) as total_attempts,
            SUM(qr.is_correct) as correct_attempts,
            (SUM(qr.is_correct) / COUNT(qr.response_id)) * 100 as success_rate,
            AVG(qr.time_spent) as avg_time_spent
        FROM questions q
        JOIN subjects s ON q.subject_id = s.subject_id
        LEFT JOIN question_responses qr ON q.question_id = qr.question_id
        WHERE q.is_active = TRUE
        """
        
        if question_id:
            base_query += " AND q.question_id = %s"
            params = (question_id,)
        else:
            params = ()
        
        base_query += """
        GROUP BY q.question_id
        HAVING COUNT(qr.response_id) > 0
        ORDER BY success_rate ASC
        """
        
        return self.db.execute_query(base_query, params)


def get_db_config():
    """Get database configuration from environment or config file"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'quiz_system'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'port': int(os.getenv('DB_PORT', 3306)),
        'charset': 'utf8mb4',
        'use_unicode': True,
        'autocommit': False
    }


# Global database manager instance
db_manager = None
quiz_db = None

def initialize_database():
    """Initialize global database instances"""
    global db_manager, quiz_db
    
    config = get_db_config()
    db_manager = DatabaseManager(config)
    quiz_db = QuizDatabase(db_manager)
    
    return db_manager, quiz_db

def get_database():
    """Get initialized database instances"""
    global db_manager, quiz_db
    
    if not db_manager or not quiz_db:
        return initialize_database()
    
    return db_manager, quiz_db