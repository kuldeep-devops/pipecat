"""
Voice Assistant - Main logic for handling conversations
"""

import asyncio
import os
import re
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
        logger.debug("🔧 Initializing VoiceAssistant")
        
        logger.debug("📋 Loading configuration")
        self.deepgram_config = config.deepgram
        self.openai_config = config.openai
        self.elevenlabs_config = config.elevenlabs
        logger.debug(f"   Deepgram model: {self.deepgram_config.model}")
        logger.debug(f"   OpenAI model: {self.openai_config.model}")
        logger.debug(f"   ElevenLabs voice_id: {self.elevenlabs_config.voice_id}")
        
        logger.debug("🔌 Initializing OpenAI client")
        self.openai_client = OpenAI(api_key=self.openai_config.api_key)
        logger.debug("✅ OpenAI client initialized")
        
        # Load Knowledge Base
        kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge_base.json")
        logger.debug(f"📚 Loading knowledge base from: {kb_path}")
        self.kb = LevoWellnessDemoKB(data_path=kb_path)
        kb_context = self.kb.get_context_string()
        logger.debug(f"✅ Knowledge base loaded, context length: {len(kb_context)} chars")

        # Initialize conversation with healthcare persona + KB
        logger.debug("💬 Initializing conversation history with system prompt")
        system_prompt = get_demo_prompt(kb_context)
        self.conversation_history = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
        logger.debug(f"✅ System prompt initialized, length: {len(system_prompt)} chars")
        logger.debug("✅ VoiceAssistant initialization complete")
    
    async def handle_client(self, websocket):
        """Handle a browser client connection"""
        client_addr = websocket.remote_address
        logger.info(f"🎙️  Client connected: {client_addr}")
        logger.debug(f"   Client address: {client_addr}")
        logger.debug(f"   WebSocket state: {websocket.state}")
        
        # Build Deepgram URL using config values
        logger.debug("🔗 Building Deepgram WebSocket URL")
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
        logger.debug(f"   Deepgram URL: {deepgram_url.split('?')[0]}... (params configured)")
        logger.debug(f"   Parameters: model={self.deepgram_config.model}, language={self.deepgram_config.language}, sample_rate={self.deepgram_config.sample_rate}")
        
        logger.info("🔌 Connecting to Deepgram...")
        
        try:
            # Connect to Deepgram - exact copy from working version
            import websockets.legacy.client as client
            logger.debug("   Creating WebSocket connection to Deepgram")
            dg_ws = await client.connect(
                deepgram_url,
                extra_headers=[("Authorization", f"Token {self.deepgram_config.api_key}")]
            )
            logger.info("✅ Connected to Deepgram")
            logger.debug(f"   Deepgram WebSocket state: {dg_ws.state}")
            
        except Exception as e:
            logger.error(f"❌ Deepgram connection failed: {e}")
            logger.exception("   Full exception traceback:")
            return
        
        # Send ready to browser
        logger.debug("📤 Sending 'ready' message to client")
        await websocket.send(json.dumps({'type': 'ready'}))
        logger.debug("✅ 'ready' message sent")
        
        # Flag to track if greeting has been sent (after first user message)
        greeting_sent = False
        logger.debug("🔧 Initialized greeting_sent flag: False")
        
        try:
            async def forward_audio():
                """Forward audio from browser to Deepgram"""
                logger.debug("🔄 Starting audio forwarding task")
                audio_count = 0
                total_bytes = 0
                
                async for message in websocket:
                    if isinstance(message, bytes):
                        audio_count += 1
                        total_bytes += len(message)
                        if audio_count == 1:
                            logger.info(f"📤 First audio chunk: {len(message)} bytes")
                            logger.debug(f"   First chunk size: {len(message)} bytes")
                        if audio_count % 50 == 0:
                            logger.info(f"📤 {audio_count} audio chunks")
                            logger.debug(f"   Total audio bytes forwarded: {total_bytes}")
                        await dg_ws.send(message)
                    elif isinstance(message, str):
                        logger.debug(f"📥 Received text message from client: {message[:100]}")
                        data = json.loads(message)
                        logger.debug(f"   Parsed message type: {data.get('type')}")
                        if data.get('type') == 'stop':
                            logger.info("🛑 Received 'stop' signal from client")
                            logger.debug("   Stopping audio forwarding")
                            break
                logger.debug(f"✅ Audio forwarding task completed (total chunks: {audio_count}, total bytes: {total_bytes})")
            
            async def process_transcriptions():
                """Process transcriptions from Deepgram"""
                nonlocal greeting_sent
                logger.debug("🔄 Starting transcription processing task")
                transcription_count = 0
                
                async for message in dg_ws:
                    logger.debug(f"📥 Received message from Deepgram: {len(message)} chars")
                    try:
                        data = json.loads(message)
                        logger.debug(f"   Parsed Deepgram response, keys: {list(data.keys())}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse Deepgram message as JSON: {e}")
                        logger.debug(f"   Raw message: {message[:200]}")
                        continue
                    
                    if 'channel' in data and 'alternatives' in data['channel']:
                        alternatives = data['channel']['alternatives']
                        logger.debug(f"   Found {len(alternatives)} alternatives")
                        if alternatives and len(alternatives) > 0:
                            transcript = alternatives[0].get('transcript', '')
                            is_final = data.get('is_final', False)
                            confidence = alternatives[0].get('confidence', 0)
                            logger.debug(f"   Transcript: '{transcript}', is_final: {is_final}, confidence: {confidence}")
                            
                            if transcript and is_final:
                                transcription_count += 1
                                logger.info(f"🎤 USER: {transcript}")
                                logger.debug(f"   Final transcription #{transcription_count}: '{transcript}'")
                                
                                # Send transcription to browser
                                logger.debug("📤 Sending transcription to client")
                                await websocket.send(json.dumps({
                                    'type': 'transcription',
                                    'text': transcript
                                }))
                                logger.debug("✅ Transcription sent to client")
                                
                                # Send greeting after first user message (only once)
                                if not greeting_sent:
                                    logger.debug("👋 First user message detected, preparing greeting")
                                    greeting = self.kb.get_greeting(mode="voice_nano")
                                    logger.info(f"👋 Sending greeting after first message: {greeting}")
                                    logger.debug(f"   Greeting text: '{greeting}'")
                                    
                                    logger.debug("📤 Sending greeting message to client")
                                    await websocket.send(json.dumps({
                                        'type': 'greeting',
                                        'text': greeting
                                    }))
                                    logger.debug("✅ Greeting message sent")
                                    
                                    # Add greeting to conversation history BEFORE user message
                                    # This helps LLM understand the greeting was already sent
                                    logger.debug("💬 Adding greeting to conversation history")
                                    self.conversation_history.append({
                                        "role": "assistant",
                                        "content": greeting
                                    })
                                    logger.debug(f"   Conversation history length: {len(self.conversation_history)}")
                                    
                                    # Add user message to history
                                    logger.debug("💬 Adding user message to conversation history")
                                    self.conversation_history.append({
                                        "role": "user",
                                        "content": transcript
                                    })
                                    logger.debug(f"   Conversation history length: {len(self.conversation_history)}")
                                    
                                    # Add explicit instruction to NOT ask another question
                                    logger.debug("💬 Adding system reminder to conversation history")
                                    self.conversation_history.append({
                                        "role": "system",
                                        "content": "REMINDER: The greeting already asked 'How can I help you today?' DO NOT ask 'How can I assist you today?' or any similar question. Just acknowledge and wait, or answer if the user has a specific request."
                                    })
                                    logger.debug(f"   Conversation history length: {len(self.conversation_history)}")
                                    
                                    greeting_sent = True
                                    logger.debug("✅ Greeting sent flag set to True")
                                    
                                    # Send greeting TTS and wait for it to complete
                                    logger.debug("🔊 Starting greeting TTS generation")
                                    await self.text_to_speech(greeting, websocket)
                                    logger.debug("✅ Greeting TTS completed")
                                    
                                    # Estimate greeting audio duration and wait for it to complete
                                    word_count = len(greeting.split())
                                    estimated_duration = (word_count / 2.5) + 1.0  # seconds
                                    logger.info(f"⏳ Waiting {estimated_duration:.1f}s for greeting audio to complete...")
                                    logger.debug(f"   Word count: {word_count}, estimated duration: {estimated_duration:.1f}s")
                                    await asyncio.sleep(estimated_duration)
                                    logger.debug("✅ Waiting period completed")
                                    
                                    # Get LLM response (user message already added to history)
                                    logger.debug("🧠 Getting LLM response (direct)")
                                    await self.get_llm_response_direct(websocket)
                                    logger.debug("✅ LLM response completed")
                                else:
                                    logger.debug("💬 Processing subsequent user message")
                                    # Get LLM response (user message will be added inside this function)
                                    await self.get_llm_response(transcript, websocket)
                                    logger.debug("✅ User message processing completed")
            
            # Run both tasks
            logger.debug("🚀 Starting parallel tasks: audio forwarding and transcription processing")
            await asyncio.gather(
                forward_audio(),
                process_transcriptions()
            )
            logger.debug("✅ Both tasks completed")
            
        except Exception as e:
            logger.error(f"❌ Session error: {e}")
            logger.exception("   Full exception traceback:")
        finally:
            logger.debug("🧹 Cleaning up session")
            try:
                await dg_ws.close()
                logger.debug("✅ Deepgram WebSocket closed")
            except Exception as e:
                logger.error(f"❌ Error closing Deepgram connection: {e}")
            logger.info("✅ Session complete")
    
    async def get_llm_response(self, user_text, websocket):
        """Get response from OpenAI"""
        logger.debug(f"💬 get_llm_response called with user text: '{user_text}'")
        try:
            # Add user message
            logger.debug("💬 Adding user message to conversation history")
            self.conversation_history.append({
                "role": "user",
                "content": user_text
            })
            logger.debug(f"   Conversation history length: {len(self.conversation_history)}")
            
            await self._process_llm_response(websocket)
            
        except Exception as e:
            logger.error(f"❌ LLM error: {e}")
            logger.exception("   Full exception traceback:")
    
    async def get_llm_response_direct(self, websocket):
        """Get LLM response when user message already in history"""
        logger.debug("💬 get_llm_response_direct called (user message already in history)")
        logger.debug(f"   Conversation history length: {len(self.conversation_history)}")
        try:
            await self._process_llm_response(websocket)
        except Exception as e:
            logger.error(f"❌ LLM error: {e}")
            logger.exception("   Full exception traceback:")
    
    async def _process_llm_response(self, websocket):
        """Process LLM response (shared logic)"""
        logger.info("🧠 Calling OpenAI...")
        logger.debug(f"   Model: {self.openai_config.model}")
        logger.debug(f"   Max tokens: {self.openai_config.max_tokens}")
        logger.debug(f"   Temperature: {self.openai_config.temperature}")
        logger.debug(f"   Full conversation history length: {len(self.conversation_history)}")
        
        # Filter out additional system messages from history (keep only the first one)
        filtered_history = [self.conversation_history[0]]  # Keep initial system prompt
        skipped_system_messages = 0
        for msg in self.conversation_history[1:]:
            if msg["role"] != "system":  # Skip additional system reminder messages
                filtered_history.append(msg)
            else:
                skipped_system_messages += 1
        logger.debug(f"   Filtered history length: {len(filtered_history)} (skipped {skipped_system_messages} system messages)")
        logger.debug(f"   Last user message: {filtered_history[-1].get('content', '')[:100] if filtered_history and filtered_history[-1].get('role') == 'user' else 'N/A'}")
        
        # Get response
        logger.debug("   Sending request to OpenAI API")
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_config.model,
                messages=filtered_history,
                max_tokens=self.openai_config.max_tokens,
                temperature=self.openai_config.temperature
            )
            logger.debug(f"   OpenAI API response received")
            logger.debug(f"   Response choices: {len(response.choices)}")
            logger.debug(f"   Usage: {response.usage}")
            
            assistant_text = response.choices[0].message.content
            logger.info(f"💬 ASSISTANT: {assistant_text}")
            logger.debug(f"   Response text length: {len(assistant_text)} chars")
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}")
            logger.exception("   Full exception traceback:")
            raise
        
        logger.debug("🔍 Processing LLM response text for filtering")
        
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
        logger.debug(f"   Original response: '{assistant_text}'")
        # Check if it contains redundant phrases (especially after greeting)
        # If it mentions helping or asking what user wants, it's likely redundant
        if any(phrase in response_lower for phrase in redundant_phrases):
            logger.debug("   Detected redundant phrase in response")
            # If it's a question, replace with simple acknowledgment - NO question
            if "?" in assistant_text:
                assistant_text = "I'm here to help."
                logger.warning("⚠️ Detected redundant question, replacing with simple acknowledgment")
                logger.debug(f"   Replaced with: '{assistant_text}'")
            # If it's a statement like "I can help you with...", also replace
            elif "i can help" in response_lower or "i can assist" in response_lower:
                assistant_text = "I'm here to help."
                logger.warning("⚠️ Detected redundant help statement, replacing with simple acknowledgment")
                logger.debug(f"   Replaced with: '{assistant_text}'")
        
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
        
        # Check if booking confirmation has generic doctor reference - should include actual doctor name
        if "booked" in response_lower:
            doctor_patterns = {
                "with a doctor": None,
                "with doctor": None,
                "with the doctor": None,
                "the dermatologist": "Dr. Anjali Khanna",
                "the nutritionist": "Ms. Priya Sengupta",
                "the ayurveda doctor": "Dr. Rajesh Kumar",
                "the pain relief doctor": "Dr. Arvind Singh",
                "dermatologist": "Dr. Anjali Khanna",
                "nutritionist": "Ms. Priya Sengupta",
                "ayurveda": "Dr. Rajesh Kumar",
                "pain relief": "Dr. Arvind Singh"
            }
            
            # Check for generic doctor references first
            if any(pattern in response_lower for pattern in ["with a doctor", "with doctor", "with the doctor", "the doctor"]):
                # Try to find doctor name from conversation history
                doctor_info_map = {
                    "dermatologist": {"name": "Dr. Anjali Khanna", "department": "Dermatologist"},
                    "nutritionist": {"name": "Ms. Priya Sengupta", "department": "Nutritionist"},
                    "ayurveda": {"name": "Dr. Rajesh Kumar", "department": "Ayurveda"},
                    "pain relief": {"name": "Dr. Arvind Singh", "department": "Pain Relief"}
                }
                
                # Search conversation history for doctor mentions
                found_doctor_info = None
                for msg in reversed(self.conversation_history[-10:]):  # Check last 10 messages
                    msg_content = msg.get("content", "").lower()
                    for keyword, doctor_info in doctor_info_map.items():
                        if keyword in msg_content:
                            found_doctor_info = doctor_info
                            doctor_with_dept = f"{doctor_info['name']} ({doctor_info['department']})"
                            # Replace generic doctor references with doctor name and department
                            assistant_text = assistant_text.replace("with a doctor", f"with {doctor_with_dept}")
                            assistant_text = assistant_text.replace("with doctor", f"with {doctor_with_dept}")
                            assistant_text = assistant_text.replace("with the doctor", f"with {doctor_with_dept}")
                            assistant_text = assistant_text.replace("the doctor", doctor_with_dept)
                            logger.warning(f"⚠️ Replaced generic doctor reference with doctor and department: {doctor_with_dept}")
                            break
                    if found_doctor_info:
                        break
            
            # Check for specific doctor type references (e.g., "the Pain Relief doctor", "with the Pain Relief doctor")
            # Handle patterns like "the [specialty] doctor" or "with the [specialty] doctor"
            # Include both department and doctor name
            specialty_patterns = {
                "pain relief": {"name": "Dr. Arvind Singh", "department": "Pain Relief"},
                "dermatologist": {"name": "Dr. Anjali Khanna", "department": "Dermatologist"},
                "nutritionist": {"name": "Ms. Priya Sengupta", "department": "Nutritionist"},
                "ayurveda": {"name": "Dr. Rajesh Kumar", "department": "Ayurveda"}
            }
            
            for specialty, doctor_info in specialty_patterns.items():
                doctor_name = doctor_info["name"]
                department = doctor_info["department"]
                doctor_with_dept = f"{doctor_name} ({department})"
                
                # Pattern: "the [specialty] doctor" (e.g., "the Pain Relief doctor")
                pattern1 = f"the {specialty} doctor"
                if pattern1 in response_lower:
                    assistant_text = re.sub(
                        rf"the\s+{re.escape(specialty)}\s+doctor",
                        doctor_with_dept,
                        assistant_text,
                        flags=re.IGNORECASE
                    )
                    logger.warning(f"⚠️ Replaced 'the {specialty} doctor' with doctor and department: {doctor_with_dept}")
                
                # Pattern: "with the [specialty] doctor" (e.g., "with the Pain Relief doctor")
                pattern2 = f"with the {specialty} doctor"
                if pattern2 in response_lower:
                    assistant_text = re.sub(
                        rf"with\s+the\s+{re.escape(specialty)}\s+doctor",
                        f"with {doctor_with_dept}",
                        assistant_text,
                        flags=re.IGNORECASE
                    )
                    logger.warning(f"⚠️ Replaced 'with the {specialty} doctor' with doctor and department: {doctor_with_dept}")
                
                # Pattern: "with [specialty]" (e.g., "with Pain Relief")
                pattern3 = f"with {specialty}"
                if pattern3 in response_lower and "booked" in response_lower:
                    # Only replace if it's not already "with Dr." or "with Ms."
                    if not re.search(rf"with\s+(Dr\.|Ms\.)\s+", assistant_text, re.IGNORECASE):
                        assistant_text = re.sub(
                            rf"with\s+{re.escape(specialty)}(?!\s+doctor)",
                            f"with {doctor_with_dept}",
                            assistant_text,
                            flags=re.IGNORECASE
                        )
                        logger.warning(f"⚠️ Replaced 'with {specialty}' with doctor and department: {doctor_with_dept}")
                
                # Also handle cases where doctor name is already present but department is missing
                if doctor_name in assistant_text and department not in assistant_text and "booked" in response_lower:
                    # Add department in parentheses after doctor name if not already there
                    if not re.search(rf"{re.escape(doctor_name)}\s*\([^)]*\)", assistant_text, re.IGNORECASE):
                        assistant_text = re.sub(
                            rf"({re.escape(doctor_name)})(?!\s*\([^)]*\))",
                            rf"\1 ({department})",
                            assistant_text,
                            flags=re.IGNORECASE
                        )
                        logger.warning(f"⚠️ Added department to existing doctor name: {doctor_with_dept}")
        
        logger.debug("💬 Adding assistant response to conversation history")
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_text
        })
        logger.debug(f"   Conversation history length: {len(self.conversation_history)}")
        
        # Send to browser
        logger.debug("📤 Sending LLM response text to client")
        await websocket.send(json.dumps({
            'type': 'llm_text',
            'text': assistant_text
        }))
        logger.debug("✅ LLM response text sent to client")
        
        # Generate speech
        logger.debug("🔊 Starting text-to-speech generation")
        await self.text_to_speech(assistant_text, websocket)
        logger.debug("✅ Text-to-speech generation completed")
    
    async def text_to_speech(self, text, websocket):
        """Convert text to speech using ElevenLabs"""
        logger.debug(f"🔊 text_to_speech called with text: '{text}'")
        logger.debug(f"   Text length: {len(text)} chars")
        try:
            logger.info("🔊 Generating speech...")
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_config.voice_id}/stream"
            logger.debug(f"   TTS URL: {url.split('/stream')[0]}...")
            logger.debug(f"   Voice ID: {self.elevenlabs_config.voice_id}")
            logger.debug(f"   Model: {self.elevenlabs_config.model}")
            
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
            logger.debug(f"   Voice settings: stability={self.elevenlabs_config.stability}, similarity_boost={self.elevenlabs_config.similarity_boost}")
            
            # Make request in thread pool to avoid blocking
            logger.debug("   Sending request to ElevenLabs API (in thread pool)")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=data, headers=headers, stream=True)
            )
            logger.debug(f"   ElevenLabs API response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.debug("   ✅ ElevenLabs API request successful, streaming audio")
                # Stream audio to browser
                chunk_count = 0
                total_bytes = 0
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        chunk_count += 1
                        total_bytes += len(chunk)
                        await websocket.send(chunk)
                        if chunk_count % 10 == 0:
                            logger.debug(f"   Sent {chunk_count} audio chunks ({total_bytes} bytes)")
                
                logger.info(f"✅ Audio sent to browser ({chunk_count} chunks)")
                logger.debug(f"   Total audio bytes sent: {total_bytes}")
                
                # Small delay to ensure last audio chunk is fully sent
                logger.debug("   Waiting 200ms to ensure last chunk is sent")
                await asyncio.sleep(0.2)
                
                # Send completion signal to client
                logger.debug("📤 Sending TTS completion signal to client")
                await websocket.send(json.dumps({'type': 'tts_complete'}))
                logger.info("📢 TTS completion signal sent to client")
                logger.debug("✅ Text-to-speech process completed successfully")
            else:
                logger.error(f"❌ TTS error: {response.status_code} - {response.text}")
                logger.debug(f"   Response headers: {dict(response.headers)}")
                
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
            logger.exception("   Full exception traceback:")
