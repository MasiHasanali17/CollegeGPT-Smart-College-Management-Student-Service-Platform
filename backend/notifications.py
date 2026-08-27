"""
notifications.py

In-app notifications for students (the bell icon). Scoped to genuinely
actionable, personal events — hostel transfer status changes, grievance
status changes, and academic record updates — rather than broadcasting
every notice to every student as a row (which wouldn't scale and isn't
needed; notices already have their own dedicated feed page).

Standalone — no chatbot dependency.
"""

from database import get_connection


def create_notification(student_id, message, link=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO notifications (student_id, message, link) VALUES (?, ?, ?)",
        (student_id, message, link)
    )
    conn.commit()
    conn.close()


def list_notifications(student_id, limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE student_id = ? ORDER BY created_at DESC LIMIT ?",
        (student_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def unread_count(student_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM notifications WHERE student_id = ? AND is_read = 0",
        (student_id,)
    ).fetchone()
    conn.close()
    return row["c"]


def mark_read(notification_id, student_id):
    """student_id passed too, so a student can only mark their OWN notifications read."""
    conn = get_connection()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND student_id = ?",
        (notification_id, student_id)
    )
    conn.commit()
    conn.close()


def mark_all_read(student_id):
    conn = get_connection()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE student_id = ?",
        (student_id,)
    )
    conn.commit()
    conn.close()
