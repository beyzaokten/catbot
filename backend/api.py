from fastapi import FastAPI, HTTPException, Depends
import uvicorn
from sqlalchemy.orm import Session
from .models.chat import Message, ChatRequest, ChatResponse, ModelsResponse
from .services.llm_service import LLMModel
from .database.database import get_db, init_database
from .repositories.chat_repository import ChatRepository

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_database()
    print("✅ Database initialized")

llm_model = LLMModel()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat requests with database persistence"""
    try:
        chat_repo = ChatRepository(db)
        
        conversation = chat_repo.get_or_create_conversation(request.conversation_id)
        
        # Add user message to database
        user_message = chat_repo.add_message(conversation.id, "user", request.message)
        
        # Get conversation history for LLM context
        messages = chat_repo.get_conversation_messages(conversation.id)
        history = [{"role": msg.role, "content": msg.content} for msg in messages[:-1]]  
        
        # If a specific model is requested, update the model
        if request.model_name and request.model_name != llm_model.model_name:
            llm_model.__init__(model_name=request.model_name)
        
        llm_model.history = history
        
        llm_response = llm_model.get_response(request.message)
        
        if isinstance(llm_response, dict) and 'text' in llm_response:
            llm_response = llm_response['text']
        
        # Add assistant response to database
        assistant_message = chat_repo.add_message(conversation.id, "assistant", llm_response)
        
        return ChatResponse(
            response=llm_response,
            conversation_id=conversation.id,
            message_id=assistant_message.id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models", response_model=ModelsResponse)
async def get_models():
    """Get available models"""
    try:
        models = llm_model.get_available_models()
        return ModelsResponse(models=models)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    """Get all conversations"""
    try:
        chat_repo = ChatRepository(db)
        conversations = chat_repo.get_conversations()
        
        conversation_list = []
        for conv in conversations:
            message_count = len(chat_repo.get_conversation_messages(conv.id))
            conversation_list.append({
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": message_count
            })
        
        return {"conversations": conversation_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Get a specific conversation with messages"""
    try:
        chat_repo = ChatRepository(db)
        conversation_data = chat_repo.get_conversation_with_messages(conversation_id)
        
        if not conversation_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation_data
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversations")
async def create_conversation(title: str = "New Conversation", db: Session = Depends(get_db)):
    """Create a new conversation"""
    try:
        chat_repo = ChatRepository(db)
        conversation = chat_repo.create_conversation(title)
        
        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete a conversation"""
    try:
        chat_repo = ChatRepository(db)
        success = chat_repo.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"status": "success", "message": "Conversation deleted"}
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversations/{conversation_id}/clear")
async def clear_conversation_history(conversation_id: int, db: Session = Depends(get_db)):
    """Clear messages from a conversation"""
    try:
        chat_repo = ChatRepository(db)
        success = chat_repo.clear_conversation_messages(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"status": "success", "message": "Conversation history cleared"}
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_history")
async def clear_all_history(db: Session = Depends(get_db)):
    """Clear all chat history"""
    try:
        chat_repo = ChatRepository(db)
        conversations = chat_repo.get_conversations()
        
        for conv in conversations:
            chat_repo.delete_conversation(conv.id)
        
        return {"status": "success", "message": "All chat history cleared"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

def start_server(host="127.0.0.1", port=8000):
    uvicorn.run(app, host=host, port=port) 