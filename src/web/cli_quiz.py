#!/usr/bin/env python3
"""
Simple CLI quiz runner that uses the existing database layer.

Usage: python src/web/cli_quiz.py

This is a lightweight demo to take a quiz from the terminal and store the attempt.
"""
import time
import json
from src.database.db_manager import get_database


def select_quiz(quiz_db):
    quizzes = quiz_db.get_active_quizzes()
    if not quizzes:
        print("No active quizzes available.")
        return None

    print("Available quizzes:")
    for q in quizzes:
        print(f"{q['quiz_id']}: {q['quiz_title']} (Subject: {q['subject_name']})")

    while True:
        try:
            chosen = int(input("Enter quiz id to take (or 0 to cancel): ").strip())
            if chosen == 0:
                return None
            for q in quizzes:
                if q['quiz_id'] == chosen:
                    return q
            print("Invalid quiz id. Try again.")
        except ValueError:
            print("Please enter a valid number.")


def prompt_username(quiz_db):
    username = input("Enter your username (sample users exist from setup_db): ").strip()
    user = quiz_db.get_user_by_username(username)
    if not user:
        print("User not found or inactive. Please make sure the user exists.")
        return None
    return user


def assemble_questions(quiz):
    """Return a flat list of questions according to quiz difficulty mix."""
    db = quiz_db = None
    # We'll get a new db/quiz_db inside main where connection exists
    # This function kept for potential future expansion
    return []


def take_quiz(quiz_db, quiz, user):
    print(f"Starting quiz: {quiz['quiz_title']} for user {user['username']}")

    # Start attempt
    attempt_id = quiz_db.start_quiz_attempt(user['user_id'], quiz['quiz_id'])
    print(f"Attempt started (id={attempt_id}). Good luck!\n")

    # Determine questions by difficulty mix
    try:
        difficulty_mix = json.loads(quiz['difficulty_mix']) if quiz.get('difficulty_mix') else {}
    except Exception:
        # fallback if stored as string
        difficulty_mix = quiz.get('difficulty_mix') or {}

    questions = []
    # For each difficulty, fetch required number of questions
    for difficulty, count in difficulty_mix.items():
        if count <= 0:
            continue
        qs = quiz_db.get_questions_by_subject(quiz['subject_id'], difficulty=difficulty, limit=count)
        questions.extend(qs)

    # If difficulty mix didn't produce enough questions, fetch additional by subject
    if len(questions) < quiz['total_questions']:
        remaining = quiz['total_questions'] - len(questions)
        more = quiz_db.get_questions_by_subject(quiz['subject_id'], limit=remaining)
        # avoid duplicates
        existing_ids = {q['question_id'] for q in questions}
        for q in more:
            if q['question_id'] not in existing_ids:
                questions.append(q)
                if len(questions) >= quiz['total_questions']:
                    break

    # Present questions sequentially
    for idx, q in enumerate(questions, 1):
        print(f"Question {idx}/{len(questions)}: {q['question_text']}")
        options = q.get('parsed_options') or []
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt['text']}")

        # get user choice
        start = time.time()
        chosen = None
        while True:
            try:
                val = int(input("Your answer (enter option number, 0 to skip): ").strip())
                if val == 0:
                    chosen = None
                    break
                if 1 <= val <= len(options):
                    chosen = options[val - 1]
                    break
                print("Invalid choice. Try again.")
            except ValueError:
                print("Please enter a number.")

        time_spent = int(time.time() - start)

        selected_option_id = chosen['option_id'] if chosen else None
        if selected_option_id:
            quiz_db.submit_answer(attempt_id, q['question_id'], selected_option_id, time_spent)
        else:
            # insert a response with NULL selection (skip)
            quiz_db.submit_answer(attempt_id, q['question_id'], None, time_spent)

        print()

    # finalize
    result = quiz_db.complete_quiz_attempt(attempt_id)
    if result:
        print("\nQuiz completed!")
        print(f"Score: {result['total_score']} / {result['max_possible_score']}")
        print(f"Percentage: {result['percentage']:.2f}%")
        print(f"Time taken: {result['time_taken']} seconds")
    else:
        print("Error finalizing quiz attempt.")


def run_cli():
    db_manager, quiz_db = get_database()

    print("Welcome to the CLI Quiz Runner")

    user = prompt_username(quiz_db)
    if not user:
        return

    quiz = select_quiz(quiz_db)
    if not quiz:
        return

    take_quiz(quiz_db, quiz, user)


if __name__ == '__main__':
    run_cli()
