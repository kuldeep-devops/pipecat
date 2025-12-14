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
        
        # Build Deepgram URL using config values
        deepgram_url = (
            f"wss://api.deepgram.com/v1/listen"
            f"?encoding={self.deepgram_config.encoding}"
            f"&sample_rate={self.deepgram_config.sample_rate}"
            f"&channels={self.deepgram_config.channels}"
            f"&model={self.deepgram_config.model}"
            f"&language={self.deepgram_config.language}"
            f"&interim_results={str(self.deepgram_config.interim_results).lower()}"
            f"&endpointing={self.deepgram_config.endpointing}"
            f"&smart_format={str(self.deepgram_config.smart_format).lower()}"
            f"&numerals={str(self.deepgram_config.numerals).lower()}"
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
                                    
                                    # Add greeting to conversation history BEFORE user message
                                    # This helps LLM understand the greeting was already sent
                                    self.conversation_history.append({
                                        "role": "assistant",
                                        "content": greeting
                                    })
                                    
                                    # Add user message to history
                                    self.conversation_history.append({
                                        "role": "user",
                                        "content": transcript
                                    })
                                    
                                    # Add explicit instruction to NOT ask another question
                                    self.conversation_history.append({
                                        "role": "system",
                                        "content": "REMINDER: The greeting already asked 'How can I help you today?' DO NOT ask 'How can I assist you today?' or any similar question. Just acknowledge and wait, or answer if the user has a specific request."
                                    })
                                    
                                    greeting_sent = True
                                    
                                    # Send greeting TTS and wait for it to complete
                                    await self.text_to_speech(greeting, websocket)
                                    
                                    # Estimate greeting audio duration and wait for it to complete
                                    word_count = len(greeting.split())
                                    estimated_duration = (word_count / 2.5) + 1.0  # seconds
                                    logger.info(f"⏳ Waiting {estimated_duration:.1f}s for greeting audio to complete...")
                                    await asyncio.sleep(estimated_duration)
                                    
                                    # Get LLM response (user message already added to history)
                                    await self.get_llm_response_direct(websocket)
                                else:
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
            
            await self._process_llm_response(websocket)
            
        except Exception as e:
            logger.error(f"❌ LLM error: {e}")
    
    async def get_llm_response_direct(self, websocket):
        """Get LLM response when user message already in history"""
        try:
            await self._process_llm_response(websocket)
        except Exception as e:
            logger.error(f"❌ LLM error: {e}")
    
    async def _process_llm_response(self, websocket):
        """Process LLM response (shared logic)"""
        logger.info("🧠 Calling OpenAI...")
        
        # Filter out additional system messages from history (keep only the first one)
        filtered_history = [self.conversation_history[0]]  # Keep initial system prompt
        for msg in self.conversation_history[1:]:
            if msg["role"] != "system":  # Skip additional system reminder messages
                filtered_history.append(msg)
        
        # Get response
        response = self.openai_client.chat.completions.create(
            model=self.openai_config.model,
            messages=filtered_history,
            max_tokens=self.openai_config.max_tokens,
            temperature=self.openai_config.temperature
        )
        
        assistant_text = response.choices[0].message.content
        logger.info(f"💬 ASSISTANT: {assistant_text}")
        
        # Check if response is asking redundant question after greeting
        redundant_phrases = [
            "how can i assist you",
            "how can i help you",
            "what can i do for you",
            "what would you like to know",
            "what would you like",
            "i can help you with",
            "i can help you",
            "what would you like to know or do",
            "assist in booking"
        ]
        response_lower = assistant_text.lower()
        # Check if it contains redundant phrases (especially after greeting)
        # If it mentions helping or asking what user wants, it's likely redundant
        if any(phrase in response_lower for phrase in redundant_phrases):
            # If it's a question, replace with simple acknowledgment - NO question
            if "?" in assistant_text:
                assistant_text = "I'm here to help."
                logger.warning("⚠️ Detected redundant question, replacing with simple acknowledgment")
            # If it's a statement like "I can help you with...", also replace
            elif "i can help" in response_lower or "i can assist" in response_lower:
                assistant_text = "I'm here to help."
                logger.warning("⚠️ Detected redundant help statement, replacing with simple acknowledgment")
        
        # Check for "hold on" or "wait" phrases - AI should respond immediately, not ask user to wait
        delay_phrases = [
            "i'll need a moment",
            "please hold on",
            "hold on",
            "wait a moment",
            "give me a moment",
            "one moment",
            "just a moment",
            "please wait",
            "i'll get back to you",
            "get back to you"
        ]
        # Check if response contains delay phrases
        if any(phrase in response_lower for phrase in delay_phrases):
            sentences = assistant_text.split('. ')
            
            # Check if "let me check" is followed by actual result in the same response (this is OK)
            has_check_phrase = any(phrase in response_lower for phrase in ["let me check", "checking", "i'll check"])
            has_result = any(word in response_lower for word in ["available", "confirmed", "booked", "yes", "no", "full", "alternative"])
            
            # If response has both "check" phrase AND result, it's OK - just remove pure delay phrases
            if has_check_phrase and has_result:
                # This is OK - "Let me check... Yes, available" - just remove pure delay phrases
                filtered_sentences = [s for s in sentences if not any(phrase in s.lower() for phrase in delay_phrases)]
                if filtered_sentences:
                    assistant_text = '. '.join(filtered_sentences)
                    if not assistant_text.rstrip().endswith(('.', '!', '?')):
                        assistant_text += '.'
            else:
                # Response has delay phrase but no result - this is bad
                filtered_sentences = [s for s in sentences if not any(phrase in s.lower() for phrase in delay_phrases)]
                
                if filtered_sentences:
                    # Keep the non-delay sentences
                    assistant_text = '. '.join(filtered_sentences)
                    if not assistant_text.rstrip().endswith(('.', '!', '?')):
                        assistant_text += '.'
                else:
                    # Response was only delay phrases - check what user asked for
                    user_query = self.conversation_history[-1].get("content", "").lower() if self.conversation_history else ""
                    if any(word in user_query for word in ["available", "book", "appointment", "slot", "time", "when", "check"]):
                        # User asked about availability - should have been answered immediately
                        assistant_text = "Checking availability."
                        logger.warning("⚠️ Detected delay phrase for availability check without result, should provide result immediately")
                    else:
                        # Replace with simple acknowledgment
                        assistant_text = "I'm here to help."
                        logger.warning("⚠️ Detected delay phrase, replacing with acknowledgment")
        
        # Check if service listing includes too much detail (prices, availability when not asked)
        # If user asked "What services are available?" and response includes prices/details, simplify it
        if "what services" in self.conversation_history[-1].get("content", "").lower() or "services available" in self.conversation_history[-1].get("content", "").lower():
            # Check if response includes prices (₹ or rupees) or detailed availability
            if ("₹" in assistant_text or "rupees" in response_lower or "price" in response_lower) and "available" not in self.conversation_history[-1].get("content", "").lower():
                # Simplify to just departments (matching new structure)
                departments = []
                if "salon" in response_lower:
                    departments.append("Salon")
                if "aesthetics" in response_lower:
                    departments.append("Aesthetics")
                if "wellness" in response_lower:
                    departments.append("Wellness")
                if "doctor" in response_lower or "dermatologist" in response_lower or "nutritionist" in response_lower or "ayurveda" in response_lower or "pain" in response_lower:
                    departments.append("Doctors")
                if "package" in response_lower:
                    departments.append("Packages")
                
                if departments:
                    assistant_text = "We offer " + ", ".join(departments) + "."
                    logger.warning("⚠️ Detected detailed service listing, simplified to departments only")
            
            # Check if AI is asking a follow-up question after listing services - should just list and STOP
            follow_up_question_phrases = [
                "what are you interested in",
                "how can i help",
                "what would you like",
                "which one",
                "what can i do",
                "how may i assist"
            ]
            sentences = assistant_text.split('. ')
            if len(sentences) > 1:
                # Check if any sentence after the first contains a follow-up question
                for sentence in sentences[1:]:
                    sentence_lower = sentence.lower()
                    if any(phrase in sentence_lower for phrase in follow_up_question_phrases) and "?" in sentence:
                        # Remove the follow-up question, keep only the service listing
                        assistant_text = sentences[0] + '.'
                        logger.warning("⚠️ Detected follow-up question after service listing, removed - should just list and STOP")
                        break
        
        # Response length filter - enforce 1-2 sentences for most responses, 3-4 for booking confirmations
        sentences = assistant_text.split('. ')
        # Count sentences (account for final period)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Check if this is a booking confirmation - allow 3-4 sentences
        is_booking_confirmation = any(word in response_lower for word in ["booked", "confirmed", "appointment", "session"]) and any(word in response_lower for word in ["for", "on", "at"])
        
        if is_booking_confirmation:
            # Booking confirmations can be 3-4 sentences to include all details
            if sentence_count > 4:
                # Take first 4 sentences for booking confirmations
                first_four = '. '.join(sentences[:4])
                if not first_four.rstrip().endswith(('.', '!', '?')):
                    first_four += '.'
                assistant_text = first_four
                logger.warning(f"⚠️ Booking confirmation too long ({sentence_count} sentences), truncated to 4 sentences")
        else:
            # Regular responses: 1-2 sentences maximum
            if sentence_count > 2:
                # Take only first 2 sentences
                first_two = '. '.join(sentences[:2])
                # Ensure it ends with proper punctuation
                if not first_two.rstrip().endswith(('.', '!', '?')):
                    first_two += '.'
                assistant_text = first_two
                logger.warning(f"⚠️ Response too long ({sentence_count} sentences), truncated to 2 sentences")
        
        # Word count check - if response is too wordy (>50 words), try to shorten
        word_count = len(assistant_text.split())
        if word_count > 50:
            # If it's a list, try to convert to bullet points
            if ':' in assistant_text or ',' in assistant_text:
                # Try to extract key points
                parts = assistant_text.split(':')
                if len(parts) > 1:
                    # Keep the intro and first key point
                    intro = parts[0].strip()
                    first_point = parts[1].split(',')[0].strip() if ',' in parts[1] else parts[1].split('.')[0].strip()
                    assistant_text = f"{intro}: {first_point}."
                    logger.warning(f"⚠️ Response too wordy ({word_count} words), shortened")
        
        # Check if response continues after providing information (should STOP and WAIT)
        # If response contains "Let me confirm..." or "Let me check..." after already providing info, truncate
        response_lower = assistant_text.lower()
        # Check if response has multiple sentences and contains continuation phrases
        sentences = assistant_text.split('. ')
        if len(sentences) > 1:
            # Check if later sentences contain continuation phrases
            continuation_phrases = ["let me confirm", "let me verify", "i'll confirm", "i'll check"]
            # Allow "let me check" if it's followed by result in same response
            has_check_with_result = "let me check" in response_lower and any(word in response_lower for word in ["available", "confirmed", "booked", "yes", "no", "full"])
            
            for i, sentence in enumerate(sentences[1:], start=1):
                sentence_lower = sentence.lower()
                if any(phrase in sentence_lower for phrase in continuation_phrases):
                    # Truncate at the sentence before the continuation
                    assistant_text = '. '.join(sentences[:i]) + '.'
                    logger.warning("⚠️ Detected continuation after providing info, truncated to stop and wait")
                    break
                # Check for "let me check" without result (bad)
                if "let me check" in sentence_lower and not has_check_with_result:
                    # This is "let me check" without result - should have provided result
                    # Check if next sentence has result, if not, this is a problem
                    if i + 1 < len(sentences):
                        next_sentence = sentences[i + 1].lower()
                        if not any(word in next_sentence for word in ["available", "confirmed", "booked", "yes", "no", "full"]):
                            # "Let me check" without immediate result - truncate
                            assistant_text = '. '.join(sentences[:i]) + '.'
                            logger.warning("⚠️ Detected 'let me check' without result, truncated")
                            break
        
        # Check if booking confirmation says "with a doctor" or "with doctor" - should include actual doctor name
        if "booked" in response_lower and ("with a doctor" in response_lower or "with doctor" in response_lower):
            # Try to find doctor name from conversation history
            doctor_keywords = ["dermatologist", "nutritionist", "ayurveda", "pain relief", "dr.", "doctor"]
            doctor_names = {
                "dermatologist": "Dr. Anjali Khanna",
                "nutritionist": "Ms. Priya Sengupta",
                "ayurveda": "Dr. Rajesh Kumar",
                "pain relief": "Dr. Arvind Singh"
            }
            
            # Search conversation history for doctor mentions
            for msg in reversed(self.conversation_history[-5:]):  # Check last 5 messages
                msg_content = msg.get("content", "").lower()
                for keyword, doctor_name in doctor_names.items():
                    if keyword in msg_content:
                        # Replace "with a doctor" or "with doctor" with actual doctor name
                        assistant_text = assistant_text.replace("with a doctor", f"with {doctor_name}")
                        assistant_text = assistant_text.replace("with doctor", f"with {doctor_name}")
                        logger.warning(f"⚠️ Replaced 'with doctor' with actual doctor name: {doctor_name}")
                        break
                if "dr." in assistant_text.lower() or any(name.split()[1].lower() in assistant_text.lower() for name in doctor_names.values()):
                    break
        
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
