from typing import List, Dict, Any, Optional, Tuple
import logging
import os
from pathlib import Path

from .document_processor import DocumentProcessor, DocumentContent
from .text_splitter import TextSplitter, TextChunk
from .embedding_service import EmbeddingService
from .vector_store import VectorStore, SearchResult


class RAGPipeline:
    """Main RAG pipeline orchestrator"""
    
    def __init__(self, 
                 collection_name: str = "rag_documents",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 embedding_model: str = None,
                 db_path: str = None):
        
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize components
        self.document_processor = DocumentProcessor()
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)
        self.embedding_service = EmbeddingService(model_name=embedding_model)
        self.vector_store = VectorStore(collection_name, db_path)
        
        self.logger = logging.getLogger(__name__)
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """Initialize all RAG components"""
        try:
            self.logger.info("Initializing RAG pipeline...")
            
            # Initialize vector store
            self.vector_store.initialize()
            
            # Load embedding model
            self.embedding_service.load_model()
            
            self._is_initialized = True
            self.logger.info("RAG pipeline initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize RAG pipeline: {e}")
            return False
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process single document through complete RAG pipeline"""
        self._ensure_initialized()
        
        try:
            doc_content = self.document_processor.process_document(file_path)
            
            chunks = self.text_splitter.split_text(
                doc_content.text, 
                doc_content.metadata
            )
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'No chunks generated from document',
                    'document_id': None,
                    'chunks_added': 0
                }
            
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.generate_embeddings(chunk_texts)
            
            chunk_metadatas = []
            for chunk in chunks:
                metadata = chunk.metadata.copy()
                metadata.update({
                    'chunk_index': chunk.chunk_index,
                    'start_char': chunk.start_char,
                    'end_char': chunk.end_char,
                    'embedding_model': self.embedding_service.model_name
                })
                chunk_metadatas.append(metadata)
            
            document_ids = self.vector_store.add_documents(
                texts=chunk_texts,
                embeddings=embeddings,
                metadatas=chunk_metadatas
            )
            
            return {
                'success': True,
                'document_id': doc_content.metadata.get('filename', 'unknown'),
                'chunks_added': len(chunks),
                'total_characters': len(doc_content.text),
                'file_type': doc_content.file_type,
                'chunk_stats': self.text_splitter.get_chunk_stats(chunks),
                'embedding_dimension': self.embedding_service.EMBEDDING_DIMENSION
            }
            
        except Exception as e:
            print(f"❌ RAG Pipeline: Failed to process document {file_path}")
            print(f"📍 Error: {str(e)}")
            import traceback
            print(f"📍 Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'document_id': None,
                'chunks_added': 0,
                'total_characters': 0,
                'file_type': 'unknown'
            }
    
    def process_multiple_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple documents"""
        self._ensure_initialized()
        
        results = {
            'total_documents': len(file_paths),
            'successful': 0,
            'failed': 0,
            'total_chunks': 0,
            'errors': [],
            'processed_files': []
        }
        
        for file_path in file_paths:
            result = self.process_document(file_path)
            
            if result['success']:
                results['successful'] += 1
                results['total_chunks'] += result['chunks_added']
                results['processed_files'].append({
                    'file': file_path,
                    'chunks': result['chunks_added'],
                    'file_type': result.get('file_type', 'unknown')
                })
            else:
                results['failed'] += 1
                results['errors'].append({
                    'file': file_path,
                    'error': result['error']
                })
        
        self.logger.info(f"Batch processing completed: {results['successful']}/{results['total_documents']} successful")
        return results
    
    def query_documents(self, query: str, 
                       top_k: int = 5,
                       metadata_filter: Dict[str, Any] = None,
                       similarity_threshold: float = 0.0) -> List[SearchResult]:
        """Query documents using semantic search"""
        self._ensure_initialized()
        
        if not query or not query.strip():
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search similar documents
            results = self.vector_store.search_similar(
                query_embedding=query_embedding,
                n_results=top_k,
                metadata_filter=metadata_filter
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results 
                if result.similarity_score >= similarity_threshold
            ]
            
            self.logger.info(f"Query returned {len(filtered_results)} results above threshold {similarity_threshold}")
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Failed to query documents: {e}")
            return []
    
    def generate_context(self, query: str, 
                        max_context_length: int = 2000,
                        top_k: int = 5) -> str:
        """Generate context for RAG-enhanced responses"""
        search_results = self.query_documents(query, top_k)
        
        if not search_results:
            return ""
        
        # Build context from search results
        context_parts = []
        current_length = 0
        
        for result in search_results:
            content = result.content.strip()
            
            # Add source information
            source = result.metadata.get('filename', 'Unknown source')
            formatted_content = f"[Source: {source}]\n{content}\n"
            
            # Check if adding this would exceed max length
            if current_length + len(formatted_content) > max_context_length:
                # Try to add partial content
                remaining_space = max_context_length - current_length
                if remaining_space > 100:  # Only add if meaningful space left
                    truncated = formatted_content[:remaining_space-3] + "..."
                    context_parts.append(truncated)
                break
            
            context_parts.append(formatted_content)
            current_length += len(formatted_content)
        
        return "\n---\n".join(context_parts)
    
    def delete_document(self, filename: str) -> bool:
        """Delete all chunks of a specific document"""
        self._ensure_initialized()
        
        try:
            success = self.vector_store.delete_by_metadata(
                metadata_filter={'filename': filename}
            )
            
            if success:
                self.logger.info(f"Deleted document: {filename}")
            else:
                self.logger.warning(f"Failed to delete document: {filename}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting document {filename}: {e}")
            return False
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        self._ensure_initialized()
        
        try:
            vector_stats = self.vector_store.get_collection_stats()
            embedding_info = self.embedding_service.get_model_info()
            
            return {
                'is_initialized': self._is_initialized,
                'collection_name': self.collection_name,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap,
                'vector_store': vector_stats,
                'embedding_service': embedding_info,
                'supported_formats': list(self.document_processor.SUPPORTED_FORMATS.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get pipeline stats: {e}")
            return {'error': str(e)}
    
    def reset_pipeline(self) -> bool:
        """Reset entire pipeline (clear all documents)"""
        self._ensure_initialized()
        
        try:
            success = self.vector_store.reset_collection()
            if success:
                self.logger.info("Pipeline reset successfully")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to reset pipeline: {e}")
            return False
    
    def _ensure_initialized(self) -> None:
        """Ensure pipeline is initialized"""
        if not self._is_initialized:
            if not self.initialize():
                raise RuntimeError("RAG pipeline not initialized") 