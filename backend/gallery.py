"""
gallery.py

Data-access layer for the admin-manageable photo gallery (Phase 4).
Standalone — no chatbot dependency.
"""

from database import get_connection

CATEGORIES = ["Campus", "Hostels", "Labs", "Library", "Sports", "Events", "Cultural", "Student Activities"]


def add_image(category, caption, filename):
    conn = get_connection()
    conn.execute(
        "INSERT INTO gallery_images (category, caption, filename) VALUES (?, ?, ?)",
        (category, caption, filename)
    )
    conn.commit()
    conn.close()


def list_images(category=None):
    conn = get_connection()
    if category and category != "All":
        rows = conn.execute(
            "SELECT * FROM gallery_images WHERE category = ? ORDER BY uploaded_at DESC",
            (category,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM gallery_images ORDER BY uploaded_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_image(image_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM gallery_images WHERE id = ?", (image_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_image(image_id):
    conn = get_connection()
    conn.execute("DELETE FROM gallery_images WHERE id = ?", (image_id,))
    conn.commit()
    conn.close()
