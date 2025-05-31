import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Audio files table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS audio_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        file_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        duration INTEGER,
                        file_size INTEGER,
                        format TEXT,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # TTS configurations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tts_configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        text_content TEXT NOT NULL,
                        voice_name TEXT DEFAULT 'alice',
                        language TEXT DEFAULT 'en-US',
                        speed REAL DEFAULT 1.0,
                        pitch REAL DEFAULT 0.0,
                        ssml_enabled BOOLEAN DEFAULT FALSE,
                        ssml_content TEXT,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Call sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS call_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        phone_number TEXT NOT NULL,
                        audio_file_id INTEGER,
                        tts_config_id INTEGER,
                        call_type TEXT DEFAULT 'audio',
                        twilio_call_sid TEXT,
                        status TEXT DEFAULT 'initiated',
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        FOREIGN KEY (audio_file_id) REFERENCES audio_files (id),
                        FOREIGN KEY (tts_config_id) REFERENCES tts_configs (id)
                    )
                ''')
                
                # Voice responses table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS voice_responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        call_session_id INTEGER,
                        full_transcription TEXT,
                        extracted_numbers TEXT,
                        confidence_score REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (call_session_id) REFERENCES call_sessions (id)
                    )
                ''')
                
                # User sessions table for inline keyboard state
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        user_id INTEGER PRIMARY KEY,
                        session_data TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def save_audio_file(self, user_id: int, file_id: str, filename: str, 
                       file_path: str, duration: int = None, file_size: int = None, 
                       format: str = None) -> int:
        """Save audio file information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audio_files (user_id, file_id, filename, file_path, 
                                           duration, file_size, format)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, file_id, filename, file_path, duration, file_size, format))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            raise
    
    def get_user_audio_files(self, user_id: int) -> List[Dict]:
        """Get all audio files for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM audio_files WHERE user_id = ? ORDER BY upload_date DESC
                ''', (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting audio files: {e}")
            return []
    
    def delete_audio_file(self, user_id: int, audio_id: int) -> bool:
        """Delete audio file record"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM audio_files WHERE id = ? AND user_id = ?
                ''', (audio_id, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting audio file: {e}")
            return False
    
    def save_tts_config(self, user_id: int, text_content: str, config: Dict) -> int:
        """Save TTS configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tts_configs (user_id, text_content, voice_name, language,
                                           speed, pitch, ssml_enabled, ssml_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, text_content, config.get('voice_name', 'alice'),
                    config.get('language', 'en-US'), config.get('speed', 1.0),
                    config.get('pitch', 0.0), config.get('ssml_enabled', False),
                    json.dumps(config.get('ssml_options', {}))
                ))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving TTS config: {e}")
            raise
    
    def create_call_session(self, user_id: int, phone_number: str, 
                           call_type: str = 'audio', audio_file_id: int = None,
                           tts_config_id: int = None) -> int:
        """Create new call session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO call_sessions (user_id, phone_number, call_type,
                                             audio_file_id, tts_config_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, phone_number, call_type, audio_file_id, tts_config_id))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating call session: {e}")
            raise
    
    def update_call_session(self, session_id: int, **kwargs):
        """Update call session with new data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                set_clauses = []
                values = []
                
                for key, value in kwargs.items():
                    if key in ['twilio_call_sid', 'status', 'end_time']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if set_clauses:
                    values.append(session_id)
                    cursor.execute(f'''
                        UPDATE call_sessions SET {', '.join(set_clauses)}
                        WHERE id = ?
                    ''', values)
        except Exception as e:
            logger.error(f"Error updating call session: {e}")
    
    def save_voice_response(self, call_session_id: int, transcription: str,
                           extracted_numbers: str, confidence_score: float = None):
        """Save voice response data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO voice_responses (call_session_id, full_transcription,
                                               extracted_numbers, confidence_score)
                    VALUES (?, ?, ?, ?)
                ''', (call_session_id, transcription, extracted_numbers, confidence_score))
        except Exception as e:
            logger.error(f"Error saving voice response: {e}")
    
    def get_call_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get call history for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT cs.*, vr.full_transcription, vr.extracted_numbers
                    FROM call_sessions cs
                    LEFT JOIN voice_responses vr ON cs.id = vr.call_session_id
                    WHERE cs.user_id = ?
                    ORDER BY cs.start_time DESC
                    LIMIT ?
                ''', (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting call history: {e}")
            return []
    
    def save_user_session(self, user_id: int, session_data: Dict):
        """Save user session data for inline keyboards"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_sessions (user_id, session_data, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, json.dumps(session_data)))
        except Exception as e:
            logger.error(f"Error saving user session: {e}")
    
    def get_user_session(self, user_id: int) -> Dict:
        """Get user session data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT session_data FROM user_sessions WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return {}
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return {}
    
    def clear_user_session(self, user_id: int):
        """Clear user session data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
        except Exception as e:
            logger.error(f"Error clearing user session: {e}")

    def get_call_session_by_sid(self, call_sid: str) -> Optional[Dict]:
        """Get call session by Twilio call SID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM call_sessions WHERE twilio_call_sid = ?
                ''', (call_sid,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting call session by SID: {e}")
            return None
