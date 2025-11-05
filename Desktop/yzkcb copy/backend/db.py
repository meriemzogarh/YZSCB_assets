"""
Database initialization and management for the Yazaki Chatbot backend.

Handles:
- MongoDB connection and initialization
- Vector store setup and loading  
- Database health checks
- Index creation for optimal performance
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Add parent directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages MongoDB and vector store connections for the chatbot."""
    
    def __init__(self, mongo_uri: str = None, db_name: str = None):
        """
        Initialize database manager.
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: MongoDB database name
        """
        self.mongo_uri = mongo_uri or os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.db_name = db_name or os.getenv('MONGODB_DB', 'yazaki_chatbot')
        
        self.mongo_client: Optional[MongoClient] = None
        self.mongo_db = None
        self.conversations_collection = None
        self.sessions_collection = None
        self.is_connected = False
        
        # Vector store components
        self.vector_store = None
        self.retriever = None
        self.embeddings = None
        self.llm_manager = None
        
    def connect_mongodb(self) -> bool:
        """
        Establish MongoDB connection and create necessary collections.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MongoDB at {self.mongo_uri}")
            
            # Create client with timeout
            self.mongo_client = MongoClient(
                self.mongo_uri, 
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            self.mongo_client.admin.command('ping')
            self.mongo_db = self.mongo_client[self.db_name]
            
            # Setup collections
            self.conversations_collection = self.mongo_db['conversations']
            self.sessions_collection = self.mongo_db['sessions']
            
            # Create indexes for performance
            self._create_indexes()
            
            self.is_connected = True
            logger.info(f"✅ MongoDB connected successfully to {self.db_name}")
            logger.info(f"   Active Collections: conversations, sessions")
            
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"⚠️ MongoDB connection failed: {e}")
            logger.warning("Database operations will be disabled")
            self.is_connected = False
            return False
            
        except Exception as e:
            logger.error(f"❌ MongoDB initialization error: {e}")
            self.is_connected = False
            return False
    
    def _create_indexes(self):
        """Create database indexes for optimal query performance."""
        try:
            # Conversations collection indexes
            self.conversations_collection.create_index([("session_id", 1)])
            self.conversations_collection.create_index([("timestamp", -1)])
            
            # Sessions collection indexes
            self.sessions_collection.create_index([("session_id", 1)], unique=True)
            self.sessions_collection.create_index([("last_active", -1)])
            self.sessions_collection.create_index([("created_at", -1)])
            
            logger.debug("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database indexes: {e}")
    
    def initialize_vector_store(self, vector_store_name: str = 'vector_store_json') -> bool:
        """
        Initialize vector store and retrieval components.
        
        Args:
            vector_store_name: Name of the vector store to use
            
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info(f"Initializing vector store: {vector_store_name}")
            
            from backend.src.rag_system.embeddings import LangchainEmbeddingAdapter
            from backend.src.rag_system.vector_store import VectorStoreManager
            from backend.src.rag_system.hybrid_retriever import HybridRetriever
            from backend.src.llm.local_llm import LocalLLMManager
            from scripts.embed_json_data import JsonEmbeddingManager
            from config import get_config
            
            config = get_config()
            
            # Initialize embeddings
            logger.debug("Loading embedding model...")
            try:
                self.embeddings = JsonEmbeddingManager(model_name=config.EMBEDDING_MODEL)
            except Exception as e:
                logger.warning(f"Failed to load configured embedding model: {e}")
                fallback_model = 'all-MiniLM-L6-v2'
                logger.info(f"Falling back to: {fallback_model}")
                self.embeddings = JsonEmbeddingManager(model_name=fallback_model)
            
            embedding_adapter = LangchainEmbeddingAdapter(self.embeddings.model)
            
            # Setup vector store
            vector_store_path = Path(config.VECTOR_STORE_PATH).parent / vector_store_name
            self.vector_store = VectorStoreManager(str(vector_store_path))
            
            if os.path.exists(f"{vector_store_path}/faiss_index"):
                logger.info("Loading existing vector store...")
                self.vector_store.load_store(embedding_adapter)
            else:
                logger.info("Creating new vector store...")
                from backend.src.document_processor.pdf_handler import PDFHandler
                from langchain_core.documents import Document
                
                pdf_handler = PDFHandler()
                documents = pdf_handler.process_directory(config.PDF_DATA_PATH)
                
                if documents:
                    self.vector_store.create_store(documents, embedding_adapter)
                else:
                    logger.warning("No PDF documents found, creating placeholder")
                    dummy_doc = [Document(page_content="Placeholder", metadata={"source": "placeholder"})]
                    self.vector_store.create_store(dummy_doc, embedding_adapter)
            
            # Initialize LLM
            logger.debug("Initializing LLM manager...")
            self.llm_manager = LocalLLMManager(
                model_name=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE
            )
            
            # Setup retriever (skip BOM and hierarchy for now)
            logger.debug("Setting up retriever...")
            self.retriever = HybridRetriever(
                vector_store_json=self.vector_store,
                embeddings=self.embeddings,
                bom_index=None,  # Skip for JSON testing
                hierarchy_tree=None
            )
            
            logger.info("Vector store initialization completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Vector store initialization failed: {e}", exc_info=True)
            return False
    
    def get_db_connection(self):
        """Get MongoDB database connection."""
        if not self.is_connected:
            raise RuntimeError("Database not connected. Call connect_mongodb() first.")
        return self.mongo_db
    
    def get_conversations_collection(self):
        """Get conversations collection."""
        if not self.is_connected:
            return None
        return self.conversations_collection
    
    def get_sessions_collection(self):
        """Get sessions collection."""
        if not self.is_connected:
            return None
        return self.sessions_collection
    
    def get_retriever(self):
        """Get the retriever instance."""
        return self.retriever
    
    def get_llm_manager(self):
        """Get the LLM manager instance."""
        return self.llm_manager
    
    def get_embeddings(self):
        """Get the embeddings instance."""
        return self.embeddings
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on database and vector store.
        
        Returns:
            Dict containing health status information
        """
        health_status = {
            "mongodb": {"status": "disconnected", "details": {}},
            "vector_store": {"status": "not_initialized", "details": {}},
            "overall": "unhealthy"
        }
        
        # Check MongoDB
        try:
            if self.is_connected and self.mongo_client:
                # Test connection
                self.mongo_client.admin.command('ping')
                
                # Get collection stats
                conv_count = self.conversations_collection.count_documents({})
                sessions_count = self.sessions_collection.count_documents({})
                
                health_status["mongodb"] = {
                    "status": "connected",
                    "details": {
                        "database": self.db_name,
                        "conversations_count": conv_count,
                        "sessions_count": sessions_count
                    }
                }
        except Exception as e:
            health_status["mongodb"]["details"]["error"] = str(e)
        
        # Check vector store
        try:
            if self.vector_store and self.retriever:
                # Test retrieval
                test_results = self.retriever.retrieve("test query", k=1)
                
                health_status["vector_store"] = {
                    "status": "initialized",
                    "details": {
                        "retriever_available": True,
                        "test_results_count": len(test_results)
                    }
                }
        except Exception as e:
            health_status["vector_store"]["details"]["error"] = str(e)
        
        # Overall status
        mongodb_ok = health_status["mongodb"]["status"] == "connected"
        vector_ok = health_status["vector_store"]["status"] == "initialized"
        
        if mongodb_ok and vector_ok:
            health_status["overall"] = "healthy"
        elif mongodb_ok or vector_ok:
            health_status["overall"] = "partially_healthy"
        
        return health_status
    
    def close_connections(self):
        """Close all database connections."""
        try:
            if self.mongo_client:
                self.mongo_client.close()
                logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")


# Global database instance
_db_manager = None

def get_db_manager(mongo_uri: str = None, db_name: str = None) -> DatabaseManager:
    """
    Get or create global database manager instance.
    
    Args:
        mongo_uri: MongoDB connection URI
        db_name: MongoDB database name
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(mongo_uri, db_name)
    
    return _db_manager

def init_database(vector_store_name: str = 'vector_store_json') -> Tuple[bool, Dict[str, Any]]:
    """
    Initialize complete database system (MongoDB + vector store).
    
    Args:
        vector_store_name: Name of vector store to initialize
        
    Returns:
        Tuple of (success: bool, status_info: dict)
    """
    db_manager = get_db_manager()
    
    # Connect to MongoDB
    mongo_success = db_manager.connect_mongodb()
    
    # Initialize vector store
    vector_success = db_manager.initialize_vector_store(vector_store_name)
    
    # Get health status
    health_status = db_manager.health_check()
    
    overall_success = mongo_success and vector_success
    
    return overall_success, health_status