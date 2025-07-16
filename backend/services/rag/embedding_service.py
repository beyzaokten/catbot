import numpy as np
from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer
import logging


class EmbeddingService:
    """English-optimized embedding generation service"""
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384
    
    def __init__(self, model_name: str = None, device: str = "cpu"):
        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self.model = None
        self._is_loaded = False
        
        self.logger = logging.getLogger(__name__)
    
    def load_model(self) -> None:
        """Load the embedding model"""
        if self._is_loaded:
            return
        
        try:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self._is_loaded = True
            self.logger.info("Embedding model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Could not load embedding model: {e}")
    
    def generate_embedding(self, text: str, normalize: bool = True) -> List[float]:
        """Generate embedding for single text"""
        if not text or not text.strip():
            return [0.0] * self.EMBEDDING_DIMENSION
        
        embeddings = self.generate_embeddings([text], normalize=normalize)
        return embeddings[0]
    
    def generate_embeddings(self, texts: List[str], 
                          normalize: bool = True,
                          batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []
        
        self._ensure_model_loaded()
        
        # Filter empty texts
        non_empty_texts = [text.strip() for text in texts if text and text.strip()]
        if not non_empty_texts:
            return [[0.0] * self.EMBEDDING_DIMENSION] * len(texts)
        
        try:
            # Generate embeddings in batches
            all_embeddings = []
            
            for i in range(0, len(non_empty_texts), batch_size):
                batch = non_empty_texts[i:i + batch_size]
                
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    normalize_embeddings=normalize,
                    show_progress_bar=len(non_empty_texts) > 100
                )
                
                all_embeddings.extend(batch_embeddings.tolist())
            
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.EMBEDDING_DIMENSION] * len(texts)
    
    def compute_similarity(self, embedding1: List[float], 
                          embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings"""
        if not embedding1 or not embedding2:
            return 0.0
        
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Handle zero vectors
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    def find_most_similar(self, query_embedding: List[float], 
                         candidate_embeddings: List[List[float]],
                         top_k: int = 5) -> List[tuple]:
        """Find most similar embeddings to query"""
        if not query_embedding or not candidate_embeddings:
            return []
        
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.compute_similarity(query_embedding, candidate)
            similarities.append((i, similarity))
        
        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.EMBEDDING_DIMENSION,
            'device': self.device,
            'is_loaded': self._is_loaded,
            'model_max_length': getattr(self.model, 'max_seq_length', 'unknown') if self.model else 'unknown'
        }
    
    def _ensure_model_loaded(self) -> None:
        """Ensure model is loaded before operations"""
        if not self._is_loaded:
            self.load_model()
    
    def cleanup(self) -> None:
        """Clean up model resources"""
        if self.model is not None:
            del self.model
            self.model = None
            self._is_loaded = False
            self.logger.info("Embedding model cleaned up") 