import xml.etree.ElementTree as ET
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class TTSConfig:
    """Text-to-Speech configuration and SSML generation"""
    
    def __init__(self):
        self.voices = {
            'male_en': {'name': 'man', 'language': 'en-US', 'gender': 'male'},
            'female_en': {'name': 'alice', 'language': 'en-US', 'gender': 'female'},
            'robotic': {'name': 'Polly.Matthew', 'language': 'en-US', 'gender': 'male'},
            'child': {'name': 'Polly.Justin', 'language': 'en-US', 'gender': 'male'},
            'elderly': {'name': 'Polly.Brian', 'language': 'en-US', 'gender': 'male'},
            'celebrity': {'name': 'Polly.Joanna', 'language': 'en-US', 'gender': 'female'}
        }
        
        self.languages = {
            'en-US': 'English (United States)',
            'en-GB': 'English (United Kingdom)', 
            'es-ES': 'Spanish (Spain)',
            'fr-FR': 'French (France)',
            'de-DE': 'German (Germany)',
            'it-IT': 'Italian (Italy)',
            'ja-JP': 'Japanese (Japan)'
        }
        
        self.speeds = {
            'slow': 0.8,
            'normal': 1.0,
            'fast': 1.2
        }
        
        self.pitches = {
            'low': -5.0,
            'normal': 0.0,
            'high': 5.0
        }
    
    def get_voice_name(self, voice_type: str) -> str:
        """Get voice name from voice type"""
        return self.voices.get(voice_type, {}).get('name', 'alice')
    
    def get_speed_value(self, speed_type: str) -> float:
        """Get speed value from speed type"""
        return self.speeds.get(speed_type, 1.0)
    
    def get_pitch_value(self, pitch_type: str) -> float:
        """Get pitch value from pitch type"""
        return self.pitches.get(pitch_type, 0.0)
    
    def get_voice_display_name(self, voice_type: str) -> str:
        """Get display name for voice type"""
        display_names = {
            'male_en': 'Male Voice',
            'female_en': 'Female Voice',
            'robotic': 'Robotic Voice',
            'child': 'Child Voice',
            'elderly': 'Elderly Voice',
            'celebrity': 'Celebrity Voice'
        }
        return display_names.get(voice_type, voice_type.replace('_', ' ').title())
    
    def generate_ssml(self, text: str, config: Dict[str, Any]) -> str:
        """Generate SSML markup for enhanced TTS"""
        try:
            # Start with basic speak element
            speak = ET.Element('speak')
            speak.set('version', '1.0')
            speak.set('xml:lang', config.get('language', 'en-US'))
            
            # Add prosody controls if specified
            if config.get('speed', 1.0) != 1.0 or config.get('pitch', 0.0) != 0.0:
                prosody = ET.SubElement(speak, 'prosody')
                if config.get('speed', 1.0) != 1.0:
                    prosody.set('rate', f"{config['speed']:.1f}")
                if config.get('pitch', 0.0) != 0.0:
                    prosody.set('pitch', f"{config['pitch']:+.1f}Hz")
                text_element = prosody
            else:
                text_element = speak
            
            # Process text for SSML enhancements
            processed_text = text
            
            if config.get('ssml_pauses', False):
                processed_text = self._add_natural_pauses(processed_text)
            
            if config.get('ssml_emphasis', False):
                processed_text = self._add_emphasis_tags(processed_text)
            
            if config.get('ssml_spell', False):
                processed_text = self._spell_out_numbers(processed_text)
            
            # Set the text content
            text_element.text = processed_text
            
            # Convert to string
            ssml_string = ET.tostring(speak, encoding='unicode')
            logger.info(f"Generated SSML: {ssml_string}")
            return ssml_string
            
        except Exception as e:
            logger.error(f"SSML generation error: {e}")
            return text  # Fallback to plain text
    
    def _add_natural_pauses(self, text: str) -> str:
        """Add natural pauses to text"""
        # Add pauses after sentences and commas
        text = text.replace('.', '.<break time="500ms"/>')
        text = text.replace(',', ',<break time="200ms"/>')
        text = text.replace('?', '?<break time="500ms"/>')
        text = text.replace('!', '!<break time="500ms"/>')
        return text
    
    def _add_emphasis_tags(self, text: str) -> str:
        """Add emphasis to important words"""
        important_words = ['PIN', 'password', 'security', 'verification', 'code', 'account']
        for word in important_words:
            # Case insensitive replacement
            text = text.replace(word.lower(), f'<emphasis level="strong">{word.lower()}</emphasis>')
            text = text.replace(word.upper(), f'<emphasis level="strong">{word.upper()}</emphasis>')
            text = text.replace(word.title(), f'<emphasis level="strong">{word.title()}</emphasis>')
        return text
    
    def _spell_out_numbers(self, text: str) -> str:
        """Convert numbers to spelled out format"""
        import re
        def replace_numbers(match):
            number = match.group()
            return f'<say-as interpret-as="spell-out">{number}</say-as>'
        
        return re.sub(r'\b\d+\b', replace_numbers, text)
    
    def validate_tts_text(self, text: str, max_length: int = 4000) -> tuple[bool, str]:
        """Validate TTS text for length and content"""
        if not text or not text.strip():
            return False, "Text cannot be empty"
        
        if len(text) > max_length:
            return False, f"Text too long (max {max_length} characters)"
        
        # Check for potentially problematic characters
        problematic_chars = ['<', '>', '&'] if not text.startswith('<speak') else []
        for char in problematic_chars:
            if char in text:
                return False, f"Text contains problematic character: {char}"
        
        return True, "Valid"
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default TTS configuration"""
        return {
            'voice_name': 'alice',
            'language': 'en-US',
            'speed': 1.0,
            'pitch': 0.0,
            'ssml_enabled': False,
            'ssml_pauses': False,
            'ssml_emphasis': False,
            'ssml_spell': False,
            'ssml_prosody': False,
            'ssml_volume': False,
            'ssml_breaks': False
        }
    
    def format_config_summary(self, config: Dict[str, Any], text: str) -> str:
        """Format configuration summary for display"""
        voice_display = self.get_voice_display_name(config.get('voice_type', 'female_en'))
        
        summary = f"🎙️ TTS Configuration:\n\n"
        summary += f"📝 Text: {text[:100]}{'...' if len(text) > 100 else ''}\n"
        summary += f"🗣️ Voice: {voice_display}\n"
        summary += f"🌍 Language: {config.get('language', 'en-US')}\n"
        summary += f"🎵 Speed: {config.get('speed', 1.0)}\n"
        summary += f"📊 Pitch: {config.get('pitch', 0.0)}\n"
        
        ssml_features = []
        if config.get('ssml_pauses'): ssml_features.append('Pauses')
        if config.get('ssml_emphasis'): ssml_features.append('Emphasis')
        if config.get('ssml_spell'): ssml_features.append('Spell Numbers')
        
        summary += f"⚙️ SSML: {', '.join(ssml_features) if ssml_features else 'Disabled'}\n"
        
        return summary
