import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
import traceback

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
        print(f"Database initialized at {self.db_path}")
    
    def save_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        conn = None
        try:
            print(f"DEBUG - save_video called with video_id: {video_data.get('video_id')}")
            print(f"DEBUG - Database path: {self.db_path}")
            print(f"DEBUG - Full video_data keys: {video_data.keys()}")
            
            conn = sqlite3.connect(self.db_path)
            print(f"DEBUG - Database connected successfully")
            
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            print(f"DEBUG - About to insert with values:")
            print(f"  url: {video_data.get('url')}")
            print(f"  video_id: {video_data.get('video_id')}")
            print(f"  platform: {video_data.get('platform', 'youtube')}")
            print(f"  transcript length: {len(video_data.get('raw_transcript', ''))}")
            print(f"  language: {video_data.get('language')}")
            print(f"  is_generated: {video_data.get('is_generated')}")
            print(f"  segments_count: {video_data.get('segments_count')}")
            
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
            
            print(f"DEBUG - Insert executed, rows affected: {cursor.rowcount}")
            
            conn.commit()
            print(f"DEBUG - Commit successful")
            
            video_id = cursor.lastrowid
            print(f"DEBUG - Last row id: {video_id}")
            
            cursor.execute('SELECT * FROM saved_videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            
            if row:
                result_data = dict(row)
                print(f"DEBUG - Successfully retrieved inserted row: {result_data.get('video_id')}")
                return {'success': True, 'data': result_data}
            else:
                print(f"ERROR - Could not retrieve inserted row")
                return {'success': False, 'error': 'Video inserted but could not retrieve'}
            
        except sqlite3.IntegrityError as e:
            error_msg = f'Video already exists: {str(e)}'
            print(f"ERROR - IntegrityError: {error_msg}")
            traceback.print_exc()
            return {'success': False, 'error': error_msg}
            
        except KeyError as e:
            error_msg = f'Missing required field: {str(e)}'
            print(f"ERROR - KeyError: {error_msg}")
            traceback.print_exc()
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = f'{type(e).__name__}: {str(e)}' if str(e) else f'{type(e).__name__} with no message'
            print(f"ERROR - Unexpected exception: {error_msg}")
            traceback.print_exc()
            return {'success': False, 'error': error_msg}
            
        finally:
            if conn:
                conn.close()
                print(f"DEBUG - Database connection closed")
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video by YouTube video ID"""
        conn = None
        try:
            print(f"DEBUG - Getting video by id: {video_id}")
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM saved_videos WHERE video_id = ?', (video_id,))
            row = cursor.fetchone()
            
            result = dict(row) if row else None
            print(f"DEBUG - Found existing video: {result is not None}")
            return result
            
        except Exception as e:
            print(f"ERROR fetching video: {type(e).__name__}: {e}")
            traceback.print_exc()
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
            
        except Exception as e:
            print(f"ERROR fetching videos: {type(e).__name__}: {e}")
            traceback.print_exc()
            return []
            
        finally:
            if conn:
                conn.close()