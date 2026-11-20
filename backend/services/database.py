import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

# Any constant works; it just has to be the same in every replica.
_SCHEMA_LOCK_ID = 7_824_001


def get_database_url() -> str:
    """Return the Postgres connection string, or fail if it isn't set."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Point it at Postgres, for example "
            "postgresql://stash:stash@localhost:5432/stash (see README)."
        )
    return url


class DatabaseService:
    def __init__(self, dsn: str | None = None):
        # Don't connect here. On Kubernetes the app can start before Postgres
        # is up, and the app must still boot and answer its probes meanwhile.
        # Tables are created on first use instead (see _connect).
        self.dsn = dsn or get_database_url()
        self._schema_ready = False

    def _open(self) -> psycopg.Connection:
        """Open a connection that returns rows as dicts.

        Used as a context manager: commits on success, rolls back on error.
        """
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5)

    def _connect(self) -> psycopg.Connection:
        """Open a connection, creating the tables first if this is the first use."""
        if not self._schema_ready:
            self._init_database()
        return self._open()

    def ping(self) -> bool:
        """Return True if the database answers a trivial query."""
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _init_database(self):
        """Create tables if they don't exist.

        Several replicas can start at once, and concurrent CREATE TABLE IF NOT
        EXISTS can still collide in Postgres, so schema setup runs under an
        advisory lock that only one connection can hold at a time.
        """
        with self._open() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_SCHEMA_LOCK_ID,))

            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_videos (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL,
                    video_id TEXT NOT NULL UNIQUE,
                    platform TEXT DEFAULT 'youtube',
                    title TEXT,
                    raw_transcript TEXT,
                    ai_summary TEXT,
                    language TEXT,
                    is_generated BOOLEAN,
                    segments_count INTEGER,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON saved_videos(user_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_at ON saved_videos(created_at DESC)"
            )
        self._schema_ready = True

    def save_video(self, video_data: dict[str, Any], user_id: int) -> dict[str, Any]:
        """Save a video to the database with user_id"""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO saved_videos
                    (url, video_id, platform, raw_transcript, ai_summary, language,
                     is_generated, segments_count, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        video_data["url"],
                        video_data["video_id"],
                        video_data.get("platform", "youtube"),
                        video_data["raw_transcript"],
                        video_data.get("ai_summary"),
                        video_data.get("language"),
                        video_data.get("is_generated"),
                        video_data.get("segments_count"),
                        user_id,
                    ),
                ).fetchone()
                return {"success": True, "data": row}
        except psycopg.errors.UniqueViolation as e:
            return {"success": False, "error": f"Video already exists: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_videos(self, user_id: int) -> list[dict[str, Any]]:
        """Get all videos for a specific user"""
        try:
            with self._connect() as conn:
                return conn.execute(
                    "SELECT * FROM saved_videos WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
        except Exception:
            return []

    def get_video_by_id(self, video_id: str) -> dict[str, Any] | None:
        """Get video by YouTube video ID"""
        try:
            with self._connect() as conn:
                return conn.execute(
                    "SELECT * FROM saved_videos WHERE video_id = %s", (video_id,)
                ).fetchone()
        except Exception:
            return None

    def get_all_videos(self) -> list[dict[str, Any]]:
        """Get all saved videos"""
        try:
            with self._connect() as conn:
                return conn.execute(
                    "SELECT * FROM saved_videos ORDER BY created_at DESC"
                ).fetchall()
        except Exception:
            return []

    def create_user(self, username: str, hashed_password: str) -> dict[str, Any]:
        """Create a new user"""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO users (username, hashed_password)
                    VALUES (%s, %s)
                    RETURNING id, username, created_at
                    """,
                    (username, hashed_password),
                ).fetchone()
                return {"success": True, "data": row}
        except psycopg.errors.UniqueViolation:
            return {"success": False, "error": "Username already exists"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Get user by username (includes hashed_password for auth)"""
        try:
            with self._connect() as conn:
                return conn.execute(
                    "SELECT * FROM users WHERE username = %s", (username,)
                ).fetchone()
        except Exception:
            return None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Get user by ID"""
        try:
            with self._connect() as conn:
                return conn.execute(
                    "SELECT id, username, created_at FROM users WHERE id = %s", (user_id,)
                ).fetchone()
        except Exception:
            return None

    def delete_video(self, video_id: str) -> dict[str, Any]:
        """Delete a video by ID"""
        try:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM saved_videos WHERE video_id = %s", (video_id,))
                if cursor.rowcount > 0:
                    return {"success": True}
                return {"success": False, "error": "Video not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_video(self, video_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update video fields"""
        # Only allow updating certain fields. Field names come from this fixed
        # list, never from the caller, so formatting them into the SQL is safe.
        allowed_fields = ["ai_summary", "title"]
        update_parts = []
        values = []
        for field in allowed_fields:
            if field in updates:
                update_parts.append(f"{field} = %s")
                values.append(updates[field])
        if not update_parts:
            return {"success": False, "error": "No valid fields to update"}
        values.append(video_id)
        try:
            with self._connect() as conn:
                row = conn.execute(
                    f"UPDATE saved_videos SET {', '.join(update_parts)} "
                    "WHERE video_id = %s RETURNING *",
                    values,
                ).fetchone()
                if row:
                    return {"success": True, "data": row}
                return {"success": False, "error": "Video not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
