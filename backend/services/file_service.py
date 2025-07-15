import os
import hashlib
import mimetypes
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, List
from fastapi import UploadFile, HTTPException

class FileService:
    """Service for handling file upload, storage and management"""
    
    SUPPORTED_MIME_TYPES = {
        'application/pdf': ['.pdf'],
        'text/plain': ['.txt'],
        'text/markdown': ['.md'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'application/msword': ['.doc'],
        'text/html': ['.html'],
        'application/rtf': ['.rtf'],
        'text/csv': ['.csv'],
        'application/json': ['.json'],
        'application/xml': ['.xml'],
        'text/xml': ['.xml']
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
    UPLOAD_DIR = Path("uploads/files")
    
    def __init__(self):
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self):
        """Create upload directory structure if it doesn't exist"""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    async def calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA256 hash of file content for integrity and duplicate detection"""
        hash_sha256 = hashlib.sha256()
        hash_sha256.update(file_content)
        return hash_sha256.hexdigest()
    
    def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """Validate file type and size"""
        
        # Check file size
        if hasattr(file, 'size') and file.size and file.size > self.MAX_FILE_SIZE:
            return False, f"File size ({file.size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({self.MAX_FILE_SIZE / 1024 / 1024}MB)"
        
        # Get file extension and mime type
        file_extension = Path(file.filename).suffix.lower()
        detected_mime_type, _ = mimetypes.guess_type(file.filename)
        
        # Use content type from upload if mime detection fails
        mime_type = detected_mime_type or file.content_type
        
        # Check if mime type is supported
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            supported_types = list(self.SUPPORTED_MIME_TYPES.keys())
            return False, f"File type '{mime_type}' not supported. Supported types: {supported_types}"
        
        # Verify extension matches mime type
        expected_extensions = self.SUPPORTED_MIME_TYPES[mime_type]
        if file_extension not in expected_extensions:
            return False, f"File extension '{file_extension}' doesn't match content type '{mime_type}'"
        
        return True, "File validation successful"
    
    def generate_storage_path(self, filename: str, file_hash: str) -> Path:
        """Generate organized storage path based on date and hash"""
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        # Create subdirectory structure
        storage_dir = self.UPLOAD_DIR / year / month
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Use hash prefix + original filename for uniqueness
        file_extension = Path(filename).suffix
        safe_filename = f"{file_hash[:8]}_{filename}"
        
        return storage_dir / safe_filename
    
    async def save_file(self, file: UploadFile) -> Tuple[str, str, int]:
        """Save uploaded file and return (file_path, file_hash, file_size)"""
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size after reading
        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({self.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )
        
        # Calculate file hash
        file_hash = await self.calculate_file_hash(content)
        
        # Generate storage path
        storage_path = self.generate_storage_path(file.filename, file_hash)
        
        # Save file asynchronously
        async with aiofiles.open(storage_path, 'wb') as f:
            await f.write(content)
        
        return str(storage_path), file_hash, file_size
    
    async def read_file(self, file_path: str) -> bytes:
        """Read file content from storage"""
        path = Path(file_path)
        
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        path = Path(file_path)
        
        if not path.exists():
            return False
        
        try:
            path.unlink()  
            
            parent = path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                grandparent = parent.parent
                if grandparent.exists() and not any(grandparent.iterdir()):
                    grandparent.rmdir()
            
            return True
        except Exception:
            return False
    
    def get_supported_types(self) -> List[str]:
        """Return list of supported file types"""
        return list(self.SUPPORTED_MIME_TYPES.keys())
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB" 