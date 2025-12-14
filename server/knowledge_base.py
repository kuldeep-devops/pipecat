"""
Levo Wellness Demo - Compact Knowledge Base Loader
"""
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LevoWellnessDemoKB:
    """Compact demo version of Levo Wellness Knowledge Base"""
    
    def __init__(self, data_path="levo_wellness_demo_kb.json"):
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
                logger.info("🌿 Levo Wellness demo KB loaded")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load KB: {e}")
            return {}

    def get_greeting(self, mode="voice"):
        """
        Get greeting message
        mode: 'voice' (TTS-friendly) or 'text' (with emoji)
        """
        if mode == "voice":
            return "Welcome to Lay-vo Wellness Center. Your wellness journey starts here. How can I help you today?"
        else:
            return "🌿 Welcome to Levo Wellness Center!\n\nYour wellness journey starts here. How can I help you today?"

    def get_clinic_info(self):
        """Get basic clinic information"""
        return self.data.get('clinic_info', {})

    def get_all_doctors(self):
        """Get all doctors"""
        return self.data.get('doctors', {})

    def get_doctor(self, specialty):
        """Get specific doctor by specialty"""
        doctors = self.get_all_doctors()
        return doctors.get(specialty, None)

    def get_services(self, department=None):
        """Get services, optionally filtered by department"""
        departments = self.data.get('departments', {})
        if department:
            return departments.get(department, {}).get('services', {})
        
        # Return all services
        all_services = {}
        for dept_name, dept in departments.items():
            all_services[dept_name] = dept.get('services', {})
        return all_services

    def get_packages(self):
        """Get wellness packages"""
        return self.data.get('packages', {}).get('wellness_packages', [])

    def get_faqs(self):
        """Get FAQs"""
        return self.data.get('faqs', [])

    def get_booking_policies(self):
        """Get booking policies"""
        return self.data.get('booking_policies', {})

    def search_services(self, keyword):
        """Search services by keyword"""
        results = []
        keyword_lower = keyword.lower()
        
        departments = self.data.get('departments', {})
        for dept_name, dept in departments.items():
            services = dept.get('services', {})
            for service_key, service in services.items():
                if keyword_lower in service.get('name', '').lower():
                    results.append({
                        'department': dept_name,
                        'name': service['name'],
                        'price': service.get('price') or service.get('price_range', {})
                    })
        return results

    def get_context_string(self, user_query=None):
        """Get context string for LLM"""
        if not self.data:
            return ""

        parts = ["## LEVO WELLNESS CENTER"]
        
        # Basic info
        info = self.get_clinic_info()
        parts.append(f"\n📍 Location: {info.get('location', 'N/A')}")
        parts.append(f"📞 Phone: {info.get('contact', {}).get('main_phone', 'N/A')}")
        
        # If query is provided, return relevant context only
        if user_query:
            query_lower = user_query.lower()
            
            # Doctor queries
            if any(word in query_lower for word in ['doctor', 'dermatologist', 'nutritionist', 'appointment']):
                parts.append("\n### Doctors")
                for specialty, doctor in self.get_all_doctors().items():
                    parts.append(f"- {doctor['name']} ({specialty}): ₹{doctor['consultation_fee']}")
            
            # Service queries
            if any(word in query_lower for word in ['service', 'massage', 'hair', 'spa', 'yoga', 'meditation']):
                parts.append("\n### Services")
                for dept_name, services in self.get_services().items():
                    for service in services.values():
                        price = service.get('price') or f"₹{service.get('price_range', {}).get('min', 0)}-{service.get('price_range', {}).get('max', 0)}"
                        parts.append(f"- {service['name']}: {price}")
            
            # Package queries
            if 'package' in query_lower:
                parts.append("\n### Packages")
                for pkg in self.get_packages():
                    parts.append(f"- {pkg['name']}: ₹{pkg['price']}")
        
        else:
            # Return full context
            parts.append("\n### Doctors")
            for doctor in self.get_all_doctors().values():
                parts.append(f"- {doctor['name']}: ₹{doctor['consultation_fee']}")
            
            parts.append("\n### Services")
            for dept_name, services in self.get_services().items():
                parts.append(f"\n{dept_name.title()}:")
                for service in services.values():
                    parts.append(f"  - {service['name']}")
        
        return "\n".join(parts)


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("LEVO WELLNESS DEMO KB - TESTING")
    print("=" * 60)
    
    kb = LevoWellnessDemoKB()
    
    print("\n1. GREETINGS:")
    print("-" * 60)
    print("Voice mode:", kb.get_greeting("voice"))
    print("\nText mode:", kb.get_greeting("text"))
    
    print("\n2. DOCTORS:")
    print("-" * 60)
    for specialty, doctor in kb.get_all_doctors().items():
        print(f"- {doctor['name']} ({specialty}): ₹{doctor['consultation_fee']}")
    
    print("\n3. SERVICES:")
    print("-" * 60)
    for dept, services in kb.get_services().items():
        print(f"\n{dept.title()}:")
        for service in services.values():
            print(f"  - {service['name']}")
    
    print("\n4. PACKAGES:")
    print("-" * 60)
    for pkg in kb.get_packages():
        print(f"- {pkg['name']}: ₹{pkg['price']}")
    
    print("\n5. SMART CONTEXT:")
    print("-" * 60)
    query = "book dermatologist"
    context = kb.get_context_string(query)
    print(f"Query: '{query}'")
    print(f"\n{context}")
    
    print("\n" + "=" * 60)
    print("✅ Demo KB test completed!")
    print("=" * 60)
