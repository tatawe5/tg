# Advanced Telegram Calling Bot

A complete Python Telegram bot that makes phone calls using Twilio, plays audio files or generates text-to-speech, and intelligently extracts numbers from spoken responses including 8-digit sequences.

## Features

### Core Functionality
- **Audio Calls**: Upload audio files and play during calls
- **Text-to-Speech Calls**: Convert text to speech with voice customization
- **Number Extraction**: Extract PIN codes, passwords, and numeric sequences of any length (3-20 digits)
- **Call Management**: Complete call flow with status tracking
- **Multi-language Support**: Enhanced number extraction for various formats

### Bot Commands
- `/start` - Initialize bot and show welcome
- `/call <phone_number>` - Make call with uploaded audio
- `/calltts <phone_number> <text>` - Make call with text-to-speech
- `/upload` - Upload audio files for calls
- `/list` - View uploaded files and configurations
- `/delete <id>` - Delete audio files
- `/history` - View call history and responses
- `/help` - Show detailed help

### Advanced Features
- **Inline Keyboards**: Interactive configuration for TTS settings
- **Voice Options**: Multiple voice types (male, female, robotic, etc.)
- **SSML Support**: Advanced speech synthesis markup
- **Number Detection**: Handles "one two three", "1234", "twelve thirty-four"
- **8-Digit Focus**: Optimized extraction for 8-digit sequences
- **Call Recording**: Complete transcription and number extraction

## Setup Instructions

### 1. Required Credentials

#### Telegram Bot Token
1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Copy the bot token

#### Twilio Credentials
1. Sign up at [twilio.com](https://twilio.com)
2. Get Account SID and Auth Token from Console
3. Buy a phone number with Voice capability
4. Note down all three values

### 2. Environment Variables

Set these in your deployment platform:

```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890
BASE_URL=https://your-domain.com
```

### 3. Deployment Options

#### Railway (Recommended)
1. Connect GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Railway auto-provides webhook URL
4. Deploy automatically

#### VPS/Server
1. Clone repository
2. Install Python dependencies
3. Set environment variables
4. Configure domain and SSL
5. Run: `python main.py`

#### Other Platforms
- Heroku: Set environment variables in dashboard
- DigitalOcean: Use App Platform
- Replit: Set secrets in environment

## Usage Guide

### Making Audio Calls
```
/call +1234567890
```
1. Bot shows list of uploaded audio files
2. Select audio file to play
3. Bot initiates call and plays audio
4. Captures and processes response
5. Extracts numbers automatically

### Text-to-Speech Calls
```
/calltts +1234567890 Hello, please provide your 8-digit account number
```
1. Bot shows TTS configuration options
2. Configure voice, language, speed
3. Preview and confirm settings
4. Bot generates speech and makes call
5. Processes response and extracts numbers

### Audio Management
```
/upload          # Upload new audio files
/list            # View all uploaded files
/delete 3        # Delete audio file #3
```

### Call History
```
/history         # View recent calls and responses
```

## Number Extraction Examples

The bot extracts numbers from various speech patterns:

**8-Digit Examples:**
- "My account number is one two three four five six seven eight" → `12345678`
- "It's 1 2 3 4 5 6 7 8" → `12345678`
- "The code is twelve thirty-four fifty-six seventy-eight" → `12345678`

**Other Formats:**
- "PIN is 1234" → `1234`
- "My phone number is 555-123-4567" → `5551234567`
- "Account twelve thirty-four" → `1234`

## Architecture

### Core Components
- **Telegram Bot**: Handles user interaction and commands
- **Twilio Client**: Makes phone calls and processes voice
- **Number Extractor**: Intelligent number extraction from speech
- **Database**: SQLite for storing files, calls, and responses
- **Webhook Server**: Flask server for Twilio callbacks

### Data Flow
1. User sends command via Telegram
2. Bot validates input and shows options
3. User configures call settings
4. Bot initiates Twilio call
5. Twilio plays audio/TTS and records response
6. Bot processes transcription and extracts numbers
7. Results sent back to user via Telegram

## File Structure

```
├── main.py                 # Main entry point
├── telegram_bot.py         # Telegram bot logic
├── webhook_server.py       # Flask webhook server
├── twilio_client.py        # Twilio API integration
├── number_extractor.py     # Number extraction engine
├── tts_config.py          # Text-to-speech configuration
├── database.py            # SQLite database operations
├── config.py              # Configuration management
├── audio_files/           # Uploaded audio storage
└── .env.example           # Environment variables template
```

## Troubleshooting

### Common Issues

**Bot not responding:**
- Check TELEGRAM_BOT_TOKEN is correct
- Verify bot is started with `/start`

**Calls not working:**
- Verify Twilio credentials are correct
- Check phone number has Voice capability
- Ensure webhook URL is accessible

**Numbers not extracted:**
- Check transcription quality in /history
- Verify speech was clear and audible
- Try speaking numbers more distinctly

**Webhook errors:**
- Ensure BASE_URL is publicly accessible
- Check SSL certificate is valid
- Verify port is open and accessible

### Getting Help

1. Check bot logs for error messages
2. Use `/setup` command (admin only) to verify configuration
3. Test with simple 4-digit PIN first
4. Ensure clear speech when testing

## Security Notes

- Keep Twilio Auth Token secret
- Use HTTPS for webhook URLs
- Validate all user inputs
- Store sensitive data in environment variables
- Regular rotate API keys

## License

This project is for educational and legitimate use only. Ensure compliance with local laws and Twilio's terms of service when making phone calls.