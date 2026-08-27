"""
prospective.py

Data-access layer for the "non-student" (prospective student / Interface 1)
features: admission applications and contact messages.

This is completely separate from the chatbot (rag_pipeline.py, retrieval.py,
groq_client.py, cache.py, logger.py, analytics/*) — nothing here is imported
by, or imports from, those files except read-only lookups into the existing
analytics.course / analytics.admission modules for real course & admission
data (so numbers shown to prospective students match what the chatbot says).
"""

import random
import string

from database import get_connection


# ------------------------------------------------------------
# Admission applications
# ------------------------------------------------------------

def _generate_tracking_id():
    suffix = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    return f"PU-{suffix}"


def create_application(name, email, phone, course):
    """
    Creates a new admission application with a unique tracking ID
    and default status 'Received'. Returns the tracking ID.
    """

    conn = get_connection()

    # Guarantee uniqueness (astronomically unlikely to collide, but cheap to check)
    while True:
        tracking_id = _generate_tracking_id()
        existing = conn.execute(
            "SELECT 1 FROM applications WHERE tracking_id = ?",
            (tracking_id,)
        ).fetchone()
        if not existing:
            break

    conn.execute(
        "INSERT INTO applications (tracking_id, name, email, phone, course, status) "
        "VALUES (?, ?, ?, ?, ?, 'Received')",
        (tracking_id, name, email, phone, course)
    )
    conn.commit()
    conn.close()

    return tracking_id


def get_application(tracking_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM applications WHERE tracking_id = ?",
        (tracking_id.strip().upper(),)
    ).fetchone()
    conn.close()

    return dict(row) if row else None


def list_applications():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM applications ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


APPLICATION_STATUSES = [
    "Received",
    "Under Review",
    "Offer Letter Issued",
    "Admission Confirmed",
    "Rejected",
]


def update_application_status(tracking_id, status):
    if status not in APPLICATION_STATUSES:
        return False

    conn = get_connection()
    conn.execute(
        "UPDATE applications SET status = ? WHERE tracking_id = ?",
        (status, tracking_id.strip().upper())
    )
    conn.commit()
    conn.close()

    return True


# ------------------------------------------------------------
# Contact messages
# ------------------------------------------------------------

def save_contact_message(name, email, subject, message):
    conn = get_connection()
    conn.execute(
        "INSERT INTO contact_messages (name, email, subject, message) "
        "VALUES (?, ?, ?, ?)",
        (name, email, subject, message)
    )
    conn.commit()
    conn.close()


def list_contact_messages():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM contact_messages ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]
