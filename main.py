"""
HealthCare Plus Voice Assistant - Main Server
==============================================
Entry point for the voice assistant server.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
load_dotenv()

import asyncio
from loguru import logger

from server.assistant import VoiceAssistant
from server.websocket_server import start_server

# Configure logging - File and Console
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Remove default handler
logger.remove(0)

# Add console handler with colored output
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# Add file handler with detailed logging
log_file = log_dir / f"voice_assistant_{datetime.now().strftime('%Y%m%d')}.log"
logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    enqueue=True
)

logger.info("=" * 60)
logger.info("🏥 HEALTHCARE PLUS VOICE ASSISTANT - LOGGING INITIALIZED")
logger.info("=" * 60)
logger.info(f"📝 Log file: {log_file.absolute()}")
logger.info(f"📂 Log directory: {log_dir.absolute()}")
logger.info(f"🔧 Log level: DEBUG (file), INFO (console)")
logger.info("=" * 60)


def check_environment():
    """Verify all required environment variables are set"""
    logger.debug("🔍 Starting environment variable check")
    required_vars = [
        'DEEPGRAM_API_KEY',
        'OPENAI_API_KEY',
        'ELEVENLABS_API_KEY'
    ]
    
    logger.debug(f"📋 Required variables: {required_vars}")
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        logger.error("Please set them in .env file")
        logger.debug(f"Missing vars: {missing}")
        return False
    
    # Log successful loading (without exposing keys)
    for var in required_vars:
        key_length = len(os.getenv(var, ""))
        logger.debug(f"✅ {var}: Loaded (length: {key_length} chars)")
    
    logger.info("✅ All API keys loaded")
    return True


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("🏥 HEALTHCARE PLUS VOICE ASSISTANT")
    logger.info("=" * 60)
    logger.info("Direct Deepgram + OpenAI + ElevenLabs")
    logger.info("Server: ws://localhost:8765")
    logger.info("=" * 60 + "\n")
    
    logger.debug(f"🚀 Application starting at {datetime.now().isoformat()}")
    logger.debug(f"📁 Working directory: {os.getcwd()}")
    logger.debug(f"🐍 Python version: {sys.version}")
    
    if not check_environment():
        logger.error("❌ Environment check failed, exiting")
        return
    
    logger.debug("✅ Environment check passed, starting server")
    
    try:
        logger.debug("🔄 Starting asyncio event loop")
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped by user (KeyboardInterrupt)")
        logger.debug("🛑 KeyboardInterrupt received, shutting down gracefully")
    except Exception as e:
        logger.exception(f"❌ Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
