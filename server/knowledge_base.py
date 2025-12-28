"""
Levo Wellness - Smart Knowledge Base Loader

Optimized for conversational, context-aware interactions

"""
import json
import os
from datetime import datetime
from loguru import logger


class LevoWellnessSmartKB:
    """
    Smart Knowledge Base for Conversational AI
    Only provides information when asked, supports natural dialogue flow
    """
    
    def __init__(self, data_path="knowledge_base.json"):
        logger.debug(f"🔧 Initializing LevoWellnessSmartKB")
        logger.debug(f"   Data path: {data_path}")
        self.data_path = data_path
        self.data = self._load_data()
        logger.debug(f"✅ LevoWellnessSmartKB initialized")

    def _load_data(self):
        """Load knowledge base from JSON file"""
        logger.debug(f"📚 Loading knowledge base from: {self.data_path}")
        try:
            if not os.path.exists(self.data_path):
                logger.warning(f"⚠️ KB file not found at {self.data_path}")
                logger.debug(f"   Absolute path: {os.path.abspath(self.data_path)}")
                logger.debug(f"   Current directory: {os.getcwd()}")
                return {}
            
            logger.debug(f"   File exists, opening and parsing JSON")
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("🌿 Levo Wellness smart KB loaded")
                logger.debug(f"   KB data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                logger.debug(f"   KB file size: {os.path.getsize(self.data_path)} bytes")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse KB JSON: {e}")
            logger.exception("   Full exception traceback:")
            return {}
        except Exception as e:
            logger.error(f"❌ Failed to load KB: {e}")
            logger.exception("   Full exception traceback:")
            return {}

    def get_greeting(self, mode="voice_nano"):
        """Get ultra-minimal greeting (default: shortest)"""
        logger.debug(f"📝 get_greeting called with mode: {mode}")
        greetings = self.data.get('greeting_message', {})
        logger.debug(f"   Available greeting modes: {list(greetings.keys())}")
        greeting = greetings.get(mode, "Hi. How can I help?")
        logger.debug(f"   Selected greeting: '{greeting}'")
        return greeting

    # Service lookup methods
    
    def find_service(self, query):
        """
        Smart service finder based on natural language query
        Returns: service info or None
        """
        logger.debug(f"🔍 find_service called with query: '{query}'")
        query_lower = query.lower()
        keywords = self.data.get('conversation_hints', {}).get('service_keywords', {})
        logger.debug(f"   Available service keywords: {list(keywords.keys())}")
        
        # Check keywords
        for keyword, service_type in keywords.items():
            if keyword in query_lower:
                logger.debug(f"   Matched keyword: '{keyword}' -> service_type: '{service_type}'")
                service = self.get_service_by_type(service_type)
                logger.debug(f"   Service found: {service.get('name') if service else None}")
                return service
        
        logger.debug(f"   No service found for query: '{query}'")
        return None

    def get_service_by_type(self, service_type):
        """Get service details by type (spa, hair, yoga, etc.)"""
        logger.debug(f"🔍 get_service_by_type called with service_type: '{service_type}'")
        departments = self.data.get('departments', {})
        logger.debug(f"   Available departments: {list(departments.keys())}")
        
        # Search in Salon department
        salon = departments.get('salon', {}).get('services', {})
        if service_type in salon:
            logger.debug(f"   Found service in Salon department")
            return salon[service_type]
        
        # Search in Aesthetics department
        aesthetics = departments.get('aesthetics', {}).get('services', {})
        if service_type in aesthetics:
            logger.debug(f"   Found service in Aesthetics department")
            return aesthetics[service_type]
        
        # Search in Wellness department
        wellness = departments.get('wellness', {}).get('services', {})
        if service_type in wellness:
            logger.debug(f"   Found service in Wellness department")
            return wellness[service_type]
        
        logger.debug(f"   Service type '{service_type}' not found in any department")
        return None

    def get_doctor(self, specialty):
        """Get doctor info by specialty"""
        logger.debug(f"👨‍⚕️ get_doctor called with specialty: '{specialty}'")
        doctors = self.data.get('doctors', {})
        logger.debug(f"   Available doctor specialties: {list(doctors.keys())}")
        doctor = doctors.get(specialty, None)
        if doctor:
            logger.debug(f"   Found doctor: {doctor.get('name', 'Unknown')}")
        else:
            logger.debug(f"   No doctor found for specialty: '{specialty}'")
        return doctor

    def check_doctor_availability(self, specialty, day, time=None):
        """
        Check if doctor is available on a specific day/time
        Returns: available slots or availability status
        """
        logger.debug(f"📅 check_doctor_availability called: specialty={specialty}, day={day}, time={time}")
        doctor = self.get_doctor(specialty)
        if not doctor:
            logger.debug(f"   Doctor not found for specialty: '{specialty}'")
            return None
        
        day_lower = day.lower()
        available_days = doctor.get('available_days', [])
        logger.debug(f"   Doctor available days: {available_days}")
        
        # Check if day is available
        if day_lower not in available_days:
            logger.debug(f"   Doctor not available on {day}")
            return {"available": False, "message": f"Dr. {doctor['name']} is not available on {day}."}
        
        # Get slots for that day
        slots = doctor.get('slots', {}).get(day_lower, [])
        logger.debug(f"   Available slots on {day}: {slots}")
        
        if time:
            # Check specific time
            logger.debug(f"   Checking specific time: {time}")
            if time in slots:
                logger.debug(f"   Time {time} is available")
                return {"available": True, "time": time}
            else:
                logger.debug(f"   Time {time} is not available, alternatives: {slots}")
                return {"available": False, "message": f"{time} is not available.", "alternatives": slots}
        else:
            # Return all available slots
            logger.debug(f"   Returning all available slots: {slots}")
            return {"available": True, "slots": slots}

    def get_price(self, service_type):
        """Get price only when specifically asked"""
        logger.debug(f"💰 get_price called with service_type: '{service_type}'")
        service = self.get_service_by_type(service_type)
        if service:
            if 'price_range' in service:
                price_range = service['price_range']
                logger.debug(f"   Found price_range: {price_range}")
                return price_range
            elif 'price' in service:
                price = {"min": service['price'], "max": service['price']}
                logger.debug(f"   Found price: {price}")
                return price
        
        # Check if it's a doctor
        logger.debug(f"   Checking if '{service_type}' is a doctor")
        doctors = self.data.get('doctors', {})
        for specialty, doctor in doctors.items():
            if service_type in specialty or service_type in doctor.get('short_name', ''):
                fee = {"fee": doctor.get('consultation_fee')}
                logger.debug(f"   Found doctor consultation fee: {fee}")
                return fee
        
        logger.debug(f"   No price found for service_type: '{service_type}'")
        return None

    def get_minimal_context(self, query):
        """
        Get only the minimal context needed for a query
        Don't dump all information
        """
        logger.debug(f"📋 get_minimal_context called with query: '{query}'")
        query_lower = query.lower()
        context_parts = []
        
        # Only add what's needed based on query
        if any(word in query_lower for word in ['book', 'appointment', 'when', 'time', 'available']):
            logger.debug("   Adding booking process context")
            # User wants to book - prepare minimal booking context
            context_parts.append("## Booking Process")
            context_parts.append("1. Ask when they want to come")
            context_parts.append("2. Check availability")
            context_parts.append("3. Get name and phone")
            context_parts.append("4. Confirm booking")
        
        if any(word in query_lower for word in ['price', 'cost', 'how much', 'fee']):
            logger.debug("   Adding pricing context")
            # User asks about price - only then provide pricing
            context_parts.append("## Pricing Information Available")
            context_parts.append("(Look up specific price when user asks about a service)")
        
        if any(word in query_lower for word in ['doctor', 'dermatologist', 'nutritionist', 'ayurveda', 'pain']):
            logger.debug("   Adding doctors context")
            context_parts.append("## Doctors")
            doctors = self.data.get('doctors', {})
            for specialty, doctor_info in doctors.items():
                context_parts.append(f"- {doctor_info.get('name', specialty)}: {doctor_info.get('qualification', '')}")
        
        context = '\n'.join(context_parts) if context_parts else ""
        logger.debug(f"   Generated context length: {len(context)} chars, parts: {len(context_parts)}")
        return context

    def format_booking_confirmation(self, name, phone, service, date, time, doctor_name=None):
        """Format a booking confirmation message"""
        if doctor_name:
            return f"Perfect! Booked for {name} on {date} at {time} with {doctor_name}. We'll call {phone} if needed. See you then!"
        else:
            return f"Perfect! Booked for {name} on {date} at {time} for {service}. We'll call {phone} if needed. See you then!"

    def get_contact_info(self):
        """Get contact information"""
        return self.data.get('clinic_info', {}).get('contact', {})

    def get_operating_hours(self):
        """Get operating hours"""
        return self.data.get('clinic_info', {}).get('operating_hours', {})

    # Backward compatibility methods
    def get_context_string(self, user_query=None):
        """Get context string for LLM (backward compatibility)"""
        return self.get_minimal_context(user_query or "")

    def get_all_doctors(self):
        """Get all doctors (backward compatibility)"""
        return self.data.get('doctors', {})


