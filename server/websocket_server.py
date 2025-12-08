"""
WebSocket Server
"""

import asyncio
import websockets
from loguru import logger

from config.settings import config
from server.assistant import VoiceAssistant


async def start_server():
    """Start the WebSocket server"""
    assistant = VoiceAssistant()
    

    async def process_request(path, headers):
        """Validate Origin header"""
        origin = headers.get("Origin")
        
        # Log the connection attempt
        logger.info(f"🔌 Connection attempt from Origin: {origin}")
        
        # Check if origin is allowed
        # Note: None/null origin is common for local scripts or some tools, 
        # but in production browsers it will be set.
        
        # FIX: Allow wildcard '*'
        is_allowed = origin in config.server.allowed_origins
        if "*" in config.server.allowed_origins:
            is_allowed = True
            
        if origin and not is_allowed:
            logger.warning(f"⛔ Rejected connection from unauthorized origin: {origin}")
            return (403, [], b"Forbidden: Invalid Origin")
            
        return None  # Allow connection

    async with websockets.serve(
        assistant.handle_client,
        config.server.host,
        config.server.port,
        process_request=process_request
    ):
        logger.info("✅ Server running")
        logger.info(f"📍 ws://{config.server.host}:{config.server.port}")
        logger.info("🎙️  Waiting for connections...\n")
        await asyncio.Future()  # Run forever
