from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
import torch
from typing import Iterable
import logging

class EmbeddingManager:
    """
    Handles embeddings for documents
    Using open-source models with GPU acceleration
    """
    
    # Model options ranked by performance vs. speed (all cached locally)
    MODELS = {
        'fast': 'all-MiniLM-L6-v2',           # 22M params, 384 dims - cached ✓
        #'balanced': 'all-mpnet-base-v2',      # 110M params, 768 dims - cached ✓
    }
    
    def __init__(self, model_name: str = 'balanced'):
        """
        Initialize embedding model with GPU support
        
        Args:
            model_name: 'fast', 'balanced', or a full repo id
        """
        # Resolve model id: allow either a key (fast/balanced) or a full repo id
        resolved = self.MODELS.get(model_name, model_name)

        # Determine device (force CPU for stability)
        device = 'cpu'  # TODO: Re-enable CUDA after resolving initialization issues
        logging.info(f"Using device: {device} for embeddings")

        try:
            logging.info(f"Loading sentence-transformers model: {resolved}")
            # Force offline mode to prevent network calls
            import os
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            
            # Load model from cache
            self.model = SentenceTransformer(resolved, device=device)
            self.model_name = resolved
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            self.device = device
            logging.info(f"Loaded embedding model '{self.model_name}' with dim={self.embedding_dim}")
        except Exception as e:
            logging.exception(f"Failed to load embedding model '{resolved}': {e}")
            # Re-raise so callers (initialize_system) can decide how to handle fallback
            raise
    
    def encode_documents(self, documents: List[str]) -> np.ndarray:
        """
        Encode list of documents to embeddings
        
        Returns:
            numpy array of shape (num_docs, embedding_dim)
        """
        embeddings = self.model.encode(
            documents,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings
    
    def encode_query(self, query: str) -> np.ndarray:
        """Single query encoding"""
        return self.model.encode([query], convert_to_numpy=True)[0]
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        from sklearn.metrics.pairwise import cosine_similarity
        return cosine_similarity([embedding1], [embedding2])[0][0]


class LangchainEmbeddingAdapter:
    """Adapter to expose embed_documents/embed_query for LangChain-compatible vectorstores.

    This wraps a SentenceTransformer model and provides the methods expected by
    LangChain's embedding interface (embed_documents, embed_query).
    """
    def __init__(self, sentence_transformer: SentenceTransformer):
        self.model = sentence_transformer

    def embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
        # sentence-transformers returns numpy arrays
        embeddings = self.model.encode(
            list(texts),
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        emb = self.model.encode([text], convert_to_numpy=True)[0]
        return emb.tolist()
    
    def encode_documents(self, documents: List[str]) -> np.ndarray:
        """
        Encode list of documents to embeddings
        
        Returns:
            numpy array of shape (num_docs, embedding_dim)
        """
        # Batch encoding for efficiency
        embeddings = self.model.encode(
            documents,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings
    
    def encode_query(self, query: str) -> np.ndarray:
        """Single query encoding"""
        return self.model.encode([query], convert_to_numpy=True)[0]
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        from sklearn.metrics.pairwise import cosine_similarity
        return cosine_similarity([embedding1], [embedding2])[0][0]