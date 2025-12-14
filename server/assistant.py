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
from config.prompts import get_demo_prompt, get_demo_greeting


from server.knowledge_base import LevoWellnessDemoKB
import re

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
        
        # Send greeting message (only once on connection, not during conversations)
        greeting = get_demo_greeting()
        logger.info(f"👋 Sending greeting: {greeting}")
        await websocket.send(json.dumps({
            'type': 'greeting',
            'text': greeting
        }))
        await self.text_to_speech(greeting, websocket)
        
        # Mark that greeting has been sent (add to conversation history so LLM knows)
        self.conversation_history.append({
            "role": "assistant",
            "content": greeting
        })
        
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
    
    def _chunk_text(self, text, max_chars=4000):
        """
        Split text into chunks at sentence boundaries.
        ElevenLabs has a limit, so we chunk at sentences to preserve natural flow.
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        # Split by sentence endings (., !, ?) followed by space or newline
        sentences = re.split(r'([.!?]\s+)', text)
        
        current_chunk = ""
        for i in range(0, len(sentences), 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
            
            # If adding this sentence would exceed limit, save current chunk
            if current_chunk and len(current_chunk) + len(sentence) > max_chars:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence
        
        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If any chunk is still too long (shouldn't happen, but safety check)
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > max_chars:
                # Force split at word boundaries
                words = chunk.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 > max_chars:
                        if temp_chunk:
                            final_chunks.append(temp_chunk.strip())
                        temp_chunk = word
                    else:
                        temp_chunk += " " + word if temp_chunk else word
                if temp_chunk:
                    final_chunks.append(temp_chunk.strip())
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    async def text_to_speech(self, text, websocket):
        """Convert text to speech using ElevenLabs with chunking for long texts"""
        try:
            text_length = len(text)
            logger.info(f"🔊 Generating speech for text ({text_length} characters)...")
            logger.info(f"📝 Full text: {text}")
            
            # Chunk text if it's too long (ElevenLabs limit is ~5000 chars, we use 4000 for safety)
            chunks = self._chunk_text(text, max_chars=4000)
            
            if len(chunks) > 1:
                logger.info(f"📝 Text split into {len(chunks)} chunks for TTS")
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_config.voice_id}/stream"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_config.api_key
            }
            
            total_chunks_sent = 0
            
            # Process each chunk sequentially
            for chunk_idx, chunk in enumerate(chunks):
                logger.info(f"🔊 Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} chars)")
                
                data = {
                    "text": chunk,
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
                    for audio_chunk in response.iter_content(chunk_size=4096):
                        if audio_chunk:
                            chunk_count += 1
                            total_chunks_sent += 1
                            await websocket.send(audio_chunk)
                    
                    logger.info(f"✅ Chunk {chunk_idx + 1} sent ({chunk_count} audio chunks)")
                    
                    # Small delay between chunks to ensure smooth playback
                    if chunk_idx < len(chunks) - 1:
                        await asyncio.sleep(0.1)
                else:
                    logger.error(f"❌ TTS error for chunk {chunk_idx + 1}: {response.status_code} - {response.text}")
                    break
            
            logger.info(f"✅ Complete audio sent to browser ({total_chunks_sent} total audio chunks from {len(chunks)} text chunks)")
            
            # Small delay to ensure last audio chunk is fully sent before signaling completion
            await asyncio.sleep(0.2)
            
            # Send completion signal to client
            await websocket.send(json.dumps({'type': 'tts_complete'}))
            logger.info("📢 TTS completion signal sent to client")
                
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
