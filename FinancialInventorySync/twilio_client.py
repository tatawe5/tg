from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say, Play, Record, Pause, Hangup
import logging
from typing import Optional, Dict, Any
from config import Config
from tts_config import TTSConfig

logger = logging.getLogger(__name__)

class TwilioVoiceClient:
    """Twilio Voice API client for making calls and handling TTS"""
    
    def __init__(self):
        try:
            if (Config.TWILIO_ACCOUNT_SID and not Config.TWILIO_ACCOUNT_SID.startswith('your_') and
                Config.TWILIO_AUTH_TOKEN and not Config.TWILIO_AUTH_TOKEN.startswith('your_')):
                self.client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
                self.enabled = True
            else:
                self.client = None
                self.enabled = False
                logger.warning("Twilio client disabled - credentials not configured")
        except Exception as e:
            logger.error(f"Twilio client initialization error: {e}")
            self.client = None
            self.enabled = False
        
        self.tts_config = TTSConfig()
    
    def make_audio_call(self, to_number: str, audio_url: str, session_id: int) -> Optional[str]:
        """Initiate a call with uploaded audio file"""
        if not self.enabled:
            logger.warning("Cannot make call - Twilio not configured")
            return None
            
        try:
            # Generate TwiML for audio call
            twiml_url = f"{Config.BASE_URL}/twiml/audio/{session_id}"
            
            call = self.client.calls.create(
                to=to_number,
                from_=Config.TWILIO_PHONE_NUMBER,
                url=twiml_url,
                method='POST',
                timeout=30,
                record=False
            )
            
            logger.info(f"Audio call initiated: {call.sid}")
            return call.sid
            
        except Exception as e:
            logger.error(f"Error making audio call: {e}")
            return None
    
    def make_tts_call(self, to_number: str, session_id: int) -> Optional[str]:
        """Initiate a call with text-to-speech"""
        try:
            # Generate TwiML for TTS call
            twiml_url = f"{Config.BASE_URL}/twiml/tts/{session_id}"
            
            call = self.client.calls.create(
                to=to_number,
                from_=Config.TWILIO_PHONE_NUMBER,
                url=twiml_url,
                method='POST',
                timeout=30,
                record=False
            )
            
            logger.info(f"TTS call initiated: {call.sid}")
            return call.sid
            
        except Exception as e:
            logger.error(f"Error making TTS call: {e}")
            return None
    
    def generate_audio_twiml(self, audio_url: str, session_id: int) -> str:
        """Generate TwiML for audio file playback"""
        response = VoiceResponse()
        
        # Play the audio file
        response.play(audio_url)
        
        # Add a brief pause
        response.pause(length=2)
        
        # Start recording response
        response.record(
            action=f"{Config.BASE_URL}/capture_response/{session_id}",
            method='POST',
            max_length=Config.MAX_LISTENING_DURATION,
            transcribe=True,
            transcribe_callback=f"{Config.BASE_URL}/process_speech/{session_id}",
            play_beep=False,
            finish_on_key='#'
        )
        
        # Hangup after recording
        response.hangup()
        
        logger.info(f"Generated audio TwiML for session {session_id}")
        return str(response)
    
    def generate_tts_twiml(self, text: str, tts_config: Dict[str, Any], session_id: int) -> str:
        """Generate TwiML for text-to-speech"""
        response = VoiceResponse()
        
        try:
            # Generate SSML if enabled
            if tts_config.get('ssml_enabled', False):
                speech_text = self.tts_config.generate_ssml(text, tts_config)
            else:
                speech_text = text
            
            # Create Say element with voice configuration
            say = Say(
                speech_text,
                voice=tts_config.get('voice_name', 'alice'),
                language=tts_config.get('language', 'en-US')
            )
            response.append(say)
            
            # Add pause after TTS
            response.pause(length=2)
            
            # Start recording response
            response.record(
                action=f"{Config.BASE_URL}/capture_response/{session_id}",
                method='POST',
                max_length=Config.MAX_LISTENING_DURATION,
                transcribe=True,
                transcribe_callback=f"{Config.BASE_URL}/process_speech/{session_id}",
                play_beep=False,
                finish_on_key='#'
            )
            
            # Hangup after recording
            response.hangup()
            
            logger.info(f"Generated TTS TwiML for session {session_id}")
            return str(response)
            
        except Exception as e:
            logger.error(f"Error generating TTS TwiML: {e}")
            # Fallback to simple TwiML
            response = VoiceResponse()
            response.say(text, voice='alice')
            response.hangup()
            return str(response)
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        import re
        
        # Remove non-digit characters
        digits_only = re.sub(r'[^\d]', '', phone_number)
        
        # Check if it's a valid length (US/international format)
        if len(digits_only) == 10:  # US format without country code
            return True
        elif len(digits_only) == 11 and digits_only.startswith('1'):  # US with country code
            return True
        elif 10 <= len(digits_only) <= 15:  # International format
            return True
        
        return False
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number for Twilio (E.164 format)"""
        import re
        
        # Remove non-digit characters
        digits_only = re.sub(r'[^\d]', '', phone_number)
        
        # Add country code if missing
        if len(digits_only) == 10:
            digits_only = '1' + digits_only  # Assume US
        
        # Return in E.164 format
        return '+' + digits_only
    
    def get_call_status(self, call_sid: str) -> Optional[str]:
        """Get current status of a call"""
        try:
            call = self.client.calls(call_sid).fetch()
            return call.status
        except Exception as e:
            logger.error(f"Error getting call status: {e}")
            return None
    
    def end_call(self, call_sid: str) -> bool:
        """End an active call"""
        try:
            self.client.calls(call_sid).update(status='completed')
            return True
        except Exception as e:
            logger.error(f"Error ending call: {e}")
            return False
    
    def generate_simple_twiml(self, message: str) -> str:
        """Generate simple TwiML for basic messages"""
        response = VoiceResponse()
        response.say(message, voice='alice')
        response.hangup()
        return str(response)
    
    def handle_recording_callback(self, recording_url: str, session_id: int) -> str:
        """Handle recording completion callback"""
        response = VoiceResponse()
        response.say("Thank you for your response. Goodbye.", voice='alice')
        response.hangup()
        return str(response)
