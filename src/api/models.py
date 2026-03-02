import sqlite3
import os

DB_PATH = "images.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                original_path TEXT,
                thumb_path TEXT,
                preset TEXT,
                width INTEGER,
                height INTEGER,
                status TEXT
            )
        """
        )
        conn.commit()


def save_initial_upload(image_id, original_path):
    with get_db() as conn:
        # Note the (val1, val2, val3) tuple structure
        conn.execute(
            "INSERT INTO images (id, original_path, status) VALUES (?, ?, ?)",
            (image_id, original_path, "processing"),
        )
        conn.commit()


def update_resize_status(image_id, thumb_path, w, h, preset):
    with get_db() as conn:
        # FIX: The number of ? must match the length of the tuple below
        conn.execute(
            "UPDATE images SET thumb_path = ?, width = ?, height = ?, preset = ?, status = 'completed' WHERE id = ?",
            (thumb_path, w, h, preset, image_id),
        )
        conn.commit()


def get_metadata(image_id):
    with get_db() as conn:
        # FIX: Added the trailing comma (image_id,) to ensure it's a tuple
        row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        return dict(row) if row else None
