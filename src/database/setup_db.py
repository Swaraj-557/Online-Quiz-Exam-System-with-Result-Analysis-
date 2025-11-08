#!/usr/bin/env python3
"""
Database setup and initialization script for Quiz System
This script creates the database, tables, and populates with sample data
"""

import mysql.connector
from mysql.connector import Error
import os
import sys
import hashlib
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import get_db_config

def create_password_hash(password: str) -> str:
    """Create a simple password hash (use proper hashing in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

def execute_sql_file(cursor, file_path: str):
    """Execute SQL commands from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                cursor.execute(statement)
        
        print(f"✅ Successfully executed SQL file: {file_path}")
        
    except Exception as e:
        print(f"❌ Error executing SQL file {file_path}: {e}")
        raise

def setup_database():
    """Create database and execute schema"""
    config = get_db_config()
    
    # Connect without specifying database to create it
    initial_config = config.copy()
    initial_config.pop('database', None)
    
    try:
        # Create database connection
        connection = mysql.connector.connect(**initial_config)
        cursor = connection.cursor()
        
        print("🔧 Setting up Quiz System Database...")
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']}")
        cursor.execute(f"USE {config['database']}")
        print(f"✅ Database '{config['database']}' created/verified")
        
        # Execute schema file
        schema_path = Path(__file__).parent / 'schema.sql'
        execute_sql_file(cursor, schema_path)
        
        connection.commit()
        print("✅ Database schema created successfully")
        
        return connection, cursor
        
    except Error as e:
        print(f"❌ Error setting up database: {e}")
        raise

