from typing import Optional
from .llm_service import LLMModel
import re

class TitleGenerationService:
    def __init__(self):
        self.title_llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM with title generation specific prompt"""
        title_prompt = """You are a title generator. Your only job is to create SHORT, descriptive titles for conversations.

Rules:
- Maximum 5 words
- No quotes, no punctuation except necessary ones
- Capture the main topic or question
- Be specific and helpful
- Use Turkish if the conversation is in Turkish
- Use English if the conversation is in English

Examples:
User: "Nasıl emlak satışı yapabilirim?"
Title: Emlak Satış Stratejileri

User: "Can you help me write a marketing email?"
Title: Marketing Email Writing

User: "Python'da liste nasıl oluşturulur?"
Title: Python Liste Oluşturma

User: "What's the weather like?"
Title: Hava Durumu Sorgusu

Only respond with the title, nothing else."""

        try:
            self.title_llm = LLMModel(
                model_name="llama3",
                temperature=0.3,  
                system_prompt=title_prompt
            )
        except Exception as e:
            print(f"Title LLM initialization error: {e}")
            self.title_llm = None
    
    def generate_title_from_message(self, user_message: str) -> str:
        """Generate a short title from the first user message"""
        if not self.title_llm or not self.title_llm.is_available:
            return self._fallback_title_generation(user_message)
        
        try:
            self.title_llm.clear_history()
            
            title = self.title_llm.get_response(user_message)
            
            title = self._clean_title(title)
            
            # Validate title length and content
            if len(title) > 50 or len(title.split()) > 6:
                return self._fallback_title_generation(user_message)
            
            return title if title else self._fallback_title_generation(user_message)
            
        except Exception as e:
            print(f"Title generation error: {e}")
            return self._fallback_title_generation(user_message)
    
    def generate_title_from_conversation(self, messages: list) -> str:
        """Generate title from multiple messages in conversation"""
        if not messages:
            return "Yeni Sohbet"
        
        # Use first user message for title generation
        first_user_message = None
        for msg in messages:
            if msg.get('role') == 'user':
                first_user_message = msg.get('content', '')
                break
        
        if not first_user_message:
            return "Yeni Sohbet"
        
        return self.generate_title_from_message(first_user_message)
    
    def _clean_title(self, title: str) -> str:
        if not title:
            return ""
        
        # Remove common unwanted phrases
        unwanted_phrases = [
            "Title:", "title:", "TITLE:",
            "Başlık:", "başlık:", "BAŞLIK:",
            "\"", "'", ".", "!", "?",
            "Assistant:", "assistant:",
            "Human:", "human:"
        ]
        
        for phrase in unwanted_phrases:
            title = title.replace(phrase, "")
        
        # Remove extra whitespace and limit length
        title = " ".join(title.split())
        title = title.strip()
        
        # Capitalize first letter of each word (title case)
        title = title.title()
        
        return title[:50] 
    
    def _fallback_title_generation(self, message: str) -> str:
        """Generate title using simple rules when LLM is not available"""
        if not message:
            return "Yeni Sohbet"
        
        # Clean message
        message = message.strip()
        
        # Extract first sentence
        sentences = re.split(r'[.!?]', message)
        first_sentence = sentences[0].strip() if sentences else message
        
        # Take first few words
        words = first_sentence.split()[:5]
        title = " ".join(words)
        
        # Add ellipsis if truncated
        if len(message.split()) > 5:
            title += "..."
        
        # Capitalize
        title = title.capitalize()
        
        return title[:50] if title else "Yeni Sohbet"
    
    def update_conversation_title(self, conversation_id: int, message: str, chat_repo) -> Optional[str]:
        """Update conversation title and return the new title"""
        try:
            new_title = self.generate_title_from_message(message)
            
            updated_conversation = chat_repo.update_conversation_title(conversation_id, new_title)
            
            if updated_conversation:
                return new_title
            
        except Exception as e:
            print(f"Error updating conversation title: {e}")
        
        return None 