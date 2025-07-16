import os
import magic
from pathlib import Path
from typing import Dict, Any, Tuple
from docx import Document
import PyPDF2
from dataclasses import dataclass


@dataclass
class DocumentContent:
    text: str
    metadata: Dict[str, Any]
    file_type: str


class DocumentProcessor:
    """Processes various document formats and extracts text with metadata"""
    
    SUPPORTED_FORMATS = {
        'application/pdf': '_process_pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '_process_docx',
        'text/plain': '_process_txt'
    }
    
    def __init__(self):
        self.magic_instance = magic.Magic(mime=True)
    
    def process_document(self, file_path: str) -> DocumentContent:
        """Process document and extract text with metadata"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_type = self._detect_file_type(file_path)
        
        if file_type not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        processor_method = getattr(self, self.SUPPORTED_FORMATS[file_type])
        text, metadata = processor_method(file_path)
        
        base_metadata = self._extract_base_metadata(file_path)
        metadata.update(base_metadata)
        
        return DocumentContent(
            text=text,
            metadata=metadata,
            file_type=file_type
        )
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file MIME type using python-magic"""
        try:
            return self.magic_instance.from_file(file_path)
        except Exception:
            # Fallback to extension-based detection
            extension = Path(file_path).suffix.lower()
            extension_map = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.txt': 'text/plain'
            }
            return extension_map.get(extension, 'unknown')
    
    def _process_pdf(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF files"""
        text_content = []
        metadata = {'pages': 0}
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata['pages'] = len(pdf_reader.pages)
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text_content.append(page_text)
            
            # Extract PDF metadata
            if pdf_reader.metadata:
                pdf_meta = pdf_reader.metadata
                metadata.update({
                    'title': pdf_meta.get('/Title', ''),
                    'author': pdf_meta.get('/Author', ''),
                    'subject': pdf_meta.get('/Subject', ''),
                    'creator': pdf_meta.get('/Creator', '')
                })
        
        return '\n\n'.join(text_content), metadata
    
    def _process_docx(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from DOCX files"""
        doc = Document(file_path)
        
        text_content = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)
        
        metadata = {
            'paragraphs': len(doc.paragraphs),
            'title': doc.core_properties.title or '',
            'author': doc.core_properties.author or '',
            'subject': doc.core_properties.subject or '',
            'keywords': doc.core_properties.keywords or ''
        }
        
        return '\n\n'.join(text_content), metadata
    
    def _process_txt(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from plain text files"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        metadata = {
            'lines': len(content.splitlines()),
            'characters': len(content)
        }
        
        return content, metadata
    
    def _extract_base_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract basic file metadata"""
        path_obj = Path(file_path)
        stat = path_obj.stat()
        
        return {
            'filename': path_obj.name,
            'file_size': stat.st_size,
            'created_at': stat.st_ctime,
            'modified_at': stat.st_mtime,
            'file_extension': path_obj.suffix.lower()
        } 