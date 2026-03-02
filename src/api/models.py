import sqlite3

def get_db():
    conn = sqlite3.connect("images.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                original_path TEXT,
                thumb_path TEXT,
                width INTEGER,
                height INTEGER,
                status TEXT
            )
        """)

def save_metadata(image_id, original_path, thumb_path, w, h):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO images (id, original_path, thumb_path, width, height, status) VALUES (?, ?, ?, ?, ?, ?)",
            (image_id, original_path, thumb_path, w, h, "completed")
        )

def get_metadata(image_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        return dict(row) if row else None