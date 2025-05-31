import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_bot_token_here")
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_twilio_account_sid")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")
    
    # Application Settings
    BASE_URL = os.getenv("BASE_URL", "https://your-domain.com")
    WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
    WEBHOOK_HOST = "0.0.0.0"
    
    # File Storage
    AUDIO_STORAGE_PATH = "./audio_files"
    DATABASE_PATH = "./bot_database.db"
    
    # Call Settings
    MAX_CALL_DURATION = int(os.getenv("MAX_CALL_DURATION", "300"))  # 5 minutes
    MAX_LISTENING_DURATION = int(os.getenv("MAX_LISTENING_DURATION", "60"))  # 1 minute
    MAX_TTS_TEXT_LENGTH = int(os.getenv("MAX_TTS_TEXT_LENGTH", "4000"))
    MAX_AUDIO_FILE_SIZE = int(os.getenv("MAX_AUDIO_FILE_SIZE", "52428800"))  # 50MB
    
    # Admin Configuration
    ADMIN_USER_IDS = [int(x.strip()) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()]

# Auto-detect deployment platform for webhook URL
def get_webhook_url():
    """Auto-detect webhook URL based on deployment platform"""
    base_url = Config.BASE_URL
    
    # Railway detection
    if os.getenv("RAILWAY_ENVIRONMENT"):
        railway_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")
        if railway_url:
            base_url = f"https://{railway_url}"
    
    # Replit detection
    elif os.getenv("REPLIT_DB_URL"):
        repl_slug = os.getenv("REPL_SLUG", "telegram-bot")
        repl_owner = os.getenv("REPL_OWNER", "user")
        base_url = f"https://{repl_slug}.{repl_owner}.repl.co"
    
    # Heroku detection
    elif os.getenv("DYNO"):
        heroku_app = os.getenv("HEROKU_APP_NAME")
        if heroku_app:
            base_url = f"https://{heroku_app}.herokuapp.com"
    
    return base_url

# Create audio directory if it doesn't exist
os.makedirs(Config.AUDIO_STORAGE_PATH, exist_ok=True)
