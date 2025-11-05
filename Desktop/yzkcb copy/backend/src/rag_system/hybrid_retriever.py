# src/rag_system/hybrid_retriever.py

from typing import List, Dict
import numpy as np

class HybridRetriever:
    """
    Combine vector search with keyword search and metadata filtering
    """
    
    def __init__(self, vector_store_json, embeddings, bom_index, hierarchy_tree):
        self.vector_store = vector_store_json 
        self.embeddings = embeddings
        self.bom_index = bom_index
        self.hierarchy_tree = hierarchy_tree
    
    def retrieve(
        self,
        query: str,
        k: int = 5,
        search_types: List[str] = None,
        filters: Dict = None
    ) -> List[Dict]:
        """
        Hybrid retrieval combining multiple search strategies
        
        Args:
            query: User query
            k: Number of results
            search_types: List of ['vector', 'keyword', 'bom', 'hierarchy']
            filters: Metadata filters (e.g., {"source": "APQP procedure"})
        """
        
        if search_types is None:
            search_types = ['vector', 'keyword']
        
        all_results = {}
        result_scores = {}
        
        # Strategy 1: Vector Semantic Search
        if 'vector' in search_types:
            from langchain.schema import Document
            query_embedding = self.embeddings.encode_query(query)
            vector_results = self.vector_store.retrieve(query_embedding, k=k)
            
            for i, doc in enumerate(vector_results):
                # Ensure it's a Document object
                if isinstance(doc, dict):
                    doc = Document(
                        page_content=doc.get('page_content', doc.get('content', '')),
                        metadata=doc.get('metadata', {})
                    )
                
                doc_id = hash(doc.page_content) % (10**8)
                result_scores[doc_id] = result_scores.get(doc_id, 0) + (1.0 / (i + 1))
                all_results[doc_id] = doc
        
        # Strategy 2: Keyword Search
        if 'keyword' in search_types:
            keyword_results = self._keyword_search(query, k)
            for i, doc in enumerate(keyword_results):
                doc_id = hash(doc.get('content', '')) % (10**8)
                result_scores[doc_id] = result_scores.get(doc_id, 0) + (0.7 / (i + 1))
                all_results[doc_id] = doc
        
        # Strategy 3: BOM Search
        if 'bom' in search_types:
            bom_results = self._search_bom(query)
            for i, result in enumerate(bom_results[:k]):
                doc_id = hash(result.get('part_number', '')) % (10**8)
                result_scores[doc_id] = result_scores.get(doc_id, 0) + (0.6 / (i + 1))
                all_results[doc_id] = result
        
        # Strategy 4: Hierarchy Search
        if 'hierarchy' in search_types:
            hierarchy_results = self._search_hierarchy(query)
            for i, result in enumerate(hierarchy_results[:k]):
                doc_id = hash(result.get('id', '')) % (10**8)
                result_scores[doc_id] = result_scores.get(doc_id, 0) + (0.6 / (i + 1))
                all_results[doc_id] = result
        
        # Rank by combined score
        ranked_docs = sorted(
            all_results.items(),
            key=lambda x: result_scores.get(x[0], 0),
            reverse=True
        )
        
        return [doc for _, doc in ranked_docs[:k]]
    
    def _keyword_search(self, query: str, k: int) -> List[Dict]:
        """Simple keyword search"""
        keywords = query.lower().split()
        results = []
        
        # Search in vector store metadata
        for doc_id, metadata in self.vector_store.metadata_index.items():
            score = sum(1 for kw in keywords if kw in str(metadata).lower())
            if score > 0:
                results.append((score, metadata))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:k]]
    
    def _search_bom(self, query: str) -> List[Dict]:
        """Search BOM index"""
        from ..document_processor.advanced_csv_handler import AdvancedCSVProcessor
        processor = AdvancedCSVProcessor()
        return processor.search_bom(self.bom_index, query)
    
    def _search_hierarchy(self, query: str) -> List[Dict]:
        """Search hierarchy tree"""
        results = []
        query_lower = query.lower()
        
        for class_id, node in self.hierarchy_tree['all_nodes'].items():
            if (query_lower in node['name'].lower() or 
                query_lower in str(node['requirements']).lower()):
                results.append(node)
        
        return results