# Backward compatibility alias
LevoWellnessDemoKB = LevoWellnessSmartKB


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("LEVO WELLNESS SMART KB - CONVERSATIONAL TESTS")
    print("=" * 70)
    
    kb = LevoWellnessSmartKB()
    
    print("\n1. ULTRA-MINIMAL GREETING:")
    print("-" * 70)
    print(f"Shortest: {kb.get_greeting('voice_nano')}")
    print(f"Short: {kb.get_greeting('voice_tiny')}")
    
    print("\n2. SMART SERVICE FINDER:")
    print("-" * 70)
    test_queries = [
        "I want a massage",
        "Need a haircut",
        "Want to see skin doctor"
    ]
    
    for query in test_queries:
        service = kb.find_service(query)
        if service:
            print(f"Query: '{query}'")
            print(f"Found: {service.get('name')}")
            print()
    
    print("\n3. CHECK DOCTOR AVAILABILITY:")
    print("-" * 70)
    availability = kb.check_doctor_availability('dermatologist', 'monday')
    print(f"Dermatologist on Monday: {availability}")
    
    availability = kb.check_doctor_availability('dermatologist', 'monday', '3:00 PM')
    print(f"Dermatologist Monday at 3 PM: {availability}")
    
    print("\n4. GET PRICE (only when asked):")
    print("-" * 70)
    price = kb.get_price('spa')
    print(f"SPA price: {price}")
    
    price = kb.get_price('dermatologist')
    print(f"Dermatologist fee: {price}")
    
    print("\n5. MINIMAL CONTEXT (smart):")
    print("-" * 70)
    query = "I want to book a massage"
    context = kb.get_minimal_context(query)
    print(f"Query: '{query}'")
    print(f"Context provided:\n{context}")
    
    print("\n6. BOOKING CONFIRMATION:")
    print("-" * 70)
    confirmation = kb.format_booking_confirmation(
        "Raj", "9876543210", "SPA Massage", "Tomorrow", "3:00 PM"
    )
    print(confirmation)
    
    print("\n" + "=" * 70)
    print("✅ Smart conversational KB ready!")
    print("=" * 70)
