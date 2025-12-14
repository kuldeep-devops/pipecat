"""
Levo Wellness - Smart Knowledge Base Loader

Optimized for conversational, context-aware interactions

"""
import json
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LevoWellnessSmartKB:
    """
    Smart Knowledge Base for Conversational AI
    Only provides information when asked, supports natural dialogue flow
    """
    
    def __init__(self, data_path="knowledge_base.json"):
        self.data_path = data_path
        self.data = self._load_data()

    def _load_data(self):
        """Load knowledge base from JSON file"""
        try:
            if not os.path.exists(self.data_path):
                logger.warning(f"⚠️ KB file not found at {self.data_path}")
                return {}
            
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("🌿 Levo Wellness smart KB loaded")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load KB: {e}")
            return {}

    def get_greeting(self, mode="voice_nano"):
        """Get ultra-minimal greeting (default: shortest)"""
        greetings = self.data.get('greeting_message', {})
        return greetings.get(mode, "Hi. How can I help?")

    # Service lookup methods
    
    def find_service(self, query):
        """
        Smart service finder based on natural language query
        Returns: service info or None
        """
        query_lower = query.lower()
        keywords = self.data.get('conversation_hints', {}).get('service_keywords', {})
        
        # Check keywords
        for keyword, service_type in keywords.items():
            if keyword in query_lower:
                return self.get_service_by_type(service_type)
        
        return None

    def get_service_by_type(self, service_type):
        """Get service details by type (spa, hair, yoga, etc.)"""
        services = self.data.get('services', {})
        
        # Search in salon
        salon = services.get('salon', {})
        if service_type in salon:
            return salon[service_type]
        
        # Search in wellness
        wellness = services.get('wellness', {})
        if service_type in wellness:
            return wellness[service_type]
        
        return None

    def get_doctor(self, specialty):
        """Get doctor info by specialty"""
        doctors = self.data.get('doctors', {})
        return doctors.get(specialty, None)

    def check_doctor_availability(self, specialty, day, time=None):
        """
        Check if doctor is available on a specific day/time
        Returns: available slots or availability status
        """
        doctor = self.get_doctor(specialty)
        if not doctor:
            return None
        
        day_lower = day.lower()
        
        # Check if day is available
        if day_lower not in doctor.get('available_days', []):
            return {"available": False, "message": f"Dr. {doctor['name']} is not available on {day}."}
        
        # Get slots for that day
        slots = doctor.get('slots', {}).get(day_lower, [])
        
        if time:
            # Check specific time
            if time in slots:
                return {"available": True, "time": time}
            else:
                return {"available": False, "message": f"{time} is not available.", "alternatives": slots}
        else:
            # Return all available slots
            return {"available": True, "slots": slots}

    def get_price(self, service_type):
        """Get price only when specifically asked"""
        service = self.get_service_by_type(service_type)
        if service:
            if 'price_range' in service:
                return service['price_range']
            elif 'price' in service:
                return {"min": service['price'], "max": service['price']}
        
        # Check if it's a doctor
        doctors = self.data.get('doctors', {})
        for specialty, doctor in doctors.items():
            if service_type in specialty or service_type in doctor.get('short_name', ''):
                return {"fee": doctor.get('consultation_fee')}
        
        return None

    def get_minimal_context(self, query):
        """
        Get only the minimal context needed for a query
        Don't dump all information
        """
        query_lower = query.lower()
        context_parts = []
        
        # Only add what's needed based on query
        if any(word in query_lower for word in ['book', 'appointment', 'when', 'time', 'available']):
            # User wants to book - prepare minimal booking context
            context_parts.append("## Booking Process")
            context_parts.append("1. Ask when they want to come")
            context_parts.append("2. Check availability")
            context_parts.append("3. Get name and phone")
            context_parts.append("4. Confirm booking")
        
        if any(word in query_lower for word in ['price', 'cost', 'how much', 'fee']):
            # User asks about price - only then provide pricing
            context_parts.append("## Pricing Information Available")
            context_parts.append("(Look up specific price when user asks about a service)")
        
        if any(word in query_lower for word in ['doctor', 'dermatologist', 'nutritionist']):
            context_parts.append("## Doctors")
            context_parts.append("- Dermatologist: Dr. Anjali Khanna")
            context_parts.append("- Nutritionist: Ms. Priya Sengupta")
        
        return '\n'.join(context_parts) if context_parts else ""

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
