from flask import Flask, request, jsonify, send_file
import logging
from database import Database
from twilio_client import TwilioVoiceClient
from number_extractor import NumberExtractor
from config import Config, get_webhook_url
import os
import threading
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebhookServer:
    """Flask server to handle Twilio webhooks"""
    
    def __init__(self, telegram_bot=None):
        self.app = Flask(__name__)
        self.db = Database(Config.DATABASE_PATH)
        self.twilio_client = TwilioVoiceClient()
        self.number_extractor = NumberExtractor()
        self.telegram_bot = telegram_bot
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register all webhook routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({"status": "healthy", "service": "telegram-bot-webhooks"})
        
        @self.app.route('/twiml/audio/<int:session_id>', methods=['POST'])
        def audio_twiml(session_id):
            """Generate TwiML for audio file playback"""
            try:
                # Get audio file URL from session
                audio_url = f"{get_webhook_url()}/audio/{session_id}"
                twiml = self.twilio_client.generate_audio_twiml(audio_url, session_id)
                
                return twiml, 200, {'Content-Type': 'text/xml'}
            except Exception as e:
                logger.error(f"Error generating audio TwiML: {e}")
                return self.twilio_client.generate_simple_twiml("Sorry, there was an error.")
        
        @self.app.route('/twiml/tts/<int:session_id>', methods=['POST'])
        def tts_twiml(session_id):
            """Generate TwiML for text-to-speech"""
            try:
                # Get TTS configuration from database
                call_session = self._get_call_session(session_id)
                if not call_session:
                    return self.twilio_client.generate_simple_twiml("Session not found.")
                
                tts_config_id = call_session.get('tts_config_id')
                if not tts_config_id:
                    return self.twilio_client.generate_simple_twiml("TTS configuration not found.")
                
                tts_config, text = self._get_tts_config(tts_config_id)
                twiml = self.twilio_client.generate_tts_twiml(text, tts_config, session_id)
                
                return twiml, 200, {'Content-Type': 'text/xml'}
            except Exception as e:
                logger.error(f"Error generating TTS TwiML: {e}")
                return self.twilio_client.generate_simple_twiml("Sorry, there was an error.")
        
        @self.app.route('/audio/<int:session_id>', methods=['GET'])
        def serve_audio(session_id):
            """Serve audio file for playback"""
            try:
                # Get audio file path from session
                call_session = self._get_call_session(session_id)
                if not call_session:
                    return "Audio file not found", 404
                
                audio_file_id = call_session.get('audio_file_id')
                if not audio_file_id:
                    return "Audio file not found", 404
                
                audio_file = self._get_audio_file(audio_file_id)
                if not audio_file or not os.path.exists(audio_file['file_path']):
                    return "Audio file not found", 404
                
                return send_file(
                    audio_file['file_path'],
                    mimetype='audio/wav',
                    as_attachment=False
                )
            except Exception as e:
                logger.error(f"Error serving audio: {e}")
                return "Error serving audio", 500
        
        @self.app.route('/capture_response/<int:session_id>', methods=['POST'])
        def capture_response(session_id):
            """Handle call response capture"""
            try:
                # Get recording URL and other data
                recording_url = request.form.get('RecordingUrl')
                call_sid = request.form.get('CallSid')
                
                logger.info(f"Captured response for session {session_id}: {recording_url}")
                
                # Update call session
                self.db.update_call_session(
                    session_id,
                    status='recording_captured',
                    twilio_call_sid=call_sid
                )
                
                # Generate response TwiML
                return self.twilio_client.handle_recording_callback(recording_url, session_id)
                
            except Exception as e:
                logger.error(f"Error capturing response: {e}")
                return self.twilio_client.generate_simple_twiml("Thank you.")
        
        @self.app.route('/process_speech/<int:session_id>', methods=['POST'])
        def process_speech(session_id):
            """Process speech transcription and extract numbers"""
            try:
                # Get transcription from Twilio
                transcription_text = request.form.get('TranscriptionText', '')
                transcription_status = request.form.get('TranscriptionStatus')
                call_sid = request.form.get('CallSid')
                
                logger.info(f"Processing speech for session {session_id}: {transcription_text}")
                
                if transcription_status == 'completed' and transcription_text:
                    # Extract numbers from transcription
                    extracted_numbers, confidence = self.number_extractor.extract_numbers_from_speech(
                        transcription_text
                    )
                    
                    # Save response to database
                    numbers_str = ', '.join(extracted_numbers) if extracted_numbers else 'None'
                    self.db.save_voice_response(
                        session_id, transcription_text, numbers_str, confidence
                    )
                    
                    # Update call session
                    self.db.update_call_session(
                        session_id,
                        status='completed',
                        end_time='CURRENT_TIMESTAMP'
                    )
                    
                    # Send results to Telegram user
                    if self.telegram_bot:
                        self._send_results_to_user(session_id, transcription_text, extracted_numbers)
                
                return jsonify({"status": "processed"})
                
            except Exception as e:
                logger.error(f"Error processing speech: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/call_status/<int:session_id>', methods=['POST'])
        def call_status_callback(session_id):
            """Handle call status updates"""
            try:
                call_status = request.form.get('CallStatus')
                call_sid = request.form.get('CallSid')
                
                logger.info(f"Call status update for session {session_id}: {call_status}")
                
                # Update call session with status
                self.db.update_call_session(
                    session_id,
                    status=call_status,
                    twilio_call_sid=call_sid
                )
                
                # Notify user of status changes
                if self.telegram_bot:
                    self._notify_user_of_status(session_id, call_status)
                
                return jsonify({"status": "updated"})
                
            except Exception as e:
                logger.error(f"Error updating call status: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _get_call_session(self, session_id: int) -> dict:
        """Get call session from database"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM call_sessions WHERE id = ?', (session_id,))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            logger.error(f"Error getting call session: {e}")
            return None
    
    def _get_tts_config(self, tts_config_id: int) -> tuple:
        """Get TTS configuration from database"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tts_configs WHERE id = ?', (tts_config_id,))
                result = cursor.fetchone()
                if result:
                    config_data = dict(result)
                    
                    # Build config dictionary
                    config = {
                        'voice_name': config_data['voice_name'],
                        'language': config_data['language'],
                        'speed': config_data['speed'],
                        'pitch': config_data['pitch'],
                        'ssml_enabled': config_data['ssml_enabled']
                    }
                    
                    return config, config_data['text_content']
                return {}, ""
        except Exception as e:
            logger.error(f"Error getting TTS config: {e}")
            return {}, ""
    
    def _get_audio_file(self, audio_file_id: int) -> dict:
        """Get audio file info from database"""
        try:
            with self.db.conn:
                cursor = self.db.conn.cursor()
                cursor.execute('SELECT * FROM audio_files WHERE id = ?', (audio_file_id,))
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            logger.error(f"Error getting audio file: {e}")
            return None
    
    def _send_results_to_user(self, session_id: int, transcription: str, extracted_numbers: list):
        """Send call results to Telegram user"""
        try:
            # Get call session to find user
            call_session = self._get_call_session(session_id)
            if not call_session:
                return
            
            user_id = call_session['user_id']
            phone_number = call_session['phone_number']
            
            # Format results message
            message = f"📞 Call completed to {phone_number}\n\n"
            message += f"🎤 Full response:\n\"{transcription}\"\n\n"
            
            if extracted_numbers:
                message += f"🔢 Numbers extracted: {', '.join(extracted_numbers)}\n"
            else:
                message += "❌ No numbers detected in response\n"
            
            # Send via Telegram bot
            if self.telegram_bot:
                import asyncio
                asyncio.create_task(
                    self.telegram_bot.bot.send_message(chat_id=user_id, text=message)
                )
                
        except Exception as e:
            logger.error(f"Error sending results to user: {e}")
    
    def _notify_user_of_status(self, session_id: int, status: str):
        """Notify user of call status changes"""
        try:
            call_session = self._get_call_session(session_id)
            if not call_session:
                return
            
            user_id = call_session['user_id']
            
            status_messages = {
                'ringing': '📞 Phone is ringing...',
                'in-progress': '✅ Call answered! Playing audio...',
                'completed': '🏁 Call ended',
                'busy': '📵 Line busy - call failed',
                'no-answer': '📞 No answer - call failed',
                'failed': '❌ Call failed'
            }
            
            message = status_messages.get(status, f"📊 Call status: {status}")
            
            if self.telegram_bot and status in status_messages:
                import asyncio
                asyncio.create_task(
                    self.telegram_bot.bot.send_message(chat_id=user_id, text=message)
                )
                
        except Exception as e:
            logger.error(f"Error notifying user of status: {e}")
    
    def run(self):
        """Run the webhook server"""
        try:
            logger.info(f"Starting webhook server on {Config.WEBHOOK_HOST}:{Config.WEBHOOK_PORT}")
            self.app.run(
                host=Config.WEBHOOK_HOST,
                port=Config.WEBHOOK_PORT,
                debug=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Error starting webhook server: {e}")
            raise

def run_webhook_server(telegram_bot=None):
    """Function to run webhook server in a separate thread"""
    server = WebhookServer(telegram_bot)
    server.run()
