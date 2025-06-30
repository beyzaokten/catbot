from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from llm_model import LLMModel
import uvicorn

app = FastAPI()

# Initialize the LLM model
llm_model = LLMModel()

# Define data models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = None
    model_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    
class ModelsResponse(BaseModel):
    models: List[str]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests"""
    try:
        # If a specific model is requested, update the model
        if request.model_name and request.model_name != llm_model.model_name:
            llm_model.__init__(model_name=request.model_name)
        
        # If history is provided, update model history
        if request.history:
            llm_model.history = [{"role": msg.role, "content": msg.content} for msg in request.history]
        
        response = llm_model.get_response(request.message)
        
        if isinstance(response, dict) and 'text' in response:
            response = response['text']
        
        return ChatResponse(response=response)
    
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

@app.post("/clear_history")
async def clear_history():
    """Clear chat history"""
    try:
        llm_model.clear_history()
        return {"status": "success", "message": "Chat history cleared"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

def start_server(host="127.0.0.1", port=8000):
    uvicorn.run(app, host=host, port=port) 