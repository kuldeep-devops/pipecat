"""
Levo Wellness Knowledge Base Loader
"""
import json
import os
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LevoWellnessKnowledgeBase:
    """
    Knowledge Base manager for Levo Wellness Center
    Loads and provides access to all clinic information
    """
    
    def __init__(self, data_path="data/levo_wellness_knowledge_base.json"):
        self.data_path = data_path
        self.data = self._load_data()

    def _load_data(self):
        """Load knowledge base from JSON file"""
        try:
            if not os.path.exists(self.data_path):
                logger.warning(f"⚠️ Knowledge base file not found at {self.data_path}")
                return {}
            
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("🌿 Levo Wellness knowledge base loaded successfully")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load knowledge base: {e}")
            return {}

    def get_greeting_message(self):
        """Get the greeting message"""
        return self.data.get('greeting_message', {}).get('primary', 
            "🌿 Namaste! Welcome to Levo Wellness.\n\nYour wellness journey starts here. How can I help you today?")

    def get_clinic_info(self):
        """Get basic clinic information"""
        return self.data.get('clinic_info', {})

    def get_all_doctors(self):
        """Get information about all doctors"""
        return self.data.get('doctors', {})

    def get_doctor_by_specialty(self, specialty):
        """
        Get doctor information by specialty
        specialty: 'dermatologist', 'ayurveda', 'nutritionist', 'pain_relief'
        """
        doctors = self.data.get('doctors', {})
        return doctors.get(specialty, None)

    def get_doctor_slots(self, specialty, day=None):
        """
        Get available slots for a doctor
        specialty: 'dermatologist', 'ayurveda', 'nutritionist', 'pain_relief'
        day: optional specific day (e.g., 'monday', 'tuesday')
        """
        doctor = self.get_doctor_by_specialty(specialty)
        if not doctor:
            return None
        
        slots = doctor.get('available_days_slots', {})
        if day:
            return slots.get(day.lower(), [])
        return slots

    def get_department_services(self, department):
        """
        Get all services in a department
        department: 'salon', 'aesthetics', 'wellness'
        """
        departments = self.data.get('departments', {})
        return departments.get(department, {}).get('services', {})

    def get_service_details(self, department, service_key):
        """
        Get details for a specific service
        department: 'salon', 'aesthetics', 'wellness'
        service_key: 'hair', 'nail', 'spa', 'skin_health', etc.
        """
        services = self.get_department_services(department)
        return services.get(service_key, None)

    def search_services(self, keyword):
        """Search for services by keyword"""
        results = []
        keyword_lower = keyword.lower()
        
        departments = self.data.get('departments', {})
        for dept_name, dept in departments.items():
            services = dept.get('services', {})
            for service_key, service in services.items():
                service_name = service.get('name', '').lower()
                services_offered = ' '.join(service.get('services_offered', [])).lower()
                
                if keyword_lower in service_name or keyword_lower in services_offered:
                    results.append({
                        'department': dept_name,
                        'service_key': service_key,
                        'name': service['name'],
                        'price_range': service.get('price_range', {}),
                        'duration': service.get('duration', 'N/A')
                    })
        
        return results

    def get_wellness_packages(self):
        """Get all wellness packages"""
        return self.data.get('packages', {}).get('wellness_packages', [])

    def get_memberships(self):
        """Get all membership plans"""
        return self.data.get('packages', {}).get('memberships', [])

    def get_package_by_name(self, package_name):
        """Find a package by name (partial match)"""
        packages = self.get_wellness_packages()
        package_name_lower = package_name.lower()
        
        for package in packages:
            if package_name_lower in package['name'].lower():
                return package
        return None

    def get_membership_by_tier(self, tier):
        """Get membership by tier (Silver, Gold, Platinum)"""
        memberships = self.get_memberships()
        tier_lower = tier.lower()
        
        for membership in memberships:
            if tier_lower == membership['tier'].lower():
                return membership
        return None

    def get_booking_policies(self):
        """Get booking and cancellation policies"""
        return self.data.get('booking_policies', {})

    def get_faqs(self, keyword=None):
        """
        Get FAQs, optionally filtered by keyword
        """
        faqs = self.data.get('faqs', [])
        
        if keyword:
            keyword_lower = keyword.lower()
            return [faq for faq in faqs 
                   if keyword_lower in faq['question'].lower() 
                   or keyword_lower in faq['answer'].lower()]
        
        return faqs

    def get_contact_info(self):
        """Get contact information"""
        clinic_info = self.get_clinic_info()
        return clinic_info.get('contact', {})

    def get_operating_hours(self):
        """Get operating hours"""
        clinic_info = self.get_clinic_info()
        return clinic_info.get('operating_hours', {})

    def get_context_string(self, user_query=None):
        """
        Convert KB data into a context string for the LLM
        If user_query provided, returns relevant context only
        Otherwise returns complete knowledge base context
        """
        if not self.data:
            return ""

        context_parts = ["## LEVO WELLNESS CENTER KNOWLEDGE BASE"]
        
        # If user query provided, extract relevant context
        if user_query:
            query_lower = user_query.lower()
            
            # Doctor-related queries
            if any(word in query_lower for word in ['doctor', 'dermatologist', 'ayurveda', 'nutritionist', 'pain', 'specialist', 'consultation']):
                context_parts.append(self._format_doctors_context())
            
            # Service-related queries
            if any(word in query_lower for word in ['service', 'treatment', 'massage', 'facial', 'hair', 'nail', 'spa', 'yoga', 'pilates', 'meditation']):
                context_parts.append(self._format_services_context())
            
            # Package/membership queries
            if any(word in query_lower for word in ['package', 'membership', 'offer', 'discount', 'deal']):
                context_parts.append(self._format_packages_context())
            
            # Booking-related queries
            if any(word in query_lower for word in ['book', 'appointment', 'schedule', 'slot', 'available', 'cancel']):
                context_parts.append(self._format_booking_context())
            
            # Price/cost queries
            if any(word in query_lower for word in ['price', 'cost', 'fee', 'charge', 'payment']):
                context_parts.append(self._format_pricing_context())
            
            # Always include contact info
            context_parts.append(self._format_contact_context())
            
        else:
            # Return complete context
            context_parts.append(self._format_clinic_info())
            context_parts.append(self._format_doctors_context())
            context_parts.append(self._format_services_context())
            context_parts.append(self._format_packages_context())
            context_parts.append(self._format_booking_context())
            context_parts.append(self._format_contact_context())

        return "\n\n".join(filter(None, context_parts))

    def _format_clinic_info(self):
        """Format clinic information"""
        info = self.get_clinic_info()
        if not info:
            return ""
        
        parts = ["### Clinic Information"]
        parts.append(f"**{info.get('name', 'Levo Wellness Center')}**")
        parts.append(f"Location: {info.get('location', 'N/A')}")
        parts.append(f"Mission: {info.get('mission', '')}")
        
        hours = info.get('operating_hours', {})
        if hours:
            parts.append("\n**Operating Hours:**")
            for day_range, time_range in hours.items():
                parts.append(f"- {day_range.replace('_', ' ').title()}: {time_range}")
        
        return "\n".join(parts)

    def _format_doctors_context(self):
        """Format doctors information"""
        doctors = self.get_all_doctors()
        if not doctors:
            return ""
        
        parts = ["### Available Doctors & Specialists"]
        
        for specialty, doctor in doctors.items():
            parts.append(f"\n**{doctor['name']}** - {specialty.replace('_', ' ').title()}")
            parts.append(f"- Qualification: {doctor['qualification']}")
            parts.append(f"- Experience: {doctor['experience_years']} years")
            parts.append(f"- Consultation Fee: ₹{doctor['consultation_fee']}")
            
            # Format specializations
            if doctor.get('specialization'):
                parts.append(f"- Specializes in: {', '.join(doctor['specialization'][:3])}")
            
            # Format available days
            slots = doctor.get('available_days_slots', {})
            if slots:
                days = ', '.join([day.capitalize() for day in slots.keys()])
                parts.append(f"- Available Days: {days}")
        
        return "\n".join(parts)

    def _format_services_context(self):
        """Format services information"""
        departments = self.data.get('departments', {})
        if not departments:
            return ""
        
        parts = ["### Available Services"]
        
        for dept_name, dept in departments.items():
            parts.append(f"\n**{dept['name']}**")
            services = dept.get('services', {})
            
            for service_key, service in services.items():
                parts.append(f"\n*{service['name']}*")
                
                # Price range
                price_range = service.get('price_range')
                if price_range:
                    parts.append(f"- Price: ₹{price_range['min']} - ₹{price_range['max']}")
                
                # Duration
                if service.get('duration'):
                    parts.append(f"- Duration: {service['duration']}")
                
                # Services offered (first 3)
                services_offered = service.get('services_offered', [])
                if services_offered:
                    parts.append(f"- Includes: {', '.join(services_offered[:3])}")
        
        return "\n".join(parts)

    def _format_packages_context(self):
        """Format packages and memberships"""
        parts = ["### Wellness Packages & Memberships"]
        
        # Wellness packages
        packages = self.get_wellness_packages()
        if packages:
            parts.append("\n**Wellness Packages:**")
            for pkg in packages[:5]:  # First 5 packages
                parts.append(f"\n- **{pkg['name']}**: ₹{pkg['price']}")
                if pkg.get('validity'):
                    parts.append(f"  Valid for: {pkg['validity']}")
                parts.append(f"  Includes: {', '.join(pkg['includes'][:2])}")
        
        # Memberships
        memberships = self.get_memberships()
        if memberships:
            parts.append("\n**Membership Plans:**")
            for mem in memberships:
                parts.append(f"\n- **{mem['tier']}**: ₹{mem['price']}/{mem['billing']}")
                parts.append(f"  Benefits: {', '.join(mem['benefits'][:2])}")
        
        return "\n".join(parts)

    def _format_booking_context(self):
        """Format booking policies"""
        policies = self.get_booking_policies()
        if not policies:
            return ""
        
        parts = ["### Booking Policies"]
        parts.append(f"- Advance Booking: {policies.get('advance_booking', 'N/A')}")
        parts.append(f"- Same Day: {policies.get('same_day', 'N/A')}")
        
        cancellation = policies.get('cancellation', {})
        if cancellation:
            parts.append(f"- Cancellation Notice: {cancellation.get('notice_required', 'N/A')}")
            parts.append(f"- Late Cancellation Charge: {cancellation.get('late_cancellation_charge', 'N/A')}")
        
        parts.append(f"- Rescheduling: {policies.get('rescheduling', 'N/A')}")
        parts.append(f"- First-time Clients: {policies.get('first_time_clients', 'N/A')}")
        
        return "\n".join(parts)

    def _format_pricing_context(self):
        """Format pricing information for common services"""
        parts = ["### Pricing Overview"]
        
        # Get some sample pricing from different departments
        departments = self.data.get('departments', {})
        
        for dept_name, dept in departments.items():
            services = dept.get('services', {})
            if services:
                parts.append(f"\n**{dept['name']}:**")
                for service_key, service in list(services.items())[:2]:  # First 2 services
                    price_range = service.get('price_range', {})
                    if price_range:
                        parts.append(f"- {service['name']}: ₹{price_range['min']} - ₹{price_range['max']}")
        
        return "\n".join(parts)

    def _format_contact_context(self):
        """Format contact information"""
        contact = self.get_contact_info()
        clinic_info = self.get_clinic_info()
        
        if not contact:
            return ""
        
        parts = ["### Contact Information"]
        parts.append(f"📍 Location: {clinic_info.get('location', 'N/A')}")
        parts.append(f"📞 Phone: {contact.get('main_phone', 'N/A')}")
        parts.append(f"💬 WhatsApp: {contact.get('whatsapp', 'N/A')}")
        parts.append(f"📧 Email: {contact.get('email_general', 'N/A')}")
        parts.append(f"🌐 Website: {contact.get('website', 'N/A')}")
        
        return "\n".join(parts)

    def get_emergency_contacts(self):
        """Get emergency contact information"""
        return self.data.get('emergency_contacts', {})

    def get_special_features(self):
        """Get special features like corporate wellness, workshops, etc."""
        return self.data.get('special_features', {})

    def get_current_offers(self):
        """Get current promotional offers"""
        return self.data.get('current_offers', [])


