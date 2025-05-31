import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from database import Database
from twilio_client import TwilioVoiceClient
from tts_config import TTSConfig
from config import Config
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBot:
    """Main Telegram bot class with all command handlers"""
    
    def __init__(self):
        self.db = Database(Config.DATABASE_PATH)
        self.twilio_client = TwilioVoiceClient()
        self.tts_config = TTSConfig()
        
        # Create application
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command and callback handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("call", self.call_command))
        self.application.add_handler(CommandHandler("calltts", self.calltts_command))
        self.application.add_handler(CommandHandler("upload", self.upload_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("delete", self.delete_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("setup", self.setup_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.AUDIO, self.handle_audio_upload))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_audio_upload))
        self.application.add_handler(MessageHandler(filters.Document.AUDIO, self.handle_audio_upload))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 Welcome to the Advanced Telegram Calling Bot!

This bot can make phone calls using either uploaded audio files or text-to-speech, and extract numbers from responses.

📋 Available Commands:
/call <number> - Make call with uploaded audio
/calltts <number> <text> - Make call with text-to-speech
/upload - Upload audio files
/list - View uploaded files and TTS configs
/delete <id> - Delete audio file
/history - View call history
/setup - Configure bot settings (admin only)
/help - Show detailed help

🔧 Getting Started:
1. Upload audio files with /upload
2. Make calls with /call +1234567890
3. Or use TTS with /calltts +1234567890 Hello, please provide your PIN

Let's get started! 🚀
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
📚 Detailed Help - Telegram Calling Bot

🎵 AUDIO CALLS:
/call <phone_number> - Start call with audio selection
Example: /call +1234567890

📝 TEXT-TO-SPEECH CALLS:
/calltts <phone_number> <text>
Example: /calltts +1234567890 Hello, please provide your PIN number

📁 AUDIO MANAGEMENT:
/upload - Upload audio files (MP3, WAV, M4A)
/list - View all uploaded files and saved TTS configs
/delete <audio_id> - Delete specific audio file

📊 CALL TRACKING:
/history - View recent call history and responses
         - Shows transcriptions and extracted numbers

⚙️ CONFIGURATION:
/setup - Admin-only settings configuration

🔢 NUMBER EXTRACTION:
The bot automatically extracts numbers from speech responses including:
- PIN codes (4-8 digits)
- Phone numbers (10+ digits) 
- Account numbers (6+ digits)
- Any sequence of 3+ spoken/typed digits

Supported formats: "one two three four", "1234", "twelve thirty-four"

📞 Call Flow:
1. Bot calls the number
2. Plays your audio or TTS
3. Records the response (up to 60 seconds)
4. Extracts numbers automatically
5. Sends results to you via Telegram

💡 Tips:
- Upload multiple audio files for different scenarios
- Use clear, natural language for TTS
- Numbers are extracted automatically from any speech
- Check /history to review past calls and responses

