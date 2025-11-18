import sqlite3
from typing import Any


class DatabaseService:
    def __init__(self, db_path: str = "stash.db"):
        self.db_path = db_path
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        """Create a connection with row_factory set to sqlite3.Row."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """Create tables if they don't exist"""
        with self._connect() as conn:
            cursor = conn.cursor()

            # users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")

            # saved videos table with user_id column
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    video_id TEXT NOT NULL UNIQUE,
                    platform TEXT DEFAULT 'youtube',
                    title TEXT,
                    raw_transcript TEXT,
                    ai_summary TEXT,
                    language TEXT,
                    is_generated BOOLEAN,
                    segments_count INTEGER,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_id ON saved_videos(video_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON saved_videos(user_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_at ON saved_videos(created_at DESC)"
            )

    def save_video(self, video_data: dict[str, Any], user_id: int) -> dict[str, Any]:
        """Save a video to the database with user_id"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO saved_videos
                    (url, video_id, platform, raw_transcript, ai_summary, language, is_generated, segments_count, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                )

                new_id = cursor.lastrowid
                cursor.execute("SELECT * FROM saved_videos WHERE id = ?", (new_id,))
                row = cursor.fetchone()

                if row:
                    return {"success": True, "data": dict(row)}
                else:
                    return {"success": False, "error": "Video inserted but could not retrieve"}
        except sqlite3.IntegrityError as e:
            return {"success": False, "error": f"Video already exists: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_videos(self, user_id: int) -> list[dict[str, Any]]:
        """Get all videos for a specific user"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM saved_videos WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_video_by_id(self, video_id: str) -> dict[str, Any] | None:
        """Get video by YouTube video ID"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM saved_videos WHERE video_id = ?", (video_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def get_all_videos(self) -> list[dict[str, Any]]:
        """Get all saved videos"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM saved_videos ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def create_user(self, username: str, hashed_password: str) -> dict[str, Any]:
        """Create a new user"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (username, hashed_password)
                    VALUES (?, ?)
                """,
                    (username, hashed_password),
                )
                new_id = cursor.lastrowid
                cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (new_id,))
                row = cursor.fetchone()
                if row:
                    return {"success": True, "data": dict(row)}
                else:
                    return {"success": False, "error": "User created but could not retrieve"}
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Username already exists"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Get user by username (includes hashed_password for auth)"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Get user by ID"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def delete_video(self, video_id: str) -> dict[str, Any]:
        """Delete a video by ID"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM saved_videos WHERE video_id = ?", (video_id,))
                if cursor.rowcount > 0:
                    return {"success": True}
                else:
                    return {"success": False, "error": "Video not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_video(self, video_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update video fields"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                # Only allow updating certain fields
                allowed_fields = ["ai_summary", "title"]
                update_parts = []
                values = []
                for field in allowed_fields:
                    if field in updates:
                        update_parts.append(f"{field} = ?")
                        values.append(updates[field])
                if not update_parts:
                    return {"success": False, "error": "No valid fields to update"}
                values.append(video_id)
                query = f"UPDATE saved_videos SET {', '.join(update_parts)} WHERE video_id = ?"
                cursor.execute(query, values)
                # Get updated video
                cursor.execute("SELECT * FROM saved_videos WHERE video_id = ?", (video_id,))
                row = cursor.fetchone()
                if row:
                    return {"success": True, "data": dict(row)}
                else:
                    return {"success": False, "error": "Video not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
