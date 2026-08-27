"""
auth.py

Student authentication: registration, login, session management.
Uses Flask-Login for session handling and Werkzeug for password hashing.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection


class Student(UserMixin):
    """Wraps a student DB row so Flask-Login can manage the session."""

    def __init__(self, row):
        self.id = str(row["id"])
        self.student_id = row["student_id"]
        self.name = row["name"]
        self.course = row["course"]


def get_student_by_id(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    return Student(row) if row else None


def get_student_by_student_id(student_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE student_id = ?",
        (student_id,)
    ).fetchone()
    conn.close()

    return row


SECURITY_QUESTIONS = [
    "What was the name of your first school?",
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "What was your childhood nickname?",
]


def register_student(student_id, name, password, course="",
                      security_question=None, security_answer=None):
    """
    Returns (success: bool, message: str)
    """

    existing = get_student_by_student_id(student_id)

    if existing:
        return False, "Student ID already registered."

    password_hash = generate_password_hash(password)
    answer_hash = (
        generate_password_hash(security_answer.strip().lower())
        if security_answer else None
    )

    conn = get_connection()
    conn.execute(
        "INSERT INTO students (student_id, name, password_hash, course, "
        "security_question, security_answer_hash) VALUES (?, ?, ?, ?, ?, ?)",
        (student_id, name, password_hash, course, security_question, answer_hash)
    )
    conn.commit()
    conn.close()

    return True, "Registered successfully."


def verify_login(student_id, password):
    """
    Returns a Student object if credentials are valid, else None.
    """

    row = get_student_by_student_id(student_id)

    if not row:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return Student(row)


def get_security_question(student_id):
    row = get_student_by_student_id(student_id)
    if not row or not row["security_question"]:
        return None
    return row["security_question"]


def reset_password_with_security_answer(student_id, answer, new_password):
    """
    Returns (success: bool, message: str)
    """

    row = get_student_by_student_id(student_id)

    if not row or not row["security_answer_hash"]:
        return False, "No security question set up for this account. Contact admin for help."

    if not check_password_hash(row["security_answer_hash"], answer.strip().lower()):
        return False, "That answer doesn't match our records."

    conn = get_connection()
    conn.execute(
        "UPDATE students SET password_hash = ? WHERE student_id = ?",
        (generate_password_hash(new_password), student_id)
    )
    conn.commit()
    conn.close()

    return True, "Password reset successfully. Please log in with your new password."


def admin_reset_student_password(student_id, new_password):
    """Used by admin/student-services staff to reset a student's password directly."""

    conn = get_connection()
    conn.execute(
        "UPDATE students SET password_hash = ? WHERE student_id = ?",
        (generate_password_hash(new_password), student_id)
    )
    conn.commit()
    conn.close()