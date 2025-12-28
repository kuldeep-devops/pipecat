"""
Text-to-Speech Handler using ElevenLabs
"""

import asyncio
import requests
from loguru import logger

from config.settings import config


class TTSHandler:
    """Handles text-to-speech using ElevenLabs API"""
    
    def __init__(self):
        logger.debug("🔧 Initializing TTSHandler")
        self.config = config.elevenlabs
        self.api_key = self.config.api_key
        self.voice_id = self.config.voice_id
        logger.debug(f"   Voice ID: {self.voice_id}")
        logger.debug(f"   Model: {self.config.model}")
        logger.debug(f"   Stability: {self.config.stability}")
        logger.debug(f"   Similarity boost: {self.config.similarity_boost}")
        logger.debug(f"   API key length: {len(self.api_key)}")
        logger.debug("✅ TTSHandler initialized")
    
    async def generate_speech(self, text):
        """Generate speech from text and return audio chunks"""
        logger.debug(f"🔊 generate_speech called with text: '{text}'")
        logger.debug(f"   Text length: {len(text)} chars")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        logger.debug(f"   TTS URL: {url.split('/stream')[0]}...")
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": self.config.model,
            "voice_settings": {
                "stability": self.config.stability,
                "similarity_boost": self.config.similarity_boost
            }
        }
        logger.debug(f"   Request data keys: {list(data.keys())}")
        logger.debug(f"   Voice settings: stability={self.config.stability}, similarity_boost={self.config.similarity_boost}")
        
        try:
            logger.debug("   Sending request to ElevenLabs API (in thread pool)")
            # Make request in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=data, headers=headers, stream=True)
            )
            logger.debug(f"   ElevenLabs API response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.debug("   ✅ ElevenLabs API request successful, collecting audio chunks")
                # Yield audio chunks
                chunks = []
                chunk_count = 0
                total_bytes = 0
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        chunk_count += 1
                        total_bytes += len(chunk)
                        chunks.append(chunk)
                        if chunk_count % 10 == 0:
                            logger.debug(f"   Collected {chunk_count} chunks ({total_bytes} bytes)")
                logger.debug(f"✅ Audio generation complete: {chunk_count} chunks, {total_bytes} bytes")
                return chunks
            else:
                logger.error(f"❌ TTS API error: {response.status_code} - {response.text}")
                logger.debug(f"   Response headers: {dict(response.headers)}")
                return []
                
        except Exception as e:
            logger.error(f"❌ TTS generation error: {e}")
            logger.exception("   Full exception traceback:")
            return []
