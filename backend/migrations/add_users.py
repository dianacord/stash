import sqlite3

def migrate():
    """Add users table and user_id to saved_videos"""
    conn = sqlite3.connect('stash.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add user_id column to saved_videos if it doesn't exist
    try:
        cursor.execute('ALTER TABLE saved_videos ADD COLUMN user_id INTEGER')
    except sqlite3.OperationalError:
        print("user_id column already exists")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully")

if __name__ == "__main__":
    migrate()