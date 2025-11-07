from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
import torch
from typing import Iterable
import logging

try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    # Fallback for older LangChain versions
    from langchain.embeddings.base import Embeddings

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
    
    def __init__(self, model_name: str = 'fast'):
        """
        Initialize embedding model with lazy loading
        
        Args:
            model_name: 'fast', 'balanced', or a full repo id
        """
        # Resolve model id: allow either a key (fast/balanced) or a full repo id
        self.model_name = self.MODELS.get(model_name, model_name)
        self.device = 'cpu'  # TODO: Re-enable CUDA after resolving initialization issues
        self._model = None  # Lazy loaded
        self.embedding_dim = None
        
        logging.info(f"Embedding manager initialized (model will load on first use): {self.model_name}")
    
    @property
    def model(self):
        """Lazy load the model only when first accessed"""
        if self._model is None:
            logging.info(f"Loading embedding model: {self.model_name}")
            try:
                # Force offline mode to prevent network calls
                import os
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                
                # Load model from cache
                self._model = SentenceTransformer(self.model_name, device=self.device)
                self.embedding_dim = self._model.get_sentence_embedding_dimension()
                logging.info(f"Loaded embedding model '{self.model_name}' with dim={self.embedding_dim}")
            except Exception as e:
                logging.exception(f"Failed to load embedding model '{self.model_name}': {e}")
                # Re-raise so callers can handle fallback
                raise
        return self._model
    
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


class LangchainEmbeddingAdapter(Embeddings):
    """Adapter to expose embed_documents/embed_query for LangChain-compatible vectorstores.

    This wraps a SentenceTransformer model and provides the methods expected by
    LangChain's embedding interface (embed_documents, embed_query).
    """
    def __init__(self, sentence_transformer: SentenceTransformer):
        self.model = sentence_transformer

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        # sentence-transformers returns numpy arrays
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        emb = self.model.encode([text], convert_to_numpy=True)[0]
        return emb.tolist()