def populate_sample_data(connection, cursor):
    """Populate database with sample data"""
    print("\n📊 Populating sample data...")
    
    try:
        # Create subjects
        subjects_data = [
            ('Computer Science', 'CS101', 'Fundamentals of Computer Science'),
            ('Mathematics', 'MATH101', 'Basic Mathematics and Statistics'),
            ('Physics', 'PHY101', 'Introduction to Physics'),
            ('English', 'ENG101', 'English Language and Literature'),
            ('History', 'HIST101', 'World History'),
        ]
        
        subject_query = """
        INSERT INTO subjects (subject_name, subject_code, description) 
        VALUES (%s, %s, %s)
        """
        cursor.executemany(subject_query, subjects_data)
        print("✅ Sample subjects created")
        
        # Create admin user
        admin_data = (
            'admin', 'admin@quizsystem.com', 
            create_password_hash('admin123'), 
            'System', 'Administrator', 'admin'
        )
        
        admin_query = """
        INSERT INTO users (username, email, password_hash, first_name, last_name, role)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(admin_query, admin_data)
        admin_id = cursor.lastrowid
        print("✅ Admin user created (username: admin, password: admin123)")
        
        # Create sample students
        students_data = [
            ('john_doe', 'john@example.com', create_password_hash('student123'), 'John', 'Doe', 'student'),
            ('jane_smith', 'jane@example.com', create_password_hash('student123'), 'Jane', 'Smith', 'student'),
            ('bob_wilson', 'bob@example.com', create_password_hash('student123'), 'Bob', 'Wilson', 'student'),
            ('alice_brown', 'alice@example.com', create_password_hash('student123'), 'Alice', 'Brown', 'student'),
            ('charlie_davis', 'charlie@example.com', create_password_hash('student123'), 'Charlie', 'Davis', 'student'),
        ]
        
        student_query = """
        INSERT INTO users (username, email, password_hash, first_name, last_name, role)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(student_query, students_data)
        print("✅ Sample students created (password: student123 for all)")
        
        # Get subject IDs for creating questions
        cursor.execute("SELECT subject_id, subject_name FROM subjects")
        subjects = {name: sid for sid, name in cursor.fetchall()}
        
        # Computer Science Questions
        cs_questions = [
            # Easy Questions
            {
                'subject_id': subjects['Computer Science'],
                'question_text': 'What does CPU stand for?',
                'difficulty': 'Easy',
                'options': [
                    {'text': 'Central Processing Unit', 'is_correct': True},
                    {'text': 'Computer Personal Unit', 'is_correct': False},
                    {'text': 'Central Program Unit', 'is_correct': False},
                    {'text': 'Computer Processing Unit', 'is_correct': False}
                ]
            },
            {
                'subject_id': subjects['Computer Science'],
                'question_text': 'Which of the following is a programming language?',
                'difficulty': 'Easy',
                'options': [
                    {'text': 'HTML', 'is_correct': False},
                    {'text': 'Python', 'is_correct': True},
                    {'text': 'CSS', 'is_correct': False},
                    {'text': 'HTTP', 'is_correct': False}
                ]
            },
            # Medium Questions
            {
                'subject_id': subjects['Computer Science'],
                'question_text': 'What is the time complexity of binary search?',
                'difficulty': 'Medium',
                'options': [
                    {'text': 'O(n)', 'is_correct': False},
                    {'text': 'O(log n)', 'is_correct': True},
                    {'text': 'O(n²)', 'is_correct': False},
                    {'text': 'O(1)', 'is_correct': False}
                ]
            },
            {
                'subject_id': subjects['Computer Science'],
                'question_text': 'Which data structure uses LIFO principle?',
                'difficulty': 'Medium',
                'options': [
                    {'text': 'Queue', 'is_correct': False},
                    {'text': 'Array', 'is_correct': False},
                    {'text': 'Stack', 'is_correct': True},
                    {'text': 'Linked List', 'is_correct': False}
                ]
            },
            # Hard Questions
            {
                'subject_id': subjects['Computer Science'],
                'question_text': 'In object-oriented programming, what is polymorphism?',
                'difficulty': 'Hard',
                'options': [
                    {'text': 'Having multiple constructors', 'is_correct': False},
                    {'text': 'Ability of objects to take multiple forms', 'is_correct': True},
                    {'text': 'Creating multiple objects', 'is_correct': False},
                    {'text': 'Inheriting from multiple classes', 'is_correct': False}
                ]
            }
        ]
        
        # Mathematics Questions
        math_questions = [
            # Easy Questions
            {
                'subject_id': subjects['Mathematics'],
                'question_text': 'What is 15 + 27?',
                'difficulty': 'Easy',
                'options': [
                    {'text': '42', 'is_correct': True},
                    {'text': '41', 'is_correct': False},
                    {'text': '43', 'is_correct': False},
                    {'text': '40', 'is_correct': False}
                ]
            },
            {
                'subject_id': subjects['Mathematics'],
                'question_text': 'What is the square root of 64?',
                'difficulty': 'Easy',
                'options': [
                    {'text': '6', 'is_correct': False},
                    {'text': '8', 'is_correct': True},
                    {'text': '7', 'is_correct': False},
                    {'text': '9', 'is_correct': False}
                ]
            },
            # Medium Questions
            {
                'subject_id': subjects['Mathematics'],
                'question_text': 'What is the derivative of x²?',
                'difficulty': 'Medium',
                'options': [
                    {'text': 'x', 'is_correct': False},
                    {'text': '2x', 'is_correct': True},
                    {'text': 'x²', 'is_correct': False},
                    {'text': '2x²', 'is_correct': False}
                ]
            },
            {
                'subject_id': subjects['Mathematics'],
                'question_text': 'In a right triangle, what is sin(90°)?',
                'difficulty': 'Medium',
                'options': [
                    {'text': '0', 'is_correct': False},
                    {'text': '1', 'is_correct': True},
                    {'text': '0.5', 'is_correct': False},
                    {'text': 'undefined', 'is_correct': False}
                ]
            },
            # Hard Questions
            {
                'subject_id': subjects['Mathematics'],
                'question_text': 'What is the integral of 1/x dx?',
                'difficulty': 'Hard',
                'options': [
                    {'text': 'x + C', 'is_correct': False},
                    {'text': 'ln|x| + C', 'is_correct': True},
                    {'text': 'x²/2 + C', 'is_correct': False},
                    {'text': '1/x² + C', 'is_correct': False}
                ]
            }
        ]
        
        # Physics Questions
        physics_questions = [
            # Easy Questions
            {
                'subject_id': subjects['Physics'],
                'question_text': 'What is the unit of force?',
                'difficulty': 'Easy',
                'options': [
                    {'text': 'Joule', 'is_correct': False},
                    {'text': 'Newton', 'is_correct': True},
                    {'text': 'Watt', 'is_correct': False},
                    {'text': 'Pascal', 'is_correct': False}
                ]
            },
            # Medium Questions
            {
                'subject_id': subjects['Physics'],
                'question_text': 'What is the acceleration due to gravity on Earth?',
                'difficulty': 'Medium',
                'options': [
                    {'text': '9.8 m/s²', 'is_correct': True},
                    {'text': '10 m/s²', 'is_correct': False},
                    {'text': '9.6 m/s²', 'is_correct': False},
                    {'text': '8.9 m/s²', 'is_correct': False}
                ]
            },
            # Hard Questions
            {
                'subject_id': subjects['Physics'],
                'question_text': 'According to Einstein\'s theory, what is the relationship between mass and energy?',
                'difficulty': 'Hard',
                'options': [
                    {'text': 'E = mc', 'is_correct': False},
                    {'text': 'E = mc²', 'is_correct': True},
                    {'text': 'E = m²c', 'is_correct': False},
                    {'text': 'E = m/c²', 'is_correct': False}
                ]
            }
        ]
        
        # Insert all questions
        all_questions = cs_questions + math_questions + physics_questions
        
        for question_data in all_questions:
            # Insert question
            question_query = """
            INSERT INTO questions (subject_id, question_text, difficulty, points, created_by)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(question_query, (
                question_data['subject_id'],
                question_data['question_text'],
                question_data['difficulty'],
                1,  # points
                admin_id
            ))
            question_id = cursor.lastrowid
            
            # Insert options
            for i, option in enumerate(question_data['options'], 1):
                option_query = """
                INSERT INTO question_options (question_id, option_text, is_correct, option_order)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(option_query, (
                    question_id,
                    option['text'],
                    option['is_correct'],
                    i
                ))
        
        print("✅ Sample questions created")
        
        # Create sample quizzes
        quizzes_data = [
            {
                'title': 'Computer Science Basics',
                'description': 'Test your knowledge of basic computer science concepts',
                'subject_id': subjects['Computer Science'],
                'total_questions': 5,
                'time_limit': 30,
                'difficulty_mix': {'Easy': 2, 'Medium': 2, 'Hard': 1},
                'created_by': admin_id
            },
            {
                'title': 'Mathematics Fundamentals',
                'description': 'Basic mathematics quiz covering algebra and calculus',
                'subject_id': subjects['Mathematics'],
                'total_questions': 5,
                'time_limit': 25,
                'difficulty_mix': {'Easy': 2, 'Medium': 2, 'Hard': 1},
                'created_by': admin_id
            },
            {
                'title': 'Physics Essentials',
                'description': 'Essential physics concepts and formulas',
                'subject_id': subjects['Physics'],
                'total_questions': 3,
                'time_limit': 20,
                'difficulty_mix': {'Easy': 1, 'Medium': 1, 'Hard': 1},
                'created_by': admin_id
            }
        ]
        
        for quiz in quizzes_data:
            quiz_query = """
            INSERT INTO quizzes (quiz_title, quiz_description, subject_id, total_questions,
                               time_limit, difficulty_mix, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(quiz_query, (
                quiz['title'],
                quiz['description'],
                quiz['subject_id'],
                quiz['total_questions'],
                quiz['time_limit'],
                json.dumps(quiz['difficulty_mix']),
                quiz['created_by']
            ))
        
        print("✅ Sample quizzes created")
        
        connection.commit()
        print("\n🎉 Sample data population completed successfully!")
        
    except Exception as e:
        print(f"❌ Error populating sample data: {e}")
        connection.rollback()
        raise

def main():
    """Main setup function"""
    print("🚀 Quiz System Database Setup")
    print("=" * 50)
    
    try:
        # Setup database and schema
        connection, cursor = setup_database()
        
        # Populate with sample data
        populate_sample_data(connection, cursor)
        
        print("\n" + "=" * 50)
        print("✅ Database setup completed successfully!")
        print("\n📋 Login Credentials:")
        print("   Admin: username=admin, password=admin123")
        print("   Students: password=student123 for all sample students")
        print("\n🌐 You can now start the web application!")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()