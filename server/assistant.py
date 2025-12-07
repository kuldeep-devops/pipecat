"""
Voice Assistant - Main logic for handling conversations
"""

import asyncio
from loguru import logger
from openai import OpenAI
import requests
import json

from config.settings import config
from config.prompts import get_system_prompt


from server.knowledge_base import HealthcareKnowledgeBase

class VoiceAssistant:
    """Complete voice assistant with direct Deepgram integration"""
    
    def __init__(self):
        self.deepgram_config = config.deepgram
        self.openai_config = config.openai
        self.elevenlabs_config = config.elevenlabs
        
        self.openai_client = OpenAI(api_key=self.openai_config.api_key)
        
        # Load Knowledge Base
        self.kb = HealthcareKnowledgeBase()
        kb_context = self.kb.get_context_string()

        # Initialize conversation with healthcare persona + KB
        self.conversation_history = [
            {
                "role": "system",
                "content": get_system_prompt(kb_context)
            }
        ]
    
    async def handle_client(self, websocket):
        """Handle a browser client connection"""
        logger.info(f"🎙️  Client connected: {websocket.remote_address}")
        
        # Build Deepgram URL - exact copy from working version
        deepgram_url = (
            f"wss://api.deepgram.com/v1/listen"
            f"?encoding=linear16"
            f"&sample_rate=16000"
            f"&channels=1"
            f"&model=nova-2-general"
            f"&language=en-US"
            f"&punctuate=true"
            f"&interim_results=false"
            f"&endpointing=1000"
        )
        
        logger.info("🔌 Connecting to Deepgram...")
        
        try:
            # Connect to Deepgram - exact copy from working version
            import websockets.legacy.client as client
            dg_ws = await client.connect(
                deepgram_url,
                extra_headers=[("Authorization", f"Token {self.deepgram_config.api_key}")]
            )
            logger.info("✅ Connected to Deepgram")
            
        except Exception as e:
            logger.error(f"❌ Deepgram connection failed: {e}")
            return
        
        # Send ready to browser
        await websocket.send(json.dumps({'type': 'ready'}))
        
        try:
            async def forward_audio():
                """Forward audio from browser to Deepgram"""
                audio_count = 0
                async for message in websocket:
                    if isinstance(message, bytes):
                        audio_count += 1
                        if audio_count == 1:
                            logger.info(f"📤 First audio chunk: {len(message)} bytes")
                        if audio_count % 50 == 0:
                            logger.info(f"📤 {audio_count} audio chunks")
                        await dg_ws.send(message)
                    elif isinstance(message, str):
                        data = json.loads(message)
                        if data.get('type') == 'stop':
                            break
            
            async def process_transcriptions():
                """Process transcriptions from Deepgram"""
                async for message in dg_ws:
                    data = json.loads(message)
                    
                    if 'channel' in data and 'alternatives' in data['channel']:
                        alternatives = data['channel']['alternatives']
                        if alternatives and len(alternatives) > 0:
                            transcript = alternatives[0].get('transcript', '')
                            is_final = data.get('is_final', False)
                            
                            if transcript and is_final:
                                logger.info(f"🎤 USER: {transcript}")
                                
                                # Send transcription to browser
                                await websocket.send(json.dumps({
                                    'type': 'transcription',
                                    'text': transcript
                                }))
                                
                                # Get LLM response
                                await self.get_llm_response(transcript, websocket)
            
            # Run both tasks
            await asyncio.gather(
                forward_audio(),
                process_transcriptions()
            )
            
        except Exception as e:
            logger.error(f"❌ Session error: {e}")
        finally:
            await dg_ws.close()
            logger.info("✅ Session complete")
    
    async def get_llm_response(self, user_text, websocket):
        """Get response from OpenAI"""
        try:
            # Add user message
            self.conversation_history.append({
                "role": "user",
                "content": user_text
            })
            
            logger.info("🧠 Calling OpenAI...")
            
            # Get response
            response = self.openai_client.chat.completions.create(
                model=self.openai_config.model,
                messages=self.conversation_history,
                max_tokens=self.openai_config.max_tokens,
                temperature=self.openai_config.temperature
            )
            
            assistant_text = response.choices[0].message.content
            logger.info(f"💬 ASSISTANT: {assistant_text}")
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_text
            })
            
            # Send to browser
            await websocket.send(json.dumps({
                'type': 'llm_text',
                'text': assistant_text
            }))
            
            # Generate speech
            await self.text_to_speech(assistant_text, websocket)
            
        except Exception as e:
            logger.error(f"❌ LLM error: {e}")
    
    async def text_to_speech(self, text, websocket):
        """Convert text to speech using ElevenLabs"""
        try:
            logger.info("🔊 Generating speech...")
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_config.voice_id}/stream"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_config.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.elevenlabs_config.model,
                "voice_settings": {
                    "stability": self.elevenlabs_config.stability,
                    "similarity_boost": self.elevenlabs_config.similarity_boost
                }
            }
            
            # Make request in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=data, headers=headers, stream=True)
            )
            
            if response.status_code == 200:
                # Stream audio to browser
                chunk_count = 0
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        chunk_count += 1
                        await websocket.send(chunk)
                
                logger.info(f"✅ Audio sent to browser ({chunk_count} chunks)")
            else:
                logger.error(f"❌ TTS error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
