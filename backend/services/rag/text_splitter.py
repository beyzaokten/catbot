from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    start_char: int
    end_char: int


class TextSplitter:
    """Intelligent text splitting with context preservation"""
    
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_OVERLAP = 200
    
    ENGLISH_SEPARATORS = [
        "\n\n",  
        "\n",    
        ". ",    
        "! ",    
        "? ",    
        "; ",   
        ": ",    
        ", ",    
        " ",    
        ""       
    ]
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or self.DEFAULT_OVERLAP
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.ENGLISH_SEPARATORS,
            length_function=len,
            is_separator_regex=False
        )
    
    def split_text(self, text: str, metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """Split text into semantically coherent chunks"""
        if not text or not text.strip():
            return []
        
        metadata = metadata or {}
        chunks = self.splitter.split_text(text)
        
        return self._create_text_chunks(chunks, text, metadata)
    
    def split_documents(self, documents: List[Dict[str, Any]]) -> List[TextChunk]:
        """Split multiple documents into chunks"""
        all_chunks = []
        
        for doc in documents:
            text = doc.get('content', '')
            doc_metadata = doc.get('metadata', {})
            
            chunks = self.split_text(text, doc_metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def _create_text_chunks(self, chunks: List[str], original_text: str, 
                           metadata: Dict[str, Any]) -> List[TextChunk]:
        """Create TextChunk objects with position tracking"""
        text_chunks = []
        current_position = 0
        
        for i, chunk_content in enumerate(chunks):
            # Find chunk position in original text
            start_pos = original_text.find(chunk_content, current_position)
            if start_pos == -1:
                # Fallback if exact match not found
                start_pos = current_position
            
            end_pos = start_pos + len(chunk_content)
            
            # Create chunk metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_size': len(chunk_content),
                'word_count': len(chunk_content.split()),
                'sentence_count': self._count_sentences(chunk_content),
                'original_document': metadata.get('filename', 'unknown')
            })
            
            text_chunk = TextChunk(
                content=chunk_content.strip(),
                metadata=chunk_metadata,
                chunk_index=i,
                start_char=start_pos,
                end_char=end_pos
            )
            
            text_chunks.append(text_chunk)
            current_position = start_pos + len(chunk_content)
        
        return text_chunks
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text using English punctuation"""
        sentence_endings = ['.', '!', '?']
        count = 0
        
        for char in text:
            if char in sentence_endings:
                count += 1
        
        return max(1, count)  # Minimum 1 sentence
    
    def get_chunk_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Calculate statistics for chunks"""
        if not chunks:
            return {}
        
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        word_counts = [chunk.metadata.get('word_count', 0) for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'avg_word_count': sum(word_counts) / len(word_counts),
            'total_characters': sum(chunk_sizes)
        } 