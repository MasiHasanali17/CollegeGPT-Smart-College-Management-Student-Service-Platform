"""
admin_auth.py

Real admin-account authentication with roles, replacing the single
shared ADMIN_PASSWORD constant. Separate from student auth (auth.py) —
admins are staff, not students.

Roles and their tab permissions live in database.py (ROLE_PERMISSIONS)
since that's also where the table schema/bootstrap logic lives.
"""

from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, ADMIN_ROLES, ROLE_PERMISSIONS


def verify_admin_login(username, password):
    """
    Returns the admin user dict if credentials are valid and the account
    is active, else None.
    """

    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM admin_users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    if not row["active"]:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return dict(row)


def get_admin_by_id(admin_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM admin_users WHERE id = ?", (admin_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def can_access(role, tab_or_page):
    """
    True if the given role is allowed to access the given admin_portal
    tab name (or 'applications' for the separate applications page).
    super_admin can access everything.
    """

    if role == "super_admin":
        return True

    return tab_or_page in ROLE_PERMISSIONS.get(role, set())


def allowed_tabs(role):
    """Ordered list of tab names this role can see in the nav."""

    all_tabs = ["notices", "events", "courses", "facilities", "hostel",
                "grievances", "academics", "transport", "gallery",
                "students", "admins"]

    if role == "super_admin":
        return all_tabs

    permitted = ROLE_PERMISSIONS.get(role, set())
    return [t for t in all_tabs if t in permitted]


def create_admin(username, password, role):
    """
    Returns (success: bool, message: str)
    """

    if role not in ADMIN_ROLES:
        return False, "Invalid role."

    conn = get_connection()

    existing = conn.execute(
        "SELECT 1 FROM admin_users WHERE username = ?", (username,)
    ).fetchone()

    if existing:
        conn.close()
        return False, "That username is already taken."

    conn.execute(
        "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), role)
    )
    conn.commit()
    conn.close()

    return True, "Admin account created."


def list_admins():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, role, active, created_at FROM admin_users ORDER BY created_at"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_admin_active(admin_id, active):
    conn = get_connection()
    conn.execute(
        "UPDATE admin_users SET active = ? WHERE id = ?", (1 if active else 0, admin_id)
    )
    conn.commit()
    conn.close()


def reset_admin_password(admin_id, new_password):
    conn = get_connection()
    conn.execute(
        "UPDATE admin_users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), admin_id)
    )
    conn.commit()
    conn.close()
