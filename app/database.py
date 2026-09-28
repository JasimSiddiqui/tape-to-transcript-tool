"""SQLite storage for transcripts and their timestamped segments.

Only used from the UI (main) thread.
"""

import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS transcripts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    source_path TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    duration    REAL NOT NULL DEFAULT 0,
    language    TEXT,
    model       TEXT,
    text        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS segments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    transcript_id INTEGER NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    start         REAL NOT NULL,
    end           REAL NOT NULL,
    text          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_segments_transcript ON segments(transcript_id, position);
"""


class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def add_transcript(self, title, source_path, duration, language, model, segments, text):
        """segments: list of (start, end, text) tuples. Returns the new transcript id."""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO transcripts (title, source_path, created_at, duration, language, model, text)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, source_path, created_at, duration, language, model, text),
            )
            transcript_id = cursor.lastrowid
            self.conn.executemany(
                "INSERT INTO segments (transcript_id, position, start, end, text) VALUES (?, ?, ?, ?, ?)",
                [(transcript_id, i, start, end, seg_text) for i, (start, end, seg_text) in enumerate(segments)],
            )
        return transcript_id

    def list_transcripts(self, query=""):
        """Newest first. Filters by title or transcript text when a query is given."""
        sql = "SELECT id, title, created_at, duration FROM transcripts"
        params = ()
        query = query.strip()
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            sql += " WHERE title LIKE ? ESCAPE '\\' OR text LIKE ? ESCAPE '\\'"
            params = (pattern, pattern)
        sql += " ORDER BY created_at DESC, id DESC"
        return self.conn.execute(sql, params).fetchall()

    def get_transcript(self, transcript_id):
        return self.conn.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,)).fetchone()

    def get_segments(self, transcript_id):
        """Returns a list of (start, end, text) tuples in order."""
        rows = self.conn.execute(
            "SELECT start, end, text FROM segments WHERE transcript_id = ? ORDER BY position",
            (transcript_id,),
        ).fetchall()
        return [(row["start"], row["end"], row["text"]) for row in rows]

    def rename_transcript(self, transcript_id, title):
        with self.conn:
            self.conn.execute("UPDATE transcripts SET title = ? WHERE id = ?", (title, transcript_id))

    def delete_transcript(self, transcript_id):
        with self.conn:
            self.conn.execute("DELETE FROM transcripts WHERE id = ?", (transcript_id,))
