import os
import json
import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import List, Dict, Any
from backend.src.rag_system.embeddings import EmbeddingManager
from backend.src.rag_system.vector_store import VectorStoreManager
from langchain_core.documents import Document

PARSED_JSONL = os.path.join('data', 'processed', 'parsed_json_data.jsonl')
VECTOR_STORE_DIR = os.path.join('data', 'processed', 'vector_store_json')

from langchain_core.embeddings import Embeddings

class JsonEmbeddingManager(EmbeddingManager, Embeddings):
    """
    Specialized EmbeddingManager for parsed JSON records.
    Implements Langchain Embeddings interface for vectorstore compatibility.
    """
    def __init__(self, model_name: str = 'fast'):
        """Initialize with device detection"""
        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        except:
            device = 'cpu'
        print(f"Using device: {device} for embeddings")
        super().__init__(model_name=model_name)
        
    def extract_text(self, record: Dict[str, Any]) -> str:
        # Customize this method to select which fields to embed
        # Here, join all string values except metadata fields
        return ' '.join(str(v) for k, v in record.items() if isinstance(v, str) and not k.startswith('__'))

    def encode_json_records(self, records: List[Dict[str, Any]]) -> tuple[np.ndarray, List[str]]:
        texts = [self.extract_text(rec) for rec in records]
        return self.encode_documents(texts), texts
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Langchain Embeddings interface: Convert texts to embeddings
        """
        embeddings = self.encode_documents(texts)
        return embeddings.tolist()  # Convert numpy array to list of lists
        
    def embed_query(self, text: str) -> List[float]:
        """
        Langchain Embeddings interface: Convert query to embedding
        """
        embedding = self.encode_query(text)
        return embedding.tolist()  # Convert numpy array to list

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))
    return records

def main():
    # Ensure FAISS CPU is available
    try:
        import faiss
    except ImportError:
        print("Installing FAISS CPU version...")
        import subprocess
        subprocess.check_call(["pip", "install", "faiss-cpu"])
        
    records = load_jsonl(PARSED_JSONL)
    print(f"Loaded {len(records)} JSON records for embedding.")
    emb_mgr = JsonEmbeddingManager(model_name='fast')  # or 'balanced' if you prefer
    embeddings, texts = emb_mgr.encode_json_records(records)
    print(f"Generated {len(embeddings)} embeddings.")
    # Prepare metadata - preserve source file information
    metadatas = []
    for rec in records:
        metadata = {k: v for k, v in rec.items() if k not in ['__source_file__']}
        # Add source file as 'filename' for consistency with extraction logic
        if '__source_file__' in rec:
            metadata['filename'] = rec['__source_file__']
        metadatas.append(metadata)
    
    # Create Document objects for the vector store
    from langchain_core.documents import Document
    documents = [
        Document(page_content=text, metadata=metadata)
        for text, metadata in zip(texts, metadatas)
    ]
    
    # Initialize and create the vector store
    vs = VectorStoreManager(store_path=VECTOR_STORE_DIR)
    vs.create_store(documents, emb_mgr)
    print(f"Saved embeddings to {VECTOR_STORE_DIR}")

if __name__ == "__main__":
    main()
