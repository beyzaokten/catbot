from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
import uvicorn
from typing import Optional, List
from sqlalchemy.orm import Session
from .models.chat import Message, ChatRequest, ChatResponse, ModelsResponse, FileResponse as FileResponseModel, FileUploadResponse, FileListResponse
from .services.llm_service import LLMModel
from .services.file_service import FileService
from .services.title_service import TitleGenerationService
from .database.database import get_db, init_database
from .repositories.chat_repository import ChatRepository
from .repositories.file_repository import FileRepository
from .database.models import Conversation, Message as DBMessage, File as DBFile

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_database()
    print("✅ Database initialized")

llm_model = LLMModel()
file_service = FileService()
title_service = TitleGenerationService()

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
        

        if (conversation.title == "New Conversation" or conversation.title == "Yeni Sohbet") and len(messages) <= 2:
            try:
                new_title = title_service.update_conversation_title(
                    conversation.id, 
                    request.message, 
                    chat_repo
                )
                if new_title:
                    print(f"✅ Generated title for conversation {conversation.id}: {new_title}")
            except Exception as e:
                print(f"⚠️ Title generation failed: {e}")
        
        return ChatResponse(
            response=llm_response,
            conversation_id=conversation.id,
            message_id=assistant_message.id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...), 
    conversation_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a file with optional conversation association"""
    try:
        file_repo = FileRepository(db)
        
        # Validate file
        is_valid, validation_message = file_service.validate_file(file)
        if not is_valid:
            return FileUploadResponse(
                success=False,
                message=validation_message,
                file=None
            )
        
        # Save file to storage
        file_path, file_hash, file_size = await file_service.save_file(file)
        
        
        # Detect MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file.filename)
        mime_type = mime_type or file.content_type
        
        # Save file metadata to database
        db_file = file_repo.create_file(
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            conversation_id=conversation_id
        )
        
        return FileUploadResponse(
            success=True,
            message="File uploaded successfully",
            file=FileResponseModel(
                id=db_file.id,
                filename=db_file.filename,
                file_size=db_file.file_size,
                mime_type=db_file.mime_type,
                uploaded_at=db_file.uploaded_at.isoformat(),
                conversation_id=db_file.conversation_id
            )
        )
        
    except Exception as e:
        import traceback
        print(f"File upload error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@app.get("/files", response_model=FileListResponse)
async def get_files(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Get all uploaded files"""
    try:
        file_repo = FileRepository(db)
        files = file_repo.get_all_files(skip=skip, limit=limit)
        
        file_list = [
            FileResponseModel(
                id=f.id,
                filename=f.filename,
                file_size=f.file_size,
                mime_type=f.mime_type,
                uploaded_at=f.uploaded_at.isoformat(),
                conversation_id=f.conversation_id
            )
            for f in files
        ]
        
        return FileListResponse(files=file_list)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}", response_model=FileResponseModel)
async def get_file_info(file_id: int, db: Session = Depends(get_db)):
    """Get file information by ID"""
    try:
        file_repo = FileRepository(db)
        file = file_repo.get_file(file_id)
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponseModel(
            id=file.id,
            filename=file.filename,
            file_size=file.file_size,
            mime_type=file.mime_type,
            uploaded_at=file.uploaded_at.isoformat(),
            conversation_id=file.conversation_id
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/download")
async def download_file(file_id: int, db: Session = Depends(get_db)):
    """Download a file"""
    try:
        file_repo = FileRepository(db)
        file = file_repo.get_file(file_id)
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return file response
        return FileResponse(
            path=file.file_path,
            filename=file.filename,
            media_type=file.mime_type
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{file_id}")
async def delete_file(file_id: int, db: Session = Depends(get_db)):
    """Delete a file"""
    try:
        file_repo = FileRepository(db)
        file = file_repo.get_file(file_id)
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete from storage
        storage_deleted = await file_service.delete_file(file.file_path)
        
        # Delete from database
        db_deleted = file_repo.delete_file(file_id)
        
        if not db_deleted:
            raise HTTPException(status_code=500, detail="Failed to delete file from database")
        
        return {
            "status": "success", 
            "message": "File deleted successfully",
            "storage_deleted": storage_deleted
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}/files", response_model=FileListResponse)
async def get_conversation_files(conversation_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Get all files for a specific conversation"""
    try:
        file_repo = FileRepository(db)
        files = file_repo.get_files_by_conversation(conversation_id, skip=skip, limit=limit)
        
        file_list = [
            FileResponseModel(
                id=f.id,
                filename=f.filename,
                file_size=f.file_size,
                mime_type=f.mime_type,
                uploaded_at=f.uploaded_at.isoformat(),
                conversation_id=f.conversation_id
            )
            for f in files
        ]
        
        return FileListResponse(files=file_list)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/supported-file-types")
async def get_supported_file_types():
    """Get list of supported file types"""
    try:
        supported_types = file_service.get_supported_types()
        return {
            "supported_types": supported_types,
            "max_file_size": file_service.MAX_FILE_SIZE,
            "max_file_size_mb": file_service.MAX_FILE_SIZE / (1024 * 1024)
        }
    
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

@app.post("/conversations/{conversation_id}/generate-title")
async def generate_conversation_title(conversation_id: int, db: Session = Depends(get_db)):
    """Generate or regenerate a conversation title based on first message"""
    try:
        chat_repo = ChatRepository(db)
        
        # Get conversation messages
        messages = chat_repo.get_conversation_messages(conversation_id)
        if not messages:
            raise HTTPException(status_code=400, detail="No messages found to generate title from")
        
        # Find first user message
        first_user_message = None
        for msg in messages:
            if msg.role == "user":
                first_user_message = msg.content
                break
        
        if not first_user_message:
            raise HTTPException(status_code=400, detail="No user message found")
        
        # Generate and update title
        new_title = title_service.update_conversation_title(
            conversation_id, 
            first_user_message, 
            chat_repo
        )
        
        if not new_title:
            raise HTTPException(status_code=500, detail="Failed to generate title")
        
        return {
            "status": "success",
            "title": new_title,
            "message": "Title generated successfully"
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/conversations/{conversation_id}/title")
async def update_conversation_title_manual(
    conversation_id: int, 
    title: str, 
    db: Session = Depends(get_db)
):
    """Manually update conversation title"""
    try:
        chat_repo = ChatRepository(db)
        
        # Validate title length
        if len(title.strip()) == 0:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        
        if len(title) > 255:
            raise HTTPException(status_code=400, detail="Title too long (max 255 characters)")
        
        # Update title
        updated_conversation = chat_repo.update_conversation_title(conversation_id, title.strip())
        
        if not updated_conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "status": "success",
            "title": updated_conversation.title,
            "message": "Title updated successfully"
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
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