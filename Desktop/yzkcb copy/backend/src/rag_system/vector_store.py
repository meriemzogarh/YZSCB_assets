# src/rag_system/vector_store.py

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from pathlib import Path
import json

class VectorStoreManager:
    """
    Manages FAISS vector store for document retrieval
    """
    
    def __init__(self, store_path: str = "data/processed/vector_store_json"):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.vector_store = None
        self.metadata_index = {}
    
    def create_store(self, documents: list, embeddings):
        """
        Create FAISS vector store from documents
        
        Args:
            documents: List of Document objects
            embeddings: EmbeddingManager instance
        """
        from langchain_community.vectorstores import FAISS
        from .embeddings import LangchainEmbeddingAdapter
        
        # Create proper Embeddings object for LangChain compatibility
        embeddings_adapter = LangchainEmbeddingAdapter(embeddings.model)
        
        # Create FAISS store
        self.vector_store = FAISS.from_documents(
            documents,
            embeddings_adapter  # Use the LangChain-compatible adapter
        )
        
        # Save to disk
        self.vector_store.save_local(str(self.store_path / "faiss_index"))
        
        # Build metadata index for faster queries
        for doc in documents:
            doc_id = hash(doc.page_content) % (10 ** 8)
            self.metadata_index[doc_id] = doc.metadata
        
        # Save metadata
        with open(self.store_path / "metadata.json", 'w') as f:
            json.dump(self.metadata_index, f, indent=2)
    
    def load_store(self, embeddings):
        """Load previously saved FAISS store"""
        from langchain_community.vectorstores import FAISS
        from .embeddings import LangchainEmbeddingAdapter
        
        # Create proper Embeddings object for LangChain compatibility
        embeddings_adapter = LangchainEmbeddingAdapter(embeddings.model)
        
        self.vector_store = FAISS.load_local(
            str(self.store_path / "faiss_index"),
            embeddings_adapter,
            allow_dangerous_deserialization=True
        )
        
        with open(self.store_path / "metadata.json", 'r') as f:
            self.metadata_index = json.load(f)
    
    def retrieve(self, query_embedding, k: int = 3) -> list:
        """
        Retrieve top-k most similar documents
        """
        # Using similarity search with threshold
        results = self.vector_store.similarity_search_by_vector(
            query_embedding,
            k=k
        )
        return results
    
    def add_documents(self, documents: list, embeddings):
        """Add new documents to existing store"""
        if self.vector_store is None:
            self.create_store(documents, embeddings)
        else:
            self.vector_store.add_documents(documents)
            self.vector_store.save_local(str(self.store_path / "faiss_index"))