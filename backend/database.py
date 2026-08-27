"""
database.py

SQLite database setup for student accounts and portal data.
This is separate from the chatbot's data (knowledge_base.json,
faiss_index.bin, etc.) — the chatbot is untouched by this file.
"""

import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "students.db"
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            course TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ------------------------------------------------------------
    # Prospective-student (non-student / Interface 1) tables
    # ------------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            course TEXT,
            status TEXT DEFAULT 'Received',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ------------------------------------------------------------
    # Current-student (Interface 2 / student portal) tables
    # ------------------------------------------------------------

    # "activities" covers events, extra courses, and sports/gym slots —
    # they're structurally the same (title, description, when, capacity),
    # just filtered by `kind` on the student-facing pages.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,               -- 'event' | 'course' | 'facility'
            title TEXT NOT NULL,
            description TEXT,
            schedule_text TEXT,               -- e.g. "12 Aug, 6:00 PM" or "Mon/Wed 7-8 AM"
            capacity INTEGER DEFAULT 0,        -- 0 = unlimited
            price INTEGER DEFAULT 0,           -- rupees, 0 = free (instant booking)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            booking_ref TEXT UNIQUE,
            payment_status TEXT DEFAULT 'free',   -- 'free' | 'paid'
            amount_paid INTEGER DEFAULT 0,
            razorpay_payment_id TEXT,
            booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(activity_id, student_id)
        )
    """)

    # Tracks a Razorpay order from creation until payment is verified.
    # Needed so /portal/verify-payment knows which student+activity an
    # order belongs to once Razorpay calls back with a payment result.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razorpay_order_id TEXT UNIQUE NOT NULL,
            activity_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'created',   -- 'created' | 'paid' | 'failed'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hostel_transfer_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            current_hostel TEXT NOT NULL,
            requested_hostel TEXT NOT NULL,
            reason TEXT NOT NULL,
            refund_needed TEXT DEFAULT 'No',
            status TEXT DEFAULT 'Submitted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS academic_records (
            student_id TEXT PRIMARY KEY,
            attendance_percent TEXT DEFAULT '-',
            exam_timetable TEXT DEFAULT 'Not published yet.',
            results TEXT DEFAULT 'Not published yet.',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Phase 3: Transport routes (public info page, admin-manageable —
    # no real bus-route data exists yet, so this starts empty until
    # an admin adds real routes; nothing is fabricated here)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transport_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT NOT NULL,
            stops_text TEXT NOT NULL,
            timing_text TEXT,
            contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Phase 4: Gallery
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gallery_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            caption TEXT,
            filename TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Phase 5: Admin user accounts (replaces the single shared password)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Phase 5: Student notifications (bell icon)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    _migrate_add_columns(cursor)
    conn.commit()

    _bootstrap_super_admin(cursor)
    conn.commit()

    conn.close()
    print("[Database] students.db ready.")


def _migrate_add_columns(cursor):
    """
    Adds columns introduced after a table already existed, so people
    upgrading from an earlier phase don't need to delete their database.
    Safe to run every time — checks before adding.
    """

    def existing_columns(table):
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    activity_cols = existing_columns("activities")
    if "price" not in activity_cols:
        cursor.execute("ALTER TABLE activities ADD COLUMN price INTEGER DEFAULT 0")

    booking_cols = existing_columns("activity_bookings")
    if "booking_ref" not in booking_cols:
        cursor.execute("ALTER TABLE activity_bookings ADD COLUMN booking_ref TEXT")
    if "payment_status" not in booking_cols:
        cursor.execute("ALTER TABLE activity_bookings ADD COLUMN payment_status TEXT DEFAULT 'free'")
    if "amount_paid" not in booking_cols:
        cursor.execute("ALTER TABLE activity_bookings ADD COLUMN amount_paid INTEGER DEFAULT 0")
    if "razorpay_payment_id" not in booking_cols:
        cursor.execute("ALTER TABLE activity_bookings ADD COLUMN razorpay_payment_id TEXT")

    # Phase 4: Notice board upgrade
    notice_cols = existing_columns("notices")
    if "expiry_date" not in notice_cols:
        cursor.execute("ALTER TABLE notices ADD COLUMN expiry_date TEXT")
    if "target_audience" not in notice_cols:
        cursor.execute("ALTER TABLE notices ADD COLUMN target_audience TEXT DEFAULT 'All Students'")
    if "attachment_filename" not in notice_cols:
        cursor.execute("ALTER TABLE notices ADD COLUMN attachment_filename TEXT")

    # Phase 5: Security question for self-service password reset
    # (no real email/SMS service is configured, so this is the honest,
    # actually-working option rather than faking an "email sent" flow)
    student_cols = existing_columns("students")
    if "security_question" not in student_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN security_question TEXT")
    if "security_answer_hash" not in student_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN security_answer_hash TEXT")


ADMIN_ROLES = [
    "super_admin",
    "admission_admin",
    "hostel_admin",
    "grievance_admin",
    "academic_admin",
    "student_services_admin",
]

# Which admin_portal tabs (+ the separate applications admin page) each
# role can access. super_admin bypasses this entirely (sees everything).
ROLE_PERMISSIONS = {
    "admission_admin": {"applications"},
    "hostel_admin": {"hostel", "transport"},
    "grievance_admin": {"grievances"},
    "academic_admin": {"academics"},
    "student_services_admin": {"notices", "events", "courses", "facilities", "gallery"},
}


def _bootstrap_super_admin(cursor):
    """
    Creates a default super_admin account (username: superadmin,
    password: admin123) ONLY if no admin accounts exist yet — keeps the
    same password that was already being used, so existing testing/setup
    isn't disrupted, but now backed by a real account instead of a
    hardcoded constant. Change this password after first login.
    """

    from werkzeug.security import generate_password_hash

    cursor.execute("SELECT COUNT(*) FROM admin_users")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
            ("superadmin", generate_password_hash("admin123"), "super_admin")
        )
        print("[Database] Bootstrapped default admin -> username: superadmin | password: admin123 (please change this)")


if __name__ == "__main__":
    init_db()