"""
portal.py

Data-access layer for the "current student" (Interface 2) features:
notices, activities (events / extra courses / sports & gym slots) with
booking + payment, hostel transfer requests, grievances, and academic
records.

Separate from the chatbot entirely. Also separate from prospective.py,
which handles the "not yet admitted" (Interface 1) side.
"""

import random
import string
import base64
from io import BytesIO

import qrcode

from database import get_connection


# ==============================================================
# Notices
# ==============================================================

def create_notice(title, category, description, expiry_date=None,
                   target_audience="All Students", attachment_filename=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO notices (title, category, description, expiry_date, "
        "target_audience, attachment_filename) VALUES (?, ?, ?, ?, ?, ?)",
        (title, category, description, expiry_date or None, target_audience, attachment_filename)
    )
    conn.commit()
    conn.close()


def list_notices(category=None, include_expired=False):
    """
    By default, hides notices whose expiry_date has already passed —
    students shouldn't see stale notices. Pass include_expired=True for
    the admin view, which needs to see everything.
    """
    from datetime import date

    conn = get_connection()
    if category and category != "All":
        rows = conn.execute(
            "SELECT * FROM notices WHERE category = ? ORDER BY created_at DESC",
            (category,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM notices ORDER BY created_at DESC"
        ).fetchall()
    conn.close()

    notices = [dict(r) for r in rows]

    if include_expired:
        return notices

    today = date.today().isoformat()
    return [n for n in notices if not n.get("expiry_date") or n["expiry_date"] >= today]


def delete_notice(notice_id):
    conn = get_connection()
    conn.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    conn.commit()
    conn.close()


# ==============================================================
# Activities (events / extra courses / facility slots) + bookings
# ==============================================================

KIND_PREFIX = {"event": "EVT", "course": "CRS", "facility": "FAC"}


def _generate_booking_ref(kind):
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    prefix = KIND_PREFIX.get(kind, "GEN")
    return f"PU-{prefix}-{suffix}"


def create_activity(kind, title, description, schedule_text, capacity, price=0):
    conn = get_connection()
    conn.execute(
        "INSERT INTO activities (kind, title, description, schedule_text, capacity, price) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (kind, title, description, schedule_text, capacity or 0, price or 0)
    )
    conn.commit()
    conn.close()


def delete_activity(activity_id):
    conn = get_connection()
    conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    conn.execute("DELETE FROM activity_bookings WHERE activity_id = ?", (activity_id,))
    conn.commit()
    conn.close()


def list_activities(kind):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM activities WHERE kind = ? ORDER BY created_at DESC",
        (kind,)
    ).fetchall()

    result = []
    for r in rows:
        row = dict(r)
        booked_count = conn.execute(
            "SELECT COUNT(*) as c FROM activity_bookings WHERE activity_id = ?",
            (row["id"],)
        ).fetchone()["c"]
        row["booked_count"] = booked_count
        row["is_full"] = bool(row["capacity"]) and booked_count >= row["capacity"]
        result.append(row)

    conn.close()
    return result


def get_activity(activity_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM activities WHERE id = ?", (activity_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_booked_activity_ids(student_id, kind):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT ab.activity_id FROM activity_bookings ab
        JOIN activities a ON a.id = ab.activity_id
        WHERE ab.student_id = ? AND a.kind = ?
        """,
        (student_id, kind)
    ).fetchall()
    conn.close()
    return {r["activity_id"] for r in rows}


def book_activity(activity_id, student_id, student_name,
                   payment_status="free", amount_paid=0, razorpay_payment_id=None):
    """
    Returns (success: bool, message_or_booking_ref: str)
    On success, the second value is the booking_ref (ticket ID).
    On failure, it's a human-readable error message.
    """

    conn = get_connection()

    activity = conn.execute(
        "SELECT * FROM activities WHERE id = ?", (activity_id,)
    ).fetchone()

    if not activity:
        conn.close()
        return False, "This is no longer available."

    already = conn.execute(
        "SELECT 1 FROM activity_bookings WHERE activity_id = ? AND student_id = ?",
        (activity_id, student_id)
    ).fetchone()

    if already:
        conn.close()
        return False, "You've already booked/registered for this."

    if activity["capacity"]:
        booked_count = conn.execute(
            "SELECT COUNT(*) as c FROM activity_bookings WHERE activity_id = ?",
            (activity_id,)
        ).fetchone()["c"]

        if booked_count >= activity["capacity"]:
            conn.close()
            return False, "Sorry, this is now full."

    booking_ref = _generate_booking_ref(activity["kind"])

    conn.execute(
        "INSERT INTO activity_bookings "
        "(activity_id, student_id, student_name, booking_ref, payment_status, amount_paid, razorpay_payment_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (activity_id, student_id, student_name, booking_ref,
         payment_status, amount_paid, razorpay_payment_id)
    )
    conn.commit()
    conn.close()

    return True, booking_ref


def cancel_booking(activity_id, student_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM activity_bookings WHERE activity_id = ? AND student_id = ?",
        (activity_id, student_id)
    )
    conn.commit()
    conn.close()


def list_bookings_for_activity(activity_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM activity_bookings WHERE activity_id = ? ORDER BY booked_at",
        (activity_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==============================================================
# Payments (Razorpay order tracking)
# ==============================================================

def create_payment_order_record(razorpay_order_id, activity_id, student_id, student_name, amount):
    conn = get_connection()
    conn.execute(
        "INSERT INTO payment_orders (razorpay_order_id, activity_id, student_id, student_name, amount) "
        "VALUES (?, ?, ?, ?, ?)",
        (razorpay_order_id, activity_id, student_id, student_name, amount)
    )
    conn.commit()
    conn.close()


def get_payment_order(razorpay_order_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM payment_orders WHERE razorpay_order_id = ?",
        (razorpay_order_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_payment_order_status(razorpay_order_id, status):
    conn = get_connection()
    conn.execute(
        "UPDATE payment_orders SET status = ? WHERE razorpay_order_id = ?",
        (status, razorpay_order_id)
    )
    conn.commit()
    conn.close()


# ==============================================================
# My Bookings / Tickets
# ==============================================================

def list_bookings_for_student(student_id):
    """
    All of a student's bookings across events/courses/facilities,
    newest first, joined with the activity details — powers the
    'My Bookings' page.
    """

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT ab.*, a.kind, a.title, a.description, a.schedule_text
        FROM activity_bookings ab
        JOIN activities a ON a.id = ab.activity_id
        WHERE ab.student_id = ?
        ORDER BY ab.booked_at DESC
        """,
        (student_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_booking_by_ref(booking_ref):
    """
    Full ticket detail (booking + activity), for the confirmation/ticket page.
    """

    conn = get_connection()
    row = conn.execute(
        """
        SELECT ab.*, a.kind, a.title, a.description, a.schedule_text
        FROM activity_bookings ab
        JOIN activities a ON a.id = ab.activity_id
        WHERE ab.booking_ref = ?
        """,
        (booking_ref,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def generate_ticket_qr_base64(booking_ref):
    """
    Returns a base64 PNG data URI of a QR code encoding the booking
    reference, for display on the ticket. Generated on the fly —
    nothing is written to disk.
    """

    img = qrcode.make(booking_ref)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


# ==============================================================
# Hostel transfer requests
# ==============================================================

def create_hostel_transfer_request(student_id, student_name, current_hostel,
                                     requested_hostel, reason, refund_needed):
    conn = get_connection()
    conn.execute(
        "INSERT INTO hostel_transfer_requests "
        "(student_id, student_name, current_hostel, requested_hostel, reason, refund_needed) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (student_id, student_name, current_hostel, requested_hostel, reason, refund_needed)
    )
    conn.commit()
    conn.close()


def list_hostel_requests_for_student(student_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM hostel_transfer_requests WHERE student_id = ? ORDER BY created_at DESC",
        (student_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_hostel_request(request_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM hostel_transfer_requests WHERE id = ?", (request_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_all_hostel_requests():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM hostel_transfer_requests ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


HOSTEL_REQUEST_STATUSES = ["Submitted", "Under Review", "Approved", "Rejected", "Completed"]


def update_hostel_request_status(request_id, status):
    conn = get_connection()
    conn.execute(
        "UPDATE hostel_transfer_requests SET status = ? WHERE id = ?",
        (status, request_id)
    )
    conn.commit()
    conn.close()


# ==============================================================
# Grievances
# ==============================================================

def create_grievance(student_id, student_name, category, description):
    conn = get_connection()
    conn.execute(
        "INSERT INTO grievances (student_id, student_name, category, description) "
        "VALUES (?, ?, ?, ?)",
        (student_id, student_name, category, description)
    )
    conn.commit()
    conn.close()


def list_grievances_for_student(student_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM grievances WHERE student_id = ? ORDER BY created_at DESC",
        (student_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_grievance(grievance_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM grievances WHERE id = ?", (grievance_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_all_grievances():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM grievances ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


GRIEVANCE_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]


def update_grievance_status(grievance_id, status):
    conn = get_connection()
    conn.execute(
        "UPDATE grievances SET status = ? WHERE id = ?",
        (status, grievance_id)
    )
    conn.commit()
    conn.close()


# ==============================================================
# Academic records (admin-entered — see project notes on why)
# ==============================================================

def get_academic_record(student_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM academic_records WHERE student_id = ?", (student_id,)
    ).fetchone()
    conn.close()

    if row:
        return dict(row)

    return {
        "student_id": student_id,
        "attendance_percent": "-",
        "exam_timetable": "Not published yet.",
        "results": "Not published yet.",
        "updated_at": None
    }


def upsert_academic_record(student_id, attendance_percent, exam_timetable, results):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO academic_records (student_id, attendance_percent, exam_timetable, results, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(student_id) DO UPDATE SET
            attendance_percent = excluded.attendance_percent,
            exam_timetable = excluded.exam_timetable,
            results = excluded.results,
            updated_at = CURRENT_TIMESTAMP
        """,
        (student_id, attendance_percent, exam_timetable, results)
    )
    conn.commit()
    conn.close()


def list_all_students():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, student_id, name, course FROM students ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
