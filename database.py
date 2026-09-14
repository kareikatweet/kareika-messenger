import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_FILE = "kareika.db"

class Database:
    def __init__(self):
        self.conn = None
        self.init_db()
    
    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def init_db(self):
        """Initialize database with all tables"""
        if not os.path.exists(DB_FILE):
            self.connect()
            cursor = self.conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    mnemonic TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    public_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'offline'
                )
            ''')
            
            # Groups table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    admin_id INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(admin_id) REFERENCES users(id)
                )
            ''')
            
            # Group members table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(group_id) REFERENCES groups(id),
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    UNIQUE(group_id, user_id)
                )
            ''')
            
            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER,
                    group_id INTEGER,
                    text TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    ciphertext TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_deleted BOOLEAN DEFAULT 0,
                    deleted_by INTEGER,
                    deleted_at TIMESTAMP,
                    FOREIGN KEY(sender_id) REFERENCES users(id),
                    FOREIGN KEY(receiver_id) REFERENCES users(id),
                    FOREIGN KEY(group_id) REFERENCES groups(id),
                    FOREIGN KEY(deleted_by) REFERENCES users(id)
                )
            ''')
            
            # Media table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT,
                    file_size INTEGER,
                    file_data BLOB,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(message_id) REFERENCES messages(id)
                )
            ''')
            
            # Notifications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT,
                    message TEXT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            # Calls table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    group_id INTEGER,
                    status TEXT DEFAULT 'ringing',
                    call_type TEXT DEFAULT 'voice',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    duration INTEGER,
                    FOREIGN KEY(caller_id) REFERENCES users(id),
                    FOREIGN KEY(receiver_id) REFERENCES users(id),
                    FOREIGN KEY(group_id) REFERENCES groups(id)
                )
            ''')
            
            self.conn.commit()
            self.conn.close()
    
    def get_connection(self):
        """Get database connection"""
        if self.conn is None:
            self.connect()
        return self.conn
    
    # USER OPERATIONS
    def create_user(self, username: str, mnemonic: str, email: str = None, phone: str = None) -> Dict:
        """Create new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, mnemonic, email, phone, status)
                VALUES (?, ?, ?, ?, 'offline')
            ''', (username, mnemonic, email, phone))
            conn.commit()
            return {"success": True, "user_id": cursor.lastrowid}
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Username already exists"}
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_user_status(self, user_id: int, status: str):
        """Update user online/offline status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
        conn.commit()
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, status FROM users')
        return [dict(row) for row in cursor.fetchall()]
    
    # GROUP OPERATIONS
    def create_group(self, name: str, admin_id: int, description: str = None) -> Dict:
        """Create new group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO groups (name, admin_id, description)
            VALUES (?, ?, ?)
        ''', (name, admin_id, description))
        conn.commit()
        
        group_id = cursor.lastrowid
        # Add admin to group
        cursor.execute('''
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'admin')
        ''', (group_id, admin_id))
        conn.commit()
        
        return {"success": True, "group_id": group_id}
    
    def get_group(self, group_id: int) -> Optional[Dict]:
        """Get group by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def add_group_member(self, group_id: int, user_id: int, role: str = 'member') -> Dict:
        """Add member to group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (?, ?, ?)
            ''', (group_id, user_id, role))
            conn.commit()
            return {"success": True}
        except sqlite3.IntegrityError:
            return {"success": False, "error": "User already in group"}
    
    def remove_group_member(self, group_id: int, user_id: int):
        """Remove member from group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user_id))
        conn.commit()
    
    def get_group_members(self, group_id: int) -> List[Dict]:
        """Get all members of group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.username, u.status, gm.role
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = ?
        ''', (group_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_groups(self, user_id: int) -> List[Dict]:
        """Get all groups for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.* FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_group(self, group_id: int):
        """Delete group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM messages WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
        conn.commit()
    
    # MESSAGE OPERATIONS
    def save_message(self, sender_id: int, text: str, receiver_id: int = None, 
                    group_id: int = None, message_type: str = 'text') -> Dict:
        """Save message to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, group_id, text, message_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (sender_id, receiver_id, group_id, text, message_type))
        conn.commit()
        return {"success": True, "message_id": cursor.lastrowid}
    
    def get_messages(self, user_id: int = None, group_id: int = None, limit: int = 50) -> List[Dict]:
        """Get messages"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if group_id:
            cursor.execute('''
                SELECT m.*, u.username as sender_name
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.group_id = ? AND m.is_deleted = 0
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (group_id, limit))
        else:
            cursor.execute('''
                SELECT m.*, u.username as sender_name
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE (m.receiver_id = ? OR m.sender_id = ?) AND m.is_deleted = 0
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (user_id, user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_message(self, message_id: int, deleted_by: int):
        """Delete message (soft delete)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE messages
            SET is_deleted = 1, deleted_by = ?, deleted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (deleted_by, message_id))
        conn.commit()
    
    def get_message(self, message_id: int) -> Optional[Dict]:
        """Get single message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # MEDIA OPERATIONS
    def save_media(self, message_id: int, file_name: str, file_type: str, file_size: int, file_data: bytes) -> Dict:
        """Save media file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO media (message_id, file_name, file_type, file_size, file_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (message_id, file_name, file_type, file_size, file_data))
        conn.commit()
        return {"success": True, "media_id": cursor.lastrowid}
    
    def get_media(self, message_id: int) -> Optional[Dict]:
        """Get media by message ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM media WHERE message_id = ?', (message_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # NOTIFICATION OPERATIONS
    def create_notification(self, user_id: int, notif_type: str, title: str, message: str, data: str = None) -> Dict:
        """Create notification"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (user_id, type, title, message, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, notif_type, title, message, data))
        conn.commit()
        return {"success": True, "notification_id": cursor.lastrowid}
    
    def get_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict]:
        """Get notifications"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if unread_only:
            cursor.execute('''
                SELECT * FROM notifications
                WHERE user_id = ? AND read_at IS NULL
                ORDER BY created_at DESC
            ''', (user_id,))
        else:
            cursor.execute('''
                SELECT * FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_notification_read(self, notification_id: int):
        """Mark notification as read"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notifications
            SET read_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (notification_id,))
        conn.commit()
    
    # CALL OPERATIONS
    def create_call(self, caller_id: int, receiver_id: int = None, group_id: int = None, call_type: str = 'voice') -> Dict:
        """Create call record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO calls (caller_id, receiver_id, group_id, call_type, status)
            VALUES (?, ?, ?, ?, 'ringing')
        ''', (caller_id, receiver_id, group_id, call_type))
        conn.commit()
        return {"success": True, "call_id": cursor.lastrowid}
    
    def end_call(self, call_id: int):
        """End call"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE calls
            SET status = 'ended', ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (call_id,))
        conn.commit()
    
    def get_call(self, call_id: int) -> Optional[Dict]:
        """Get call details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM calls WHERE id = ?', (call_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# Initialize database
db = Database()
