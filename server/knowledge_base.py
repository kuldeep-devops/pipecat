"""
Knowledge Base Loader
"""
import json
import os
from loguru import logger

class HealthcareKnowledgeBase:
    def __init__(self, data_path="data/knowledge_base.json"):
        self.data_path = data_path
        self.data = self._load_data()

    def _load_data(self):
        """Load knowledge base from JSON file"""
        try:
            if not os.path.exists(self.data_path):
                logger.warning(f"⚠️ Knowledge base file not found at {self.data_path}")
                return {}
            
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                logger.info("📚 Knowledge base loaded successfully")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load knowledge base: {e}")
            return {}

    def get_context_string(self):
        """Convert KB data into a context string for the LLM"""
        if not self.data:
            return ""

        context_parts = ["## INSTITUTIONAL KNOWLEDGE BASE"]
        
        # Hospital Info
        info = self.data.get('hospital_info', {})
        context_parts.append(f"### General Info\nName: {info.get('name')}\nAddress: {info.get('address')}")
        
        if 'visiting_hours' in info:
            context_parts.append("Visiting Hours:")
            for ward, hours in info['visiting_hours'].items():
                context_parts.append(f"- {ward.replace('_', ' ').title()}: {hours}")

        # Departments
        if 'departments' in self.data:
            context_parts.append("\n### Departments")
            for dept in self.data['departments']:
                context_parts.append(f"- {dept['name']} (Head: {dept['head']}, Loc: {dept['location']})")

        # Insurance
        ins = self.data.get('insurance_policies', {})
        if ins:
            context_parts.append("\n### Insurance & Billing")
            context_parts.append(f"Accepted Providers: {', '.join(ins.get('accepted_providers', []))}")
            context_parts.append(f"Policy: {ins.get('co_pay_policy')}")

        # Appointments
        appt = self.data.get('appointments', {})
        if appt:
            context_parts.append("\n### Appointment Rules")
            context_parts.append(f"Cancellation: {appt.get('cancellation_policy')}")
            context_parts.append(f"Items to Bring: {', '.join(appt.get('what_to_bring', []))}")

        return "\n".join(context_parts)
