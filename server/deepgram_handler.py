"""
Deepgram WebSocket Handler
"""

import websockets.legacy.client as ws_client
from loguru import logger


class DeepgramHandler:
    """Handles direct WebSocket connection to Deepgram"""
    
    def __init__(self, config):
        logger.debug("🔧 Initializing DeepgramHandler")
        self.config = config
        self.api_key = config.api_key
        logger.debug(f"   Deepgram model: {self.config.model}")
        logger.debug(f"   Language: {self.config.language}")
        logger.debug(f"   Sample rate: {self.config.sample_rate}")
        logger.debug(f"   API key length: {len(self.api_key)}")
        logger.debug("✅ DeepgramHandler initialized")
    
    def _build_url(self):
        """Build Deepgram WebSocket URL with parameters"""
        logger.debug("🔗 Building Deepgram WebSocket URL")
        # Match exactly what works in working_voice_assistant.py
        params = [
            f"encoding={self.config.encoding}",
            f"sample_rate={self.config.sample_rate}",
            f"channels={self.config.channels}",
            f"model={self.config.model}",
            f"language={self.config.language}",
            f"punctuate={'true' if self.config.punctuate else 'false'}",
            f"interim_results={'true' if self.config.interim_results else 'false'}",
            f"endpointing={self.config.endpointing}",
        ]
        
        url = f"wss://api.deepgram.com/v1/listen?{'&'.join(params)}"
        logger.debug(f"   Built URL: {url.split('?')[0]}... (with {len(params)} parameters)")
        logger.debug(f"   Parameters: {', '.join(params)}")
        return url
    
    async def connect(self):
        """Connect to Deepgram WebSocket API"""
        logger.debug("🔌 Starting Deepgram connection process")
        url = self._build_url()
        
        logger.info("🔌 Connecting to Deepgram...")
        logger.info(f"📍 URL: {url}")
        logger.info(f"🔑 API Key (first 10 chars): {self.api_key[:10]}...")
        logger.debug(f"   Full URL length: {len(url)} chars")
        logger.debug(f"   API key length: {len(self.api_key)} chars")
        
        try:
            logger.debug("   Creating WebSocket connection with authorization header")
            # Use legacy client with list of tuples (like working version)
            connection = await ws_client.connect(
                url,
                extra_headers=[("Authorization", f"Token {self.api_key}")]
            )
            logger.info("✅ Deepgram connected successfully")
            logger.debug(f"   WebSocket connection state: {connection.state}")
            logger.debug(f"   Connection remote address: {connection.remote_address}")
            return connection
        except Exception as e:
            logger.error(f"❌ Deepgram connection failed: {e}")
            logger.error(f"URL attempted: {url}")
            logger.error(f"API key length: {len(self.api_key)}")
            logger.exception("   Full exception traceback:")
            raise
