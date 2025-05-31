#!/usr/bin/env python3
"""
Advanced Telegram Calling Bot with Text-to-Speech
Main entry point that runs both Telegram bot and webhook server
"""

import asyncio
import threading
import logging
import signal
import sys
from telegram_bot import TelegramBot
from webhook_server import run_webhook_server
from config import Config, get_webhook_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

class BotManager:
    """Manages both Telegram bot and webhook server"""
    
    def __init__(self):
        self.telegram_bot = None
        self.webhook_thread = None
        self.running = False
    
    async def start(self):
        """Start both bot and webhook server"""
        try:
            logger.info("🚀 Starting Advanced Telegram Calling Bot...")
            
            # Validate configuration
            if not self._validate_config():
                logger.error("❌ Configuration validation failed")
                return False
            
            # Create Telegram bot
            self.telegram_bot = TelegramBot()
            
            # Start webhook server in separate thread
            logger.info(f"🌐 Starting webhook server on port {Config.WEBHOOK_PORT}")
            self.webhook_thread = threading.Thread(
                target=run_webhook_server,
                args=(self.telegram_bot,),
                daemon=True
            )
            self.webhook_thread.start()
            
            # Wait a moment for webhook server to start
            await asyncio.sleep(2)
            
            # Start Telegram bot
            logger.info("🤖 Starting Telegram bot...")
            self.running = True
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Run bot
            await self.telegram_bot.run()
            
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            return False
    
    def _validate_config(self) -> bool:
        """Validate required configuration"""
        # Check Telegram token (required)
        if not Config.TELEGRAM_BOT_TOKEN or Config.TELEGRAM_BOT_TOKEN.startswith('your_'):
            logger.error("❌ Missing TELEGRAM_BOT_TOKEN")
            return False
        
        # Check Twilio credentials (optional for testing)
        twilio_vars = [
            ('TWILIO_ACCOUNT_SID', Config.TWILIO_ACCOUNT_SID),
            ('TWILIO_AUTH_TOKEN', Config.TWILIO_AUTH_TOKEN),
            ('TWILIO_PHONE_NUMBER', Config.TWILIO_PHONE_NUMBER)
        ]
        
        missing_twilio = []
        for var_name, var_value in twilio_vars:
            if not var_value or var_value.startswith('your_'):
                missing_twilio.append(var_name)
        
        if missing_twilio:
            logger.warning(f"⚠️  Twilio credentials missing: {', '.join(missing_twilio)}")
            logger.warning("🔧 Bot will run in limited mode (no calling functionality)")
            logger.warning("💡 Add Twilio credentials later to enable phone calls")
        else:
            logger.info(f"📞 Twilio Number: {Config.TWILIO_PHONE_NUMBER}")
        
        logger.info("✅ Telegram bot configuration validated")
        logger.info(f"🌐 Webhook URL: {get_webhook_url()}")
        
        return True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)
    
    async def stop(self):
        """Stop bot and webhook server"""
        logger.info("🛑 Stopping bot...")
        self.running = False
        
        if self.telegram_bot:
            # Bot shutdown is handled in telegram_bot.py
            pass

async def main():
    """Main function"""
    bot_manager = BotManager()
    
    try:
        await bot_manager.start()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
    finally:
        await bot_manager.stop()

if __name__ == "__main__":
    # Print startup banner
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                 🤖 TELEGRAM CALLING BOT 📞                   ║
    ║                                                               ║
    ║  Advanced bot for making phone calls with TTS and audio      ║
    ║  • Upload audio files or use text-to-speech                  ║
    ║  • Make calls and capture spoken responses                   ║
    ║  • Intelligent number extraction from speech                 ║
    ║  • Full inline keyboard configuration                        ║
    ║                                                               ║
    ║  🚀 Starting up...                                           ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
