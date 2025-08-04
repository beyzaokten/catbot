import chromadb
import uuid
from typing import List, Dict, Any, Optional, Tuple
from chromadb.config import Settings
from dataclasses import dataclass
import logging
import os


@dataclass
class SearchResult:
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    document_id: str


class VectorStore:
    """ChromaDB-based vector storage and retrieval system"""
    
    DEFAULT_COLLECTION_NAME = "rag_documents"
    DEFAULT_DB_PATH = "./data/chroma_db"
    
    def __init__(self, collection_name: str = None, db_path: str = None):
        self.collection_name = collection_name or self.DEFAULT_COLLECTION_NAME
        self.db_path = db_path or self.DEFAULT_DB_PATH
        
        self.client = None
        self.collection = None
        self._is_initialized = False
        
        self.logger = logging.getLogger(__name__)
    
    def initialize(self) -> None:
        """Initialize ChromaDB client and collection"""
        if self._is_initialized:
            return
        
        try:
            os.makedirs(self.db_path, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "RAG document embeddings"}
            )
            
            self._is_initialized = True
            self.logger.info(f"ChromaDB initialized: {self.collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise RuntimeError(f"Could not initialize vector store: {e}")
    
    def add_documents(self, texts: List[str], 
                     embeddings: List[List[float]], 
                     metadatas: List[Dict[str, Any]],
                     document_ids: List[str] = None) -> List[str]:
        """Add documents to vector store"""
        self._ensure_initialized()
        
        if not texts or not embeddings or not metadatas:
            return []
        
        if len(texts) != len(embeddings) or len(texts) != len(metadatas):
            raise ValueError("Texts, embeddings, and metadatas must have same length")
        
        # Generate IDs if not provided
        if document_ids is None:
            document_ids = [str(uuid.uuid4()) for _ in texts]
        
        try:
            processed_metadatas = self._process_metadatas(metadatas)
            
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=processed_metadatas,
                ids=document_ids
            )
            
            self.logger.info(f"Added {len(texts)} documents to vector store")
            return document_ids
            
        except Exception as e:
            self.logger.error(f"Failed to add documents: {e}")
            raise RuntimeError(f"Could not add documents to vector store: {e}")
    
    def search_similar(self, query_embedding: List[float], 
                      n_results: int = 5,
                      metadata_filter: Dict[str, Any] = None) -> List[SearchResult]:
        """Search for similar documents"""
        self._ensure_initialized()
        
        if not query_embedding:
            return []
        
        try:
            where_clause = None
            if metadata_filter:
                where_clause = self._build_where_clause(metadata_filter)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            return self._parse_search_results(results)
            
        except Exception as e:
            self.logger.error(f"Failed to search similar documents: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[SearchResult]:
        """Get specific document by ID"""
        self._ensure_initialized()
        
        try:
            results = self.collection.get(
                ids=[document_id],
                include=["documents", "metadatas"]
            )
            
            if not results['ids']:
                return None
            
            return SearchResult(
                content=results['documents'][0],
                metadata=results['metadatas'][0],
                similarity_score=1.0,  # Exact match
                document_id=document_id
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs"""
        self._ensure_initialized()
        
        try:
            self.collection.delete(ids=document_ids)
            self.logger.info(f"Deleted {len(document_ids)} documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete documents: {e}")
            return False
    
    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> bool:
        """Delete documents by metadata filter"""
        self._ensure_initialized()
        
        try:
            where_clause = self._build_where_clause(metadata_filter)
            self.collection.delete(where=where_clause)
            self.logger.info(f"Deleted documents with filter: {metadata_filter}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete by metadata: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        self._ensure_initialized()
        
        try:
            # Get total chunk count
            total_chunks = self.collection.count()
            
            # Get all unique filenames to count documents
            if total_chunks > 0:
                # Query all records to get unique filenames
                all_results = self.collection.get(
                    include=['metadatas']
                )
                
                # Count unique documents based on filename
                unique_filenames = set()
                if all_results['metadatas']:
                    for metadata in all_results['metadatas']:
                        filename = metadata.get('filename', 'unknown')
                        unique_filenames.add(filename)
                
                document_count = len(unique_filenames)
            else:
                document_count = 0
            
            return {
                'collection_name': self.collection_name,
                'document_count': document_count,
                'total_chunks': total_chunks,
                'db_path': self.db_path
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {e}")
            return {
                'collection_name': self.collection_name,
                'document_count': 0,
                'total_chunks': 0,
                'db_path': self.db_path
            }
    
    def reset_collection(self) -> bool:
        """Reset (clear) the entire collection"""
        self._ensure_initialized()
        
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "RAG document embeddings"}
            )
            self.logger.info(f"Reset collection: {self.collection_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset collection: {e}")
            return False
    
    def _ensure_initialized(self) -> None:
        """Ensure vector store is initialized"""
        if not self._is_initialized:
            self.initialize()
    
    def _process_metadatas(self, metadatas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process metadata for ChromaDB compatibility"""
        processed = []
        
        for metadata in metadatas:
            processed_metadata = {}
            
            for key, value in metadata.items():
                # ChromaDB supports: str, int, float, bool
                if isinstance(value, (str, int, float, bool)):
                    processed_metadata[key] = value
                elif value is None:
                    processed_metadata[key] = ""
                else:
                    # Convert complex types to string
                    processed_metadata[key] = str(value)
            
            processed.append(processed_metadata)
        
        return processed
    
    def _build_where_clause(self, metadata_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Build ChromaDB where clause from metadata filter"""
        return metadata_filter
    
    def _parse_search_results(self, results: Dict[str, Any]) -> List[SearchResult]:
        """Parse ChromaDB search results"""
        search_results = []
        
        if not results['ids'] or not results['ids'][0]:
            return search_results
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        ids = results['ids'][0]
        
        for i, doc_id in enumerate(ids):
            # Convert ChromaDB cosine distance to similarity score
            # ChromaDB cosine distance ranges from 0 to 2, where 0 is perfect match
            similarity_score = max(0.0, 1.0 - (distances[i] / 2.0))
            
            search_result = SearchResult(
                content=documents[i],
                metadata=metadatas[i],
                similarity_score=similarity_score,
                document_id=doc_id
            )
            
            search_results.append(search_result)
        
        return search_results 