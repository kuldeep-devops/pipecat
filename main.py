"""
HealthCare Plus Voice Assistant - Main Server
==============================================
Entry point for the voice assistant server.
"""

import os
from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
load_dotenv()

import asyncio
from loguru import logger

from server.assistant import VoiceAssistant
from server.websocket_server import start_server

# Configure logging
logger.remove(0)
logger.add(lambda msg: print(msg), level="INFO")


def check_environment():
    """Verify all required environment variables are set"""
    required_vars = [
        'DEEPGRAM_API_KEY',
        'OPENAI_API_KEY',
        'ELEVENLABS_API_KEY'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        logger.error("Please set them in .env file")
        return False
    
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
    
    if not check_environment():
        return
    
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped")


if __name__ == "__main__":
    main()
