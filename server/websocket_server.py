"""
WebSocket Server
"""

import asyncio
import websockets
from loguru import logger
from datetime import datetime

from config.settings import config
from server.assistant import VoiceAssistant


async def start_server():
    """Start the WebSocket server"""
    logger.debug("🔧 Initializing VoiceAssistant instance")
    assistant = VoiceAssistant()
    logger.debug("✅ VoiceAssistant instance created successfully")
    

    async def process_request(path, headers):
        """Validate Origin header"""
        origin = headers.get("Origin")
        client_ip = headers.get("X-Forwarded-For") or headers.get("X-Real-IP") or "unknown"
        
        logger.debug(f"🔍 Processing connection request")
        logger.debug(f"   Path: {path}")
        logger.debug(f"   Origin: {origin}")
        logger.debug(f"   Client IP: {client_ip}")
        logger.debug(f"   Allowed origins: {config.server.allowed_origins}")
        
        # Log the connection attempt
        logger.info(f"🔌 Connection attempt from Origin: {origin}")
        
        # Check if origin is allowed
        # Note: None/null origin is common for local scripts or some tools, 
        # but in production browsers it will be set.
        
        # FIX: Allow wildcard '*'
        is_allowed = origin in config.server.allowed_origins
        if "*" in config.server.allowed_origins:
            is_allowed = True
            logger.debug("✅ Wildcard (*) found in allowed origins, allowing all")
        else:
            logger.debug(f"🔍 Origin check: {is_allowed} (origin: {origin})")
            
        if origin and not is_allowed:
            logger.warning(f"⛔ Rejected connection from unauthorized origin: {origin}")
            logger.debug(f"   Rejected origin: {origin}, allowed: {config.server.allowed_origins}")
            return (403, [], b"Forbidden: Invalid Origin")
        
        logger.debug("✅ Origin validation passed, allowing connection")
        return None  # Allow connection

    logger.debug(f"🚀 Starting WebSocket server")
    logger.debug(f"   Host: {config.server.host}")
    logger.debug(f"   Port: {config.server.port}")
    logger.debug(f"   Allowed origins: {config.server.allowed_origins}")
    
    async with websockets.serve(
        assistant.handle_client,
        config.server.host,
        config.server.port,
        process_request=process_request
    ):
        logger.info("✅ Server running")
        logger.info(f"📍 ws://{config.server.host}:{config.server.port}")
        logger.info("🎙️  Waiting for connections...\n")
        logger.debug(f"🔄 Server started at {datetime.now().isoformat()}")
        logger.debug("⏳ Entering infinite wait loop")
        await asyncio.Future()  # Run forever