Need help? Contact support! 🆘
        """
        await update.message.reply_text(help_message)
    
    async def call_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /call command for audio calls"""
        user_id = update.effective_user.id
        
        # Parse command arguments
        if len(context.args) != 1:
            await update.message.reply_text(
                "❌ Usage: /call <phone_number>\n"
                "Example: /call +1234567890"
            )
            return
        
        phone_number = context.args[0]
        
        # Validate phone number
        if not self.twilio_client.validate_phone_number(phone_number):
            await update.message.reply_text("❌ Invalid phone number format")
            return
        
        # Format phone number
        formatted_number = self.twilio_client.format_phone_number(phone_number)
        
        # Get user's audio files
        audio_files = self.db.get_user_audio_files(user_id)
        
        if not audio_files:
            await update.message.reply_text(
                "❌ No audio files uploaded. Use /upload to add audio files first."
            )
            return
        
        # Save call context in user session
        self.db.save_user_session(user_id, {
            'action': 'audio_call',
            'phone_number': formatted_number,
            'audio_files': audio_files
        })
        
        # Create audio selection keyboard
        keyboard = self._create_audio_selection_keyboard(audio_files)
        
        await update.message.reply_text(
            f"📞 Setting up call to: {formatted_number}\n\n"
            f"Select audio file to play:",
            reply_markup=keyboard
        )
    
    async def calltts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /calltts command for TTS calls"""
        user_id = update.effective_user.id
        
        # Parse command arguments
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: /calltts <phone_number> <text>\n"
                "Example: /calltts +1234567890 Hello, please provide your PIN number"
            )
            return
        
        phone_number = context.args[0]
        tts_text = ' '.join(context.args[1:])
        
        # Validate phone number
        if not self.twilio_client.validate_phone_number(phone_number):
            await update.message.reply_text("❌ Invalid phone number format")
            return
        
        # Validate TTS text
        is_valid, error_msg = self.tts_config.validate_tts_text(tts_text)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return
        
        # Format phone number
        formatted_number = self.twilio_client.format_phone_number(phone_number)
        
        # Save TTS call context in user session
        tts_config = self.tts_config.get_default_config()
        self.db.save_user_session(user_id, {
            'action': 'tts_call',
            'phone_number': formatted_number,
            'tts_text': tts_text,
            'tts_config': tts_config
        })
        
        # Create TTS configuration keyboard
        keyboard = self._create_tts_main_keyboard()
        
        await update.message.reply_text(
            f"📞 Setting up TTS call to: {formatted_number}\n"
            f"📝 Text: {tts_text[:100]}{'...' if len(tts_text) > 100 else ''}\n\n"
            f"Configure your text-to-speech settings:",
            reply_markup=keyboard
        )
    
    async def upload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /upload command"""
        await update.message.reply_text(
            "📁 Send me an audio file to upload!\n\n"
            "Supported formats: MP3, WAV, M4A, OGG\n"
            "Maximum size: 50MB\n\n"
            "You can send:\n"
            "• Audio files as documents\n"
            "• Voice messages\n"
            "• Music files\n\n"
            "The file will be processed and added to your audio library."
        )
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command"""
        user_id = update.effective_user.id
        
        # Get audio files
        audio_files = self.db.get_user_audio_files(user_id)
        
        message = "📋 Your Audio Library:\n\n"
        
        if audio_files:
            message += "📁 Uploaded Audio Files:\n"
            for i, audio in enumerate(audio_files, 1):
                duration = f" ({audio['duration']}s)" if audio['duration'] else ""
                size_mb = f" - {audio['file_size'] / 1024 / 1024:.1f}MB" if audio['file_size'] else ""
                message += f"{i}. {audio['filename']}{duration}{size_mb}\n"
        else:
            message += "❌ No audio files uploaded yet.\n"
        
        message += "\n💡 Use /upload to add new audio files"
        message += "\n🗑️ Use /delete <number> to remove files"
        
        # Create management keyboard
        keyboard = self._create_list_management_keyboard()
        
        await update.message.reply_text(message, reply_markup=keyboard)
    
    async def delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /delete command"""
        user_id = update.effective_user.id
        
        if len(context.args) != 1:
            await update.message.reply_text(
                "❌ Usage: /delete <audio_id>\n"
                "Use /list to see audio file IDs"
            )
            return
        
        try:
            audio_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid audio ID. Must be a number.")
            return
        
        # Delete audio file
        if self.db.delete_audio_file(user_id, audio_id):
            # Also delete physical file
            try:
                audio_files = self.db.get_user_audio_files(user_id)
                for audio in audio_files:
                    if audio['id'] == audio_id and os.path.exists(audio['file_path']):
                        os.remove(audio['file_path'])
                        break
            except Exception as e:
                logger.warning(f"Could not delete physical file: {e}")
            
            await update.message.reply_text("✅ Audio file deleted successfully!")
        else:
            await update.message.reply_text("❌ Audio file not found or could not be deleted.")
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        user_id = update.effective_user.id
        
        # Get call history
        history = self.db.get_call_history(user_id, limit=10)
        
        if not history:
            await update.message.reply_text(
                "📊 No call history found.\n\n"
                "Make your first call with /call or /calltts!"
            )
            return
        
        message = "📊 Recent Call History:\n\n"
        
        for i, call in enumerate(history, 1):
            message += f"📞 Call #{i}\n"
            message += f"📱 Number: {call['phone_number']}\n"
            message += f"🕐 Date: {call['start_time']}\n"
            message += f"📊 Status: {call['status']}\n"
            
            if call['full_transcription']:
                message += f"🎤 Response: \"{call['full_transcription'][:100]}...\"\n"
            
            if call['extracted_numbers']:
                message += f"🔢 Numbers: {call['extracted_numbers']}\n"
            
            message += "─" * 30 + "\n\n"
        
        # Split message if too long
        if len(message) > 4000:
            messages = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for msg in messages:
                await update.message.reply_text(msg)
        else:
            await update.message.reply_text(message)
    
    async def setup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setup command (admin only)"""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if user_id not in Config.ADMIN_USER_IDS:
            await update.message.reply_text("❌ This command is only available to administrators.")
            return
        
        setup_message = f"""
