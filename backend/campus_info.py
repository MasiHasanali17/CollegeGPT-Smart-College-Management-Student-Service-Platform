"""
campus_info.py

Data-access layer for Phase 3 admin-manageable public info content that
doesn't fit prospective.py (applications/contact) or portal.py (student
services). Currently just Transport Routes.

Standalone — does not touch the chatbot or backend/analytics/.
"""

from database import get_connection


def create_route(route_name, stops_text, timing_text, contact):
    conn = get_connection()
    conn.execute(
        "INSERT INTO transport_routes (route_name, stops_text, timing_text, contact) "
        "VALUES (?, ?, ?, ?)",
        (route_name, stops_text, timing_text, contact)
    )
    conn.commit()
    conn.close()


def list_routes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transport_routes ORDER BY route_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_route(route_id):
    conn = get_connection()
    conn.execute("DELETE FROM transport_routes WHERE id = ?", (route_id,))
    conn.commit()
    conn.close()
