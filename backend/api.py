from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
import uvicorn
from typing import Optional, List
from sqlalchemy.orm import Session
from .models.chat import Message, ChatRequest, ChatResponse, ModelsResponse, FileResponse as FileResponseModel, FileUploadResponse, FileListResponse
from .services.llm_service import LLMModel
from .services.file_service import FileService
from .services.title_service import TitleGenerationService
from .services.rag.rag_pipeline import RAGPipeline
from .database.database import get_db, init_database
from .repositories.chat_repository import ChatRepository
from .repositories.file_repository import FileRepository
from .database.models import Conversation, Message as DBMessage, File as DBFile
import os
from datetime import datetime
from pathlib import Path

app = FastAPI()

# Initialize services and models
llm_model = LLMModel()
file_service = FileService()
title_service = TitleGenerationService()
rag_pipeline = RAGPipeline()

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "CatBot API"}

@app.on_event("startup")
async def startup_event():
    init_database()
    print("✅ Database initialized")
    
    # Initialize RAG pipeline
    try:
        rag_pipeline.initialize()
        print("✅ RAG pipeline initialized")
    except Exception as e:
        print(f"⚠️ RAG pipeline initialization failed: {e}")
        print("📄 File processing will work without RAG features")

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
        
        enhanced_message = request.message
        
        try:
            if rag_pipeline:
                context_results = rag_pipeline.query_documents(
                    query=request.message,
                    top_k=5,
                    similarity_threshold=0.35
                )
                
                if context_results:
                    context_parts = []
                    for result in context_results:
                        source = result.metadata.get('filename', 'Unknown source')
                        content = result.content.strip()
                        
                        if len(content) > 500:
                            content = content[:500] + "..."
                        context_parts.append(f"[Source: {source}]\n{content}")
                    
                    if context_parts:
                        context_text = "\n\n---\n\n".join(context_parts)
                        enhanced_message = f"""Based on the following relevant information from uploaded documents, please answer the user's question:

RELEVANT CONTEXT:
{context_text}

USER QUESTION: {request.message}

Please provide a comprehensive answer using the context above. If the context is relevant, reference the sources. If the context doesn't help answer the question, just answer normally."""
                
        except Exception:
            pass
        
        llm_response = llm_model.get_response(enhanced_message)
        
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

# RAG-related endpoints
@app.post("/files/{file_id}/process")
async def process_file_with_rag(file_id: int, db: Session = Depends(get_db)):
    """Process uploaded file through RAG pipeline"""
    try:
        file_repo = FileRepository(db)
        file = file_repo.get_file(file_id)
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Process file through RAG pipeline
        file_path = os.path.abspath(file.file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ File not found at path: {file_path}")
            print(f"🔍 Original file path: {file.file_path}")
            print(f"🔍 Current working directory: {os.getcwd()}")
            return {
                "status": "error",
                "message": f"File not found at path: {file_path}",
                "file_id": file_id
            }
        

        result = rag_pipeline.process_document(file_path)
        
        if result['success']:
            return {
                "status": "success",
                "message": f"File processed successfully: {result['chunks_added']} chunks added",
                "file_id": file_id,
                "filename": file.filename,
                "chunks_added": result['chunks_added'],
                "total_characters": result['total_characters'],
                "file_type": result['file_type']
            }
        else:
            return {
                "status": "error",
                "message": f"Processing failed: {result['error']}",
                "file_id": file_id,
                "filename": file.filename
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

@app.get("/search/context")
async def search_context(query: str, top_k: int = 5, threshold: float = 0.0):
    """Search for relevant context from processed documents"""
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Search for relevant chunks
        search_results = rag_pipeline.query_documents(
            query=query.strip(),
            top_k=top_k,
            similarity_threshold=threshold
        )
        
        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "content": result.content,
                "similarity_score": result.similarity_score,
                "source": result.metadata.get('filename', 'Unknown'),
                "chunk_index": result.metadata.get('chunk_index', 0),
                "file_type": result.metadata.get('file_extension', 'unknown')
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context search failed: {str(e)}")

@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG pipeline statistics"""
    try:
        stats = rag_pipeline.get_pipeline_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get RAG stats: {str(e)}")

@app.get("/rag/test/{query}")
async def test_rag_query(query: str):
    """Test RAG query for debugging"""
    try:
        context_results = rag_pipeline.query_documents(
            query=query,
            top_k=5,
            similarity_threshold=0.1
        )
        
        formatted_results = []
        for result in context_results:
            formatted_results.append({
                "content": result.content[:200] + "...",
                "similarity_score": result.similarity_score,
                "source": result.metadata.get('filename', 'Unknown'),
                "chunk_index": result.metadata.get('chunk_index', 0)
            })
        
        return {
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG test failed: {str(e)}")

@app.get("/debug/pdf/{file_id}")
async def debug_pdf_processing(file_id: int, db: Session = Depends(get_db)):
    """Debug PDF processing step by step"""
    try:
        file_repo = FileRepository(db)
        file = file_repo.get_file(file_id)
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        print(f"🔍 Debug PDF Processing for file ID: {file_id}")
        print(f"📋 Database record:")
        print(f"  - filename: {file.filename}")
        print(f"  - file_path: {file.file_path}")
        print(f"  - file_size: {file.file_size}")
        print(f"  - mime_type: {file.mime_type}")
        
        # Check file path resolution
        file_path = os.path.abspath(file.file_path)
        print(f"📁 Absolute path: {file_path}")
        print(f"📂 Working directory: {os.getcwd()}")
        print(f"✅ File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            print(f"📊 File info:")
            file_stat = os.stat(file_path)
            print(f"  - Size: {file_stat.st_size} bytes")
            print(f"  - Modified: {file_stat.st_mtime}")
            
            # Test PyMuPDF directly
            try:
                import fitz
                print(f"🔍 Testing PyMuPDF directly...")
                pdf_doc = fitz.open(file_path)
                print(f"✅ PyMuPDF opened successfully: {len(pdf_doc)} pages")
                
                if len(pdf_doc) > 0:
                    page = pdf_doc.load_page(0)
                    text = page.get_text()
                    print(f"📄 First page text length: {len(text)}")
                    print(f"📄 First 200 chars: {text[:200]}")
                
                pdf_doc.close()
                
            except Exception as e:
                print(f"❌ PyMuPDF failed: {e}")
                import traceback
                print(f"📍 Traceback: {traceback.format_exc()}")
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": file.file_path,
            "absolute_path": file_path,
            "exists": os.path.exists(file_path),
            "working_dir": os.getcwd()
        }
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        print(f"📍 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/rag/clear")
async def clear_rag_database():
    """Clear all documents from RAG database (for testing)"""
    try:
        stats_before = rag_pipeline.get_pipeline_stats()
        print(f"🗑️ Clearing RAG database...")
        print(f"📊 Before: {stats_before}")
        
        # Clear the vector store
        rag_pipeline.vector_store.reset_collection()
        
        stats_after = rag_pipeline.get_pipeline_stats()
        print(f"📊 After: {stats_after}")
        
        return {
            "status": "success",
            "message": "RAG database cleared successfully",
            "before": stats_before,
            "after": stats_after
        }
    except Exception as e:
        print(f"❌ Failed to clear RAG database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear RAG database: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

def start_server(host="127.0.0.1", port=8000):
    uvicorn.run(app, host=host, port=port) 