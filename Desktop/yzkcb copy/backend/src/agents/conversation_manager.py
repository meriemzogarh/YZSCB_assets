# src/agents/conversation_manager.py

from langchain.memory import ConversationBufferWindowMemory
from typing import List, Dict

class ConversationManager:
    """
    Manage multi-turn conversations with context retention
    """
    
    def __init__(self, max_turns: int = 10):
        self.memory = ConversationBufferWindowMemory(
            k=max_turns,
            return_messages=True,
            memory_key="conversation_history"
        )
        self.session_context = {}
    
    def add_turn(self, role: str, content: str):
        """Add conversation turn"""
        if role == "user":
            self.memory.chat_memory.add_user_message(content)
        else:
            self.memory.chat_memory.add_ai_message(content)
    
    def get_context_window(self) -> str:
        """Get formatted context for agent"""
        messages = self.memory.chat_memory.messages
        
        formatted = []
        for msg in messages:
            role = "User" if msg.type == "human" else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        
        return "\n".join(formatted)
    
    def extract_entities(self, text: str) -> Dict:
        """Extract relevant entities (part numbers, project IDs, etc.)"""
        import re
        
        entities = {
            "part_numbers": re.findall(r'\b[A-Z]{2,}\d{4,}\b', text),
            "project_ids": re.findall(r'\b(M1a|M2|P1|P2|X1)\b', text),
            "suppliers": re.findall(r'(?:supplier|Supplier)[:\s]+(\w+)', text),
        }
        
        return entities
    
    def set_context_variable(self, key: str, value: str):
        """Store session context"""
        self.session_context[key] = value
    
    def get_context_variable(self, key: str):
        """Retrieve session context"""
        return self.session_context.get(key)