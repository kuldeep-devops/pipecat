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
        self.config = config.elevenlabs
        self.api_key = self.config.api_key
        self.voice_id = self.config.voice_id
    
    async def generate_speech(self, text):
        """Generate speech from text and return audio chunks"""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        
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
        
        try:
            # Make request in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=data, headers=headers, stream=True)
            )
            
            if response.status_code == 200:
                # Yield audio chunks
                chunks = []
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        chunks.append(chunk)
                return chunks
            else:
                logger.error(f"❌ TTS API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ TTS generation error: {e}")
            return []
