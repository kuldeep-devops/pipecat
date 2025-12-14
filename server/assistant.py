"""
Voice Assistant - Main logic for handling conversations
"""

import asyncio
import os
from loguru import logger
from openai import OpenAI
import requests
import json

from config.settings import config
from config.prompts import get_demo_prompt


from server.knowledge_base import LevoWellnessDemoKB

class VoiceAssistant:
    """Complete voice assistant with direct Deepgram integration"""
    
    def __init__(self):
        self.deepgram_config = config.deepgram
        self.openai_config = config.openai
        self.elevenlabs_config = config.elevenlabs
        
        self.openai_client = OpenAI(api_key=self.openai_config.api_key)
        
        # Load Knowledge Base
        kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge_base.json")
        self.kb = LevoWellnessDemoKB(data_path=kb_path)
        kb_context = self.kb.get_context_string()

        # Initialize conversation with healthcare persona + KB
        self.conversation_history = [
            {
                "role": "system",
                "content": get_demo_prompt(kb_context)
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
            f"&model=nova-3"
            f"&language=multi"
            f"&interim_results=false"
            f"&endpointing=1000"
            f"&smart_format=true"
            f"&numerals=true"
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
        
        # Flag to track if greeting has been sent (after first user message)
        greeting_sent = False
        
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
                nonlocal greeting_sent
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
                                
                                # Send greeting after first user message (only once)
                                if not greeting_sent:
                                    greeting = self.kb.get_greeting(mode="voice_nano")
                                    logger.info(f"👋 Sending greeting after first message: {greeting}")
                                    await websocket.send(json.dumps({
                                        'type': 'greeting',
                                        'text': greeting
                                    }))
                                    # Send greeting TTS and wait for it to complete
                                    await self.text_to_speech(greeting, websocket)
                                    
                                    # Add greeting to conversation history so LLM knows it was sent
                                    self.conversation_history.append({
                                        "role": "assistant",
                                        "content": greeting
                                    })
                                    greeting_sent = True
                                    
                                    # Estimate greeting audio duration and wait for it to complete
                                    # Average speech rate: ~150 words/min = 2.5 words/sec
                                    # Add buffer for TTS generation and network delay
                                    word_count = len(greeting.split())
                                    estimated_duration = (word_count / 2.5) + 1.0  # seconds
                                    logger.info(f"⏳ Waiting {estimated_duration:.1f}s for greeting audio to complete...")
                                    await asyncio.sleep(estimated_duration)
                                
                                # Get LLM response (user message will be added inside this function)
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
                
                # Small delay to ensure last audio chunk is fully sent
                await asyncio.sleep(0.2)
                
                # Send completion signal to client
                await websocket.send(json.dumps({'type': 'tts_complete'}))
                logger.info("📢 TTS completion signal sent to client")
            else:
                logger.error(f"❌ TTS error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
