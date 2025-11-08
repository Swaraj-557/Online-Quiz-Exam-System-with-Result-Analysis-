"""
Result analysis utilities for the quiz system.

Functions:
- student_proficiency_on_hard(db, user_id) -> percentage of correct Hard questions
- question_effectiveness(db, question_id) -> dict with total, correct, wrong_percent
- top_poor_questions(db, limit=10) -> list of poorest performing questions
"""
from typing import Optional, List, Dict


def student_proficiency_on_hard(quiz_db, user_id: int) -> Optional[float]:
    """Return percentage correct on questions labeled 'Hard' for the given user.

    Returns None if user has not attempted any Hard questions.
    """
    query = """
    SELECT
        COUNT(*) AS total_hard,
        SUM(qr.is_correct) AS correct_hard
    FROM question_responses qr
    JOIN questions q ON qr.question_id = q.question_id
    JOIN quiz_attempts qa ON qr.attempt_id = qa.attempt_id
    WHERE qa.user_id = %s AND qa.status = 'completed' AND q.difficulty = 'Hard'
    """
    row = quiz_db.db.execute_query(query, (user_id,), fetch_one=True)
    if not row or row['total_hard'] == 0:
        return None
    correct = row['correct_hard'] or 0
    total = row['total_hard']
    return (correct / total) * 100.0


def question_effectiveness(quiz_db, question_id: int) -> Optional[Dict]:
    """Return effectiveness metrics for a single question.

    Returns None if there are no attempts for the question.
    """
    query = """
    SELECT COUNT(*) AS total_attempts, SUM(is_correct) AS correct_attempts
    FROM question_responses
    WHERE question_id = %s
    """
    row = quiz_db.db.execute_query(query, (question_id,), fetch_one=True)
    if not row or row['total_attempts'] == 0:
        return None
    total = row['total_attempts']
    correct = row['correct_attempts'] or 0
    wrong = total - correct
    wrong_percent = (wrong / total) * 100.0
    success_rate = (correct / total) * 100.0
    return {
        'question_id': question_id,
        'total_attempts': total,
        'correct_attempts': correct,
        'wrong_attempts': wrong,
        'wrong_percent': wrong_percent,
        'success_rate': success_rate
    }


def top_poor_questions(quiz_db, limit: int = 10) -> List[Dict]:
    """Return questions sorted by highest wrong percentage (descending).
    Only questions with at least one attempt are considered.
    """
    query = """
    SELECT
        q.question_id,
        q.question_text,
        q.difficulty,
        COUNT(qr.response_id) AS total_attempts,
        SUM(qr.is_correct) AS correct_attempts,
        (1 - SUM(qr.is_correct)/COUNT(qr.response_id)) * 100 AS wrong_percent
    FROM questions q
    JOIN question_responses qr ON q.question_id = qr.question_id
    GROUP BY q.question_id
    HAVING total_attempts > 0
    ORDER BY wrong_percent DESC
    LIMIT %s
    """
    rows = quiz_db.db.execute_query(query, (limit,))
    results = []
    for r in rows:
        results.append({
            'question_id': r['question_id'],
            'question_text': r['question_text'],
            'difficulty': r['difficulty'],
            'total_attempts': r['total_attempts'],
            'correct_attempts': r['correct_attempts'],
            'wrong_percent': float(r['wrong_percent']) if r.get('wrong_percent') is not None else None
        })
    return results
