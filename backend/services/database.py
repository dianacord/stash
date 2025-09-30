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
    
    def save_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a video to the database"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO saved_videos 
                (url, video_id, platform, raw_transcript, language, is_generated, segments_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_data['url'],
                video_data['video_id'],
                video_data.get('platform', 'youtube'),
                video_data['raw_transcript'],
                video_data.get('language'),
                video_data.get('is_generated'),
                video_data.get('segments_count')
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
            
        except KeyError as e:
            return {'success': False, 'error': f'Missing required field: {str(e)}'}
            
        except Exception as e:
            error_msg = f'{type(e).__name__}: {str(e)}' if str(e) else f'{type(e).__name__}'
            return {'success': False, 'error': error_msg}
            
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