from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from .base import BaseRepository
from ..database.models import File, Conversation

class FileRepository:
    def __init__(self, db: Session):
        self.db = db
        self.file_repo = BaseRepository(File, db)
    
    def create_file(self, filename: str, file_path: str, file_size: int, 
                   mime_type: str, file_hash: str, conversation_id: Optional[int] = None) -> File:
        """Create a new file record"""
        return self.file_repo.create(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            conversation_id=conversation_id
        )
    
    def get_file(self, file_id: int) -> Optional[File]:
        """Get a file by ID"""
        return self.file_repo.get(file_id)
    
    def get_file_by_hash(self, file_hash: str) -> Optional[File]:
        """Get file by hash (for duplicate detection)"""
        return self.db.query(File).filter(File.file_hash == file_hash).first()
    
    def get_files_by_conversation(self, conversation_id: int, skip: int = 0, limit: int = 50) -> List[File]:
        """Get all files for a specific conversation"""
        return (self.db.query(File)
                .filter(File.conversation_id == conversation_id)
                .order_by(desc(File.uploaded_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_files_by_mime_type(self, mime_type: str, skip: int = 0, limit: int = 50) -> List[File]:
        """Get files filtered by mime type"""
        return (self.db.query(File)
                .filter(File.mime_type == mime_type)
                .order_by(desc(File.uploaded_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_all_files(self, skip: int = 0, limit: int = 50) -> List[File]:
        """Get all files ordered by upload date"""
        return (self.db.query(File)
                .order_by(desc(File.uploaded_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def search_files(self, search_term: str, conversation_id: Optional[int] = None, 
                    limit: int = 20) -> List[File]:
        """Search files by filename"""
        query = self.db.query(File).filter(File.filename.contains(search_term))
        
        if conversation_id:
            query = query.filter(File.conversation_id == conversation_id)
        
        return (query.order_by(desc(File.uploaded_at))
                .limit(limit)
                .all())
    
    def update_file_conversation(self, file_id: int, conversation_id: Optional[int]) -> Optional[File]:
        """Update file's conversation association"""
        return self.file_repo.update(file_id, conversation_id=conversation_id)
    
    def delete_file(self, file_id: int) -> bool:
        """Delete a file record"""
        return self.file_repo.delete(file_id)
    
    def get_conversation_file_count(self, conversation_id: int) -> int:
        """Get count of files in a conversation"""
        return self.db.query(File).filter(File.conversation_id == conversation_id).count()
    
    def get_total_file_size_by_conversation(self, conversation_id: int) -> int:
        """Get total file size for a conversation"""
        result = (self.db.query(self.db.func.sum(File.file_size))
                 .filter(File.conversation_id == conversation_id)
                 .scalar())
        return result or 0
    
    def get_files_by_size_range(self, min_size: int, max_size: int, 
                               skip: int = 0, limit: int = 50) -> List[File]:
        """Get files within size range"""
        return (self.db.query(File)
                .filter(and_(File.file_size >= min_size, File.file_size <= max_size))
                .order_by(desc(File.uploaded_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_recent_files(self, limit: int = 10) -> List[File]:
        """Get most recently uploaded files"""
        return (self.db.query(File)
                .order_by(desc(File.uploaded_at))
                .limit(limit)
                .all())
    
    def check_duplicate_exists(self, file_hash: str, conversation_id: Optional[int] = None) -> bool:
        """Check if a duplicate file exists (optionally within conversation)"""
        query = self.db.query(File).filter(File.file_hash == file_hash)
        
        if conversation_id:
            query = query.filter(File.conversation_id == conversation_id)
        
        return query.first() is not None 