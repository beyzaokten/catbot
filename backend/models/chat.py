from pydantic import BaseModel
from typing import List, Optional, Dict

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None  # For existing conversations
    history: Optional[List[Message]] = None 
    model_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    message_id: int
    
class ModelsResponse(BaseModel):
    models: List[str]

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int

class ConversationsListResponse(BaseModel):
    conversations: List[ConversationResponse]

class ConversationWithMessagesResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    messages: List[Dict]

class FileResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    mime_type: str
    uploaded_at: str
    conversation_id: Optional[int] = None

class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file: Optional[FileResponse] = None

class FileListResponse(BaseModel):
    files: List[FileResponse] 