# Backward compatibility - keep the old class name as alias
HealthcareKnowledgeBase = LevoWellnessKnowledgeBase


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("LEVO WELLNESS KNOWLEDGE BASE - TESTING")
    print("=" * 70)
    
    # Initialize
    kb = LevoWellnessKnowledgeBase("levo_wellness_knowledge_base.json")
    
    # Test 1: Greeting
    print("\n1. GREETING MESSAGE:")
    print("-" * 70)
    print(kb.get_greeting_message())
    
    # Test 2: Get all doctors
    print("\n2. ALL DOCTORS:")
    print("-" * 70)
    doctors = kb.get_all_doctors()
    for specialty, doctor in doctors.items():
        print(f"- {doctor['name']} ({specialty}): ₹{doctor['consultation_fee']}")
    
    # Test 3: Search services
    print("\n3. SEARCH SERVICES (keyword: 'massage'):")
    print("-" * 70)
    results = kb.search_services('massage')
    for result in results:
        print(f"- {result['name']}: ₹{result['price_range'].get('min', 'N/A')}-{result['price_range'].get('max', 'N/A')}")
    
    # Test 4: Get packages
    print("\n4. WELLNESS PACKAGES:")
    print("-" * 70)
    packages = kb.get_wellness_packages()
    for pkg in packages[:3]:
        print(f"- {pkg['name']}: ₹{pkg['price']}")
    
    # Test 5: Get doctor slots
    print("\n5. DERMATOLOGIST SLOTS (Monday):")
    print("-" * 70)
    slots = kb.get_doctor_slots('dermatologist', 'monday')
    print(f"Available: {', '.join(slots) if slots else 'None'}")
    
    # Test 6: Get context for specific query
    print("\n6. CONTEXT STRING FOR QUERY:")
    print("-" * 70)
    query = "I want to book a dermatologist"
    context = kb.get_context_string(query)
    print(f"Query: '{query}'")
    print(f"Context length: {len(context)} characters")
    print(f"Preview:\n{context[:300]}...")
    
    # Test 7: Get FAQs
    print("\n7. FAQs (keyword: 'booking'):")
    print("-" * 70)
    faqs = kb.get_faqs('booking')
    for faq in faqs[:2]:
        print(f"Q: {faq['question']}")
        print(f"A: {faq['answer'][:100]}...\n")
    
    # Test 8: Contact info
    print("\n8. CONTACT INFORMATION:")
    print("-" * 70)
    contact = kb.get_contact_info()
    print(f"Phone: {contact.get('main_phone')}")
    print(f"WhatsApp: {contact.get('whatsapp')}")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
