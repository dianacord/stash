import sqlite3
from typing import Optional, List, Dict, Any

class DatabaseService:
    def __init__(self, db_path: str = "stash.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON saved_videos(video_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON saved_videos(created_at DESC)')
        
        conn.commit()
        conn.close()
    
    def save_video(self, video_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Save a video to the database with user_id"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO saved_videos 
                (url, video_id, platform, raw_transcript, ai_summary, language, is_generated, segments_count, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_data['url'],
                video_data['video_id'],
                video_data.get('platform', 'youtube'),
                video_data['raw_transcript'],
                video_data.get('ai_summary'),
                video_data.get('language'),
                video_data.get('is_generated'),
                video_data.get('segments_count'),
                user_id 
            ))
            
            conn.commit()
            video_id = cursor.lastrowid
            
            cursor.execute('SELECT * FROM saved_videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            
            if row:
                return {'success': True, 'data': dict(row)}
            else:
                return {'success': False, 'error': 'Video inserted but could not retrieve'}
                
        except sqlite3.IntegrityError as e:
            return {'success': False, 'error': f'Video already exists: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if conn:
                conn.close()

    def get_user_videos(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all videos for a specific user"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT * FROM saved_videos WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception:
            return []
        finally:
            if conn:
                conn.close()
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video by YouTube video ID"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM saved_videos WHERE video_id = ?', (video_id,))
            row = cursor.fetchone()
            
            return dict(row) if row else None
            
        except Exception:
            return None
            
        finally:
            if conn:
                conn.close()
    
    def get_all_videos(self) -> List[Dict[str, Any]]:
        """Get all saved videos"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM saved_videos ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception:
            return []
            
        finally:
            if conn:
                conn.close()

    def create_user(self, username: str, hashed_password: str) -> Dict[str, Any]:
        """Create a new user"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, hashed_password)
                VALUES (?, ?)
            ''', (username, hashed_password))
            
            conn.commit()
            user_id = cursor.lastrowid
            
            cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return {'success': True, 'data': dict(row)}
            else:
                return {'success': False, 'error': 'User created but could not retrieve'}
                
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Username already exists'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if conn:
                conn.close()

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username (includes hashed_password for auth)"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            
            return dict(row) if row else None
            
        except Exception:
            return None
        finally:
            if conn:
                conn.close()

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            return dict(row) if row else None
            
        except Exception:
            return None
        finally:
            if conn:
                conn.close()

    def delete_video(self, video_id: str) -> Dict[str, Any]:
        """Delete a video by ID"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM saved_videos WHERE video_id = ?', (video_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Video not found'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if conn:
                conn.close()

    def update_video(self, video_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update video fields"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Only allow updating certain fields
            allowed_fields = ['ai_summary', 'title']
            update_parts = []
            values = []
            
            for field in allowed_fields:
                if field in updates:
                    update_parts.append(f"{field} = ?")
                    values.append(updates[field])
            
            if not update_parts:
                return {'success': False, 'error': 'No valid fields to update'}
            
            values.append(video_id)
            query = f"UPDATE saved_videos SET {', '.join(update_parts)} WHERE video_id = ?"
            
            cursor.execute(query, values)
            conn.commit()
            
            # Get updated video
            cursor.execute('SELECT * FROM saved_videos WHERE video_id = ?', (video_id,))
            row = cursor.fetchone()
            
            if row:
                return {'success': True, 'data': dict(row)}
            else:
                return {'success': False, 'error': 'Video not found'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if conn:
                conn.close()