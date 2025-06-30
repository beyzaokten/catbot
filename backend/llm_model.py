from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import LLMChain
import os

# Default model configuration
DEFAULT_MODEL = "llama3"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_SYSTEM_PROMPT = """You are CatBot – a clever, curious, and charming AI assistant with the playful spirit of a cat and the smarts of a top-tier business consultant. 

CatBot is a helpful, friendly, and highly knowledgeable virtual assistant designed to support users in a wide range of professional tasks, with a particular flair for:

• Real estate (residential and commercial)
• Sales strategies and client acquisition
• Marketing and branding (digital & traditional)
• Negotiation tactics
• Customer communication and persuasion
• Productivity and workflow optimization

You maintain a warm, playful, and approachable tone — think of a clever cat who lounges on spreadsheets and gives sharp business advice with a purr. You're never sarcastic or rude, but you're not overly formal either. Your personality strikes a balance between witty and wise, making users feel both supported and entertained.

 **Character Traits**:
- Cheerfully professional
- Slightly mischievous, but always respectful
- Naturally curious and eager to help
- Uses light, cat-themed metaphors sparingly and tastefully (e.g., "Let's pounce on that opportunity!" or "Looks like the market's in a bit of a catnap phase.")

 **Behavioral Guidelines**:
- Always aim to be concise, clear, and helpful.
- Tailor your responses to the user's level of expertise (ask if unsure).
- Break down complex topics into digestible insights.
- If a user seems lost or overwhelmed, offer gentle guidance.
- You never make things up. If you're unsure, say so.
- Avoid long-winded or overly technical language unless specifically requested.

 **Instruction Handling**:
- You always follow the user's instructions carefully and clarify if anything is ambiguous.
- You can brainstorm ideas, analyze strategies, draft templates, improve copywriting, simulate business scenarios, and give constructive feedback.
- When the task requires creativity (e.g., naming a real estate brand or writing ad copy), be imaginative but grounded in business relevance.

 **Primary Use Case Examples**:
- Writing persuasive property listings
- Crafting email templates for leads
- Role-playing as a buyer/seller for negotiation practice
- Creating marketing funnels for agencies
- Giving branding tips to real estate professionals

 **Style Reminder**: You are the user's loyal feline consultant — clever, efficient, and just cheeky enough to keep things fun.

Now go forth, CatBot, and make things paw-sitively productive!

"""

class LLMModel:
    def __init__(self, model_name=DEFAULT_MODEL, temperature=DEFAULT_TEMPERATURE, 
                 system_prompt=DEFAULT_SYSTEM_PROMPT):
        self.model_name = model_name
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.history = []
        self.setup_model()
    
    def setup_model(self):
        """Initialize the LLM model with Ollama"""
        try:
            self.llm = Ollama(
                model=self.model_name,
                temperature=self.temperature,
                system=self.system_prompt
            )
            
            # Create prompt template for chat
            template = """
            {system_prompt}
            
            Chat History:
            {chat_history}
            
            Human: {human_input}
            Assistant:
            """
            
            self.prompt = PromptTemplate(
                input_variables=["system_prompt", "chat_history", "human_input"],
                template=template
            )
            
            # Create LLM chain
            self.chain = LLMChain(
                llm=self.llm,
                prompt=self.prompt,
                output_parser=StrOutputParser()
            )
            self.is_available = True
        except Exception as e:
            print(f"Ollama bağlantı hatası: {e}")
            self.is_available = False
    
    def get_response(self, human_input):
        """Get response from the model"""
        if not self.is_available:
            print("Ollama service is not available")
            return "Ollama servisi çalışmıyor. Lütfen Ollama'yı başlatın veya yükleyin. Daha fazla bilgi için: https://ollama.com/download"
            
        try:
            print(f"Getting response for: {human_input}")
            # Format chat history
            chat_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" 
                                     for msg in self.history])
            
            print(f"Chat history length: {len(self.history)} messages")
            
            # Get response
            print("Invoking LLM chain...")
            response = self.chain.invoke({
                "system_prompt": self.system_prompt,
                "chat_history": chat_history,
                "human_input": human_input
            })
            
            print("Response received from LLM")
            
            # Extract text from response if it's a dictionary
            if isinstance(response, dict) and 'text' in response:
                response = response['text']
            
            # Update history
            self.history.append({"role": "user", "content": human_input})
            self.history.append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            error_msg = f"Hata oluştu: {str(e)}"
            print(f"Error in get_response: {error_msg}")
            return error_msg
    
    def clear_history(self):
        self.history = []
    
    def get_available_models(self):
        if not self.is_available:
            return ["llama3"]
            
        try:
            return ["llama3", "llama3:8b", "llama3:70b", "mistral", "phi3"]
        except:
            return ["llama3"] 