⚙️ Bot Configuration:

🔑 Current Settings:
• Twilio Account: {Config.TWILIO_ACCOUNT_SID[:8]}...
• Twilio Number: {Config.TWILIO_PHONE_NUMBER}
• Webhook URL: {Config.BASE_URL}
• Max Call Duration: {Config.MAX_CALL_DURATION}s
• Max Listening: {Config.MAX_LISTENING_DURATION}s

📊 Database Status:
• Audio files stored: {len(os.listdir(Config.AUDIO_STORAGE_PATH))}
• Database path: {Config.DATABASE_PATH}

🌐 Environment:
• Base URL: {Config.BASE_URL}
• Webhook Port: {Config.WEBHOOK_PORT}

✅ Bot is configured and ready!
        """
        await update.message.reply_text(setup_message)
    
    async def handle_audio_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle audio file uploads"""
        user_id = update.effective_user.id
        
        try:
            # Get file object
            if update.message.audio:
                file_obj = update.message.audio
                file_type = "audio"
            elif update.message.voice:
                file_obj = update.message.voice
                file_type = "voice"
            elif update.message.document and update.message.document.mime_type.startswith('audio'):
                file_obj = update.message.document
                file_type = "document"
            else:
                await update.message.reply_text("❌ Please send an audio file.")
                return
            
            # Check file size
            if file_obj.file_size > Config.MAX_AUDIO_FILE_SIZE:
                await update.message.reply_text(
                    f"❌ File too large. Maximum size is {Config.MAX_AUDIO_FILE_SIZE / 1024 / 1024:.1f}MB"
                )
                return
            
            # Send processing message
            processing_msg = await update.message.reply_text("📥 Processing audio file...")
            
            # Download file
            file = await file_obj.get_file()
            filename = getattr(file_obj, 'file_name', f"audio_{int(time.time())}.ogg")
            
            # Ensure audio directory exists
            os.makedirs(Config.AUDIO_STORAGE_PATH, exist_ok=True)
            
            # Create unique filename
            file_path = os.path.join(Config.AUDIO_STORAGE_PATH, f"{user_id}_{int(time.time())}_{filename}")
            
            # Download file
            await file.download_to_drive(file_path)
            
            # Get file info
            duration = getattr(file_obj, 'duration', None)
            file_size = file_obj.file_size
            
            # Save to database
            audio_id = self.db.save_audio_file(
                user_id=user_id,
                file_id=file_obj.file_id,
                filename=filename,
                file_path=file_path,
                duration=duration,
                file_size=file_size,
                format=file_type
            )
            
            # Update message
            await processing_msg.edit_text(
                f"✅ Audio file uploaded successfully!\n\n"
                f"📁 File: {filename}\n"
                f"⏱️ Duration: {duration}s\n" if duration else ""
                f"💾 Size: {file_size / 1024 / 1024:.1f}MB\n"
                f"🆔 ID: {audio_id}\n\n"
                f"Use /call <number> to make calls with this audio!"
            )
            
        except Exception as e:
            logger.error(f"Error handling audio upload: {e}")
            await update.message.reply_text(f"❌ Error processing audio file: {str(e)}")
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        try:
            # Get user session
            session = self.db.get_user_session(user_id)
            
            if data.startswith("audio_"):
                await self._handle_audio_callback(query, session, data)
            elif data.startswith("tts_") or data.startswith("config_") or data.startswith("voice_") or data.startswith("lang_") or data.startswith("speed_") or data.startswith("pitch_") or data.startswith("ssml_"):
                await self._handle_tts_callback(query, session, data)
            elif data == "start_call" or data == "confirm_tts_call":
                await self._handle_call_start(query, session)
            elif data == "cancel_call":
                await self._handle_call_cancel(query, session)
            elif data == "back_to_main":
                await self._handle_back_to_main(query, session)
            
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def _handle_audio_callback(self, query, session, data):
        """Handle audio selection callbacks"""
        if data == "audio_cancel":
            await query.edit_message_text("❌ Audio call cancelled.")
            self.db.clear_user_session(query.from_user.id)
            return
        
        # Extract audio ID
        audio_id = int(data.split("_")[1])
        
        # Update session with selected audio
        session['selected_audio_id'] = audio_id
        self.db.save_user_session(query.from_user.id, session)
        
        # Get audio file info
        audio_files = session.get('audio_files', [])
        selected_audio = next((a for a in audio_files if a['id'] == audio_id), None)
        
        if not selected_audio:
            await query.edit_message_text("❌ Audio file not found.")
            return
        
        # Show confirmation
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Call", callback_data="start_call")],
            [InlineKeyboardButton("🔄 Choose Different Audio", callback_data="audio_reselect")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_call")]
        ])
        
        await query.edit_message_text(
            f"📞 Ready to call: {session['phone_number']}\n"
            f"🎵 Audio: {selected_audio['filename']}\n"
            f"⏱️ Duration: {selected_audio.get('duration', 'Unknown')}s\n\n"
            f"Confirm to start the call:",
            reply_markup=keyboard
        )
    
    async def _handle_tts_callback(self, query, session, data):
        """Handle TTS configuration callbacks"""
        user_id = query.from_user.id
        
        if data == "config_voice":
            keyboard = self._create_voice_selection_keyboard()
            await query.edit_message_text(
                "🗣️ Select a voice for your call:",
                reply_markup=keyboard
            )
        
        elif data == "config_language":
            keyboard = self._create_language_selection_keyboard()
            await query.edit_message_text(
                "🌍 Select language for text-to-speech:",
                reply_markup=keyboard
            )
        
        elif data == "config_settings":
            keyboard = self._create_voice_settings_keyboard()
            await query.edit_message_text(
                "🎵 Configure voice speed and pitch:",
                reply_markup=keyboard
            )
        
        elif data == "config_ssml":
            keyboard = self._create_ssml_options_keyboard()
            await query.edit_message_text(
                "⚙️ Advanced SSML options:",
                reply_markup=keyboard
            )
        
        elif data.startswith("voice_"):
            voice_type = data.split("_", 1)[1]
            session['tts_config']['voice_name'] = self.tts_config.get_voice_name(voice_type)
            session['tts_config']['voice_type'] = voice_type
            self.db.save_user_session(user_id, session)
            
            await query.edit_message_text(
                f"✅ Voice selected: {self.tts_config.get_voice_display_name(voice_type)}\n\n"
                f"Configure more settings:",
                reply_markup=self._create_tts_main_keyboard()
            )
        
        elif data.startswith("lang_"):
            language = data.split("_", 1)[1]
            session['tts_config']['language'] = language
            self.db.save_user_session(user_id, session)
            
            await query.edit_message_text(
                f"✅ Language selected: {language}\n\n"
                f"Configure more settings:",
                reply_markup=self._create_tts_main_keyboard()
            )
        
        elif data.startswith("speed_"):
            speed_type = data.split("_", 1)[1]
            session['tts_config']['speed'] = self.tts_config.get_speed_value(speed_type)
            self.db.save_user_session(user_id, session)
            
            await query.edit_message_text(
                f"✅ Speed set to: {speed_type}\n\n"
                f"Configure more settings:",
                reply_markup=self._create_tts_main_keyboard()
            )
        
        elif data.startswith("pitch_"):
            pitch_type = data.split("_", 1)[1]
            session['tts_config']['pitch'] = self.tts_config.get_pitch_value(pitch_type)
            self.db.save_user_session(user_id, session)
            
            await query.edit_message_text(
                f"✅ Pitch set to: {pitch_type}\n\n"
                f"Configure more settings:",
                reply_markup=self._create_tts_main_keyboard()
            )
        
        elif data.startswith("ssml_"):
            ssml_option = data.split("_", 1)[1]
            session['tts_config']['ssml_enabled'] = True
            session['tts_config'][f'ssml_{ssml_option}'] = True
            self.db.save_user_session(user_id, session)
            
            await query.edit_message_text(
                f"✅ SSML option enabled: {ssml_option}\n\n"
                f"Configure more settings:",
                reply_markup=self._create_tts_main_keyboard()
            )
        
        elif data == "tts_start_call":
            # Show configuration summary
            config = session['tts_config']
            text = session['tts_text']
            phone_number = session['phone_number']
            
            summary = self.tts_config.format_config_summary(config, text)
            summary += f"📞 Number: {phone_number}\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm & Call", callback_data="confirm_tts_call")],
                [InlineKeyboardButton("✏️ Edit Settings", callback_data="back_to_main")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_call")]
            ])
            
            await query.edit_message_text(summary, reply_markup=keyboard)
    
    async def _handle_call_start(self, query, session):
        """Handle call initiation"""
        user_id = query.from_user.id
        
        try:
            if session['action'] == 'audio_call':
                # Audio call
                audio_id = session['selected_audio_id']
                phone_number = session['phone_number']
                
                # Create call session
                session_id = self.db.create_call_session(
                    user_id=user_id,
                    phone_number=phone_number,
                    call_type='audio',
                    audio_file_id=audio_id
                )
                
                # Initiate call
                call_sid = self.twilio_client.make_audio_call(
                    phone_number, 
                    f"{Config.BASE_URL}/audio/{session_id}",
                    session_id
                )
                
                if call_sid:
                    self.db.update_call_session(session_id, twilio_call_sid=call_sid, status='initiated')
                    await query.edit_message_text(
                        f"📞 Calling {phone_number}...\n"
                        f"🎵 Audio will play when answered\n"
                        f"🎤 Listening for response after playback\n\n"
                        f"Call ID: {call_sid[:8]}..."
                    )
                else:
                    await query.edit_message_text("❌ Failed to initiate call. Please try again.")
            
            elif session['action'] == 'tts_call':
                # TTS call
                text = session['tts_text']
                config = session['tts_config']
                phone_number = session['phone_number']
                
                # Save TTS config
                tts_config_id = self.db.save_tts_config(user_id, text, config)
                
                # Create call session
                session_id = self.db.create_call_session(
                    user_id=user_id,
                    phone_number=phone_number,
                    call_type='tts',
                    tts_config_id=tts_config_id
                )
                
                # Initiate call
                call_sid = self.twilio_client.make_tts_call(phone_number, session_id)
                
                if call_sid:
                    self.db.update_call_session(session_id, twilio_call_sid=call_sid, status='initiated')
                    await query.edit_message_text(
                        f"📞 Calling {phone_number}...\n"
                        f"🎙️ TTS will play when answered\n"
                        f"🎤 Listening for response after playback\n\n"
                        f"Call ID: {call_sid[:8]}..."
                    )
                else:
                    await query.edit_message_text("❌ Failed to initiate call. Please try again.")
            
            # Clear session
            self.db.clear_user_session(user_id)
            
        except Exception as e:
            logger.error(f"Error starting call: {e}")
            await query.edit_message_text(f"❌ Error starting call: {str(e)}")
    
    async def _handle_call_cancel(self, query, session):
        """Handle call cancellation"""
        await query.edit_message_text("❌ Call cancelled.")
        self.db.clear_user_session(query.from_user.id)
    
    async def _handle_back_to_main(self, query, session):
        """Handle back to main menu"""
        if session.get('action') == 'tts_call':
            keyboard = self._create_tts_main_keyboard()
            await query.edit_message_text(
                "Configure your text-to-speech settings:",
                reply_markup=keyboard
            )
        else:
            await query.edit_message_text("❌ Session expired. Please start over.")
    
    def _create_audio_selection_keyboard(self, audio_files):
        """Create keyboard for audio file selection"""
        keyboard = []
        for audio in audio_files:
            duration = f" ({audio['duration']}s)" if audio['duration'] else ""
            button_text = f"🎵 {audio['filename']}{duration}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"audio_{audio['id']}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel Call", callback_data="audio_cancel")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _create_tts_main_keyboard(self):
        """Create main TTS configuration keyboard"""
        keyboard = [
            [InlineKeyboardButton("🗣️ Select Voice", callback_data="config_voice"),
             InlineKeyboardButton("🌍 Select Language", callback_data="config_language")],
            [InlineKeyboardButton("🎵 Voice Settings", callback_data="config_settings"),
             InlineKeyboardButton("⚙️ Advanced SSML", callback_data="config_ssml")],
            [InlineKeyboardButton("▶️ Start Call Now", callback_data="tts_start_call")],
            [InlineKeyboardButton("❌ Cancel Call", callback_data="cancel_call")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_voice_selection_keyboard(self):
        """Create voice selection keyboard"""
        keyboard = [
            [InlineKeyboardButton("👨 Male Voice", callback_data="voice_male_en")],
            [InlineKeyboardButton("👩 Female Voice", callback_data="voice_female_en")],
            [InlineKeyboardButton("🤖 Robotic Voice", callback_data="voice_robotic")],
            [InlineKeyboardButton("👦 Child Voice", callback_data="voice_child")],
            [InlineKeyboardButton("👴 Elderly Voice", callback_data="voice_elderly")],
            [InlineKeyboardButton("🎭 Celebrity Voice", callback_data="voice_celebrity")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_language_selection_keyboard(self):
        """Create language selection keyboard"""
        keyboard = [
            [InlineKeyboardButton("🇺🇸 English (US)", callback_data="lang_en-US")],
            [InlineKeyboardButton("🇬🇧 English (UK)", callback_data="lang_en-GB")],
            [InlineKeyboardButton("🇪🇸 Spanish", callback_data="lang_es-ES")],
            [InlineKeyboardButton("🇫🇷 French", callback_data="lang_fr-FR")],
            [InlineKeyboardButton("🇩🇪 German", callback_data="lang_de-DE")],
            [InlineKeyboardButton("🇮🇹 Italian", callback_data="lang_it-IT")],
            [InlineKeyboardButton("🇯🇵 Japanese", callback_data="lang_ja-JP")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_voice_settings_keyboard(self):
        """Create voice settings keyboard"""
        keyboard = [
            [InlineKeyboardButton("🐌 Slow Speed", callback_data="speed_slow"),
             InlineKeyboardButton("🚶 Normal Speed", callback_data="speed_normal"),
             InlineKeyboardButton("🏃 Fast Speed", callback_data="speed_fast")],
            [InlineKeyboardButton("🔉 Low Pitch", callback_data="pitch_low"),
             InlineKeyboardButton("🔊 Normal Pitch", callback_data="pitch_normal"),
             InlineKeyboardButton("📢 High Pitch", callback_data="pitch_high")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_ssml_options_keyboard(self):
        """Create SSML options keyboard"""
        keyboard = [
            [InlineKeyboardButton("⏸️ Add Pauses", callback_data="ssml_pauses")],
            [InlineKeyboardButton("📈 Emphasis", callback_data="ssml_emphasis")],
            [InlineKeyboardButton("🎼 Prosody Control", callback_data="ssml_prosody")],
            [InlineKeyboardButton("🔤 Spell Numbers", callback_data="ssml_spell")],
            [InlineKeyboardButton("📢 Volume Control", callback_data="ssml_volume")],
            [InlineKeyboardButton("💬 Break Sentences", callback_data="ssml_breaks")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_list_management_keyboard(self):
        """Create list management keyboard"""
        keyboard = [
            [InlineKeyboardButton("➕ Upload Audio", callback_data="upload_new")],
            [InlineKeyboardButton("🎤 Create TTS", callback_data="create_tts")],
            [InlineKeyboardButton("📊 View History", callback_data="view_history")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def run(self):
        """Run the bot"""
        logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    @property
    def bot(self):
        """Get bot instance for webhook server"""
        return self.application.bot
