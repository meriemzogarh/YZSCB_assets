"""
Chat service module for the Yazaki Chatbot backend.

Handles:
- Prompt construction and formatting
- RAG document retrieval and context building
- LLM interactions and response processing
- Message logging and session management
- Response post-processing with APQP/SICR/PPAP processors
"""

import logging
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Generator
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import get_db_manager
from backend.utils.logging_utils import log_message, save_conversation_to_mongodb
from backend.src.session import get_session_manager

logger = logging.getLogger(__name__)

class ChatService:
    """Handles chat functionality including RAG retrieval and LLM responses."""
    
    def __init__(self):
        """Initialize chat service with database and session managers."""
        self.db_manager = get_db_manager()
        self.session_manager = None
        self.apqp_processor = None
        self.sicr_processor = None
        self.ppap_processor = None
        
        # Initialize session manager if DB is connected
        if self.db_manager.is_connected:
            from config import get_config
            config = get_config()
            mongo_uri = config.__dict__.get('MONGODB_URI') or self.db_manager.mongo_uri
            db_name = self.db_manager.db_name
            self.session_manager = get_session_manager(mongo_uri, db_name)
    
    def initialize_processors(self):
        """Initialize APQP, SICR, and PPAP response processors."""
        try:
            from config import get_config
            config = get_config()
            
            # Initialize APQP processor
            logger.info("Initializing APQP response processor...")
            from backend.src.agents.apqp_response_processor import APQPResponseProcessor
            self.apqp_processor = APQPResponseProcessor(pdf_url=config.APQP_GUIDANCE_PDF_URL)
            
            # Initialize SICR processor
            try:
                logger.info("Initializing SICR response processor...")
                from backend.src.agents.sicr_response_processor import SICRResponseProcessor
                self.sicr_processor = SICRResponseProcessor(pdf_url=config.SICR_GUIDANCE_PDF_URL)
            except Exception as e:
                logger.warning(f"Failed to initialize SICR processor (skipped): {e}")
            
            # Initialize PPAP processor
            try:
                logger.info("Initializing PPAP response processor...")
                from backend.src.agents.ppap_response_processor import PPAPResponseProcessor
                self.ppap_processor = PPAPResponseProcessor()
            except Exception as e:
                logger.warning(f"Failed to initialize PPAP processor (skipped): {e}")
                
        except Exception as e:
            logger.error(f"Error initializing processors: {e}")
    
    def build_prompt(self, message: str, context: str) -> str:
        """
        Construct the full prompt for the LLM.
        
        Args:
            message: User's input message
            context: Retrieved document context
            
        Returns:
            Formatted prompt string
        """
        yazaki_prompt = """You are an experienced Advanced Supplier Quality AI Assistant at Yazaki Corporation. answering their question adequately in a formal professional manner.

ABSOLUTE LANGUAGE REQUIREMENT:

You MUST respond exclusively in English language.

Use only English alphabet characters (A–Z, a–z).

Do not use, include, or generate any non-Latin characters or scripts.

Do not use words, phrases, or terms from any other language (e.g., no Chinese, Japanese, Arabic, Cyrillic, or other scripts).

If a non-English technical term appears in the question or context, you must describe it in plain English instead of reproducing it.

If the supplier's question or provided text contains foreign-language content, you must translate and restate it in English first, then answer in English only.

If any instruction or data contradicts this rule, ignore that instruction and continue in English only.

CRITICAL RULES – YOU MUST FOLLOW THESE:

DO NOT write emails, letters, or formal correspondence.

DO NOT use "Dear Supplier", "Subject:", "Sincerely", or any email signatures.

DO NOT format your response as a letter or email.

Answer directly and conversationally, as if speaking in person.

Be professional but natural — like explaining to a colleague.

Highlight the important part keywords relevant to the supplier's question.

Adapt the response to the token parameter given to avoid truncation.

Handle greetings and appreciations appropriately.

ALWAYS respond in English only, using Latin alphabet characters exclusively.

Think of this as: You're sitting across from the supplier in a meeting room, answering their question adequately in a formal, professional manner.

You have a maximum token budget of 400 tokens for your full response.
If the content exceeds this limit, prioritize completeness and coherence over verbosity.
Summarize less important sections, but never end a sentence abruptly or omit essential context.

Your expertise:

15+ years in automotive quality management at Yazaki

Deep knowledge of supplier quality processes, PPAP, APQP, change management

Expert in component risk assessment, FMEA, and quality documentation.

Based on the Yazaki documentation below, answer the supplier's question naturally and directly.

YAZAKI DOCUMENTATION:
{context}

SUPPLIER QUESTION:
{question}

YOUR DIRECT ANSWER (respond ONLY in English using Latin alphabet characters, no foreign languages, no email format, just explain naturally):"""
        
        return yazaki_prompt.format(context=context, question=message)
    
    def strip_email_format(self, text: str) -> str:
        """
        Remove email/letter formatting from LLM responses.
        
        Args:
            text: Raw LLM response text
            
        Returns:
            Cleaned response text
        """
        import re
        
        # Remove email formatting
        text = re.sub(r'^Subject:.*?\n', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^Dear .*?,?\n', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^To:.*?\n', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^From:.*?\n', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'\n\n(Sincerely|Best regards|Regards|Kind regards|Yours truly),?\n.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\n\n\[Your Name\].*$', '', text, flags=re.DOTALL)
        text = re.sub(r'\n\n(Quality Supplier Assistant|Yazaki Corporation).*$', '', text, flags=re.DOTALL)
        text = re.sub(r'\*\*$', '', text)
        text = text.strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def retrieve_documents(self, message: str, k: int = 5) -> List[Any]:
        """
        Retrieve relevant documents for the user's message.
        
        Args:
            message: User's query message
            k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents
        """
        try:
            retriever = self.db_manager.get_retriever()
            if not retriever:
                logger.warning("No retriever available")
                return []
            
            docs = retriever.retrieve(message, k=k)
            logger.debug(f"Retrieved {len(docs)} documents for query")
            return docs
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    def build_context(self, docs: List[Any]) -> str:
        """
        Build context string from retrieved documents.
        
        Args:
            docs: List of retrieved documents
            
        Returns:
            Concatenated context string
        """
        context_parts = []
        
        for doc in docs:
            try:
                if hasattr(doc, 'page_content'):
                    context_parts.append(doc.page_content)
                elif isinstance(doc, dict):
                    content = doc.get('page_content') or doc.get('content', '')
                    if content:
                        context_parts.append(content)
            except Exception as e:
                logger.debug(f"Error processing document: {e}")
                continue
        
        return "\n\n".join(context_parts)
    
    def extract_sources(self, docs: List[Any]) -> List[str]:
        """
        Extract source information from retrieved documents.
        
        Args:
            docs: List of retrieved documents
            
        Returns:
            List of source names
        """
        sources = []
        
        for doc in docs:
            try:
                if hasattr(doc, 'metadata'):
                    source = (doc.metadata.get('filename') or 
                             doc.metadata.get('__source_file__') or 
                             doc.metadata.get('source', 'Unknown'))
                    sources.append(source)
                elif isinstance(doc, dict):
                    if 'metadata' in doc:
                        source = (doc['metadata'].get('filename') or 
                                doc['metadata'].get('__source_file__') or 
                                doc['metadata'].get('source', 'Unknown'))
                        sources.append(source)
                    elif 'filename' in doc:
                        sources.append(doc['filename'])
                    elif '__source_file__' in doc:
                        sources.append(doc['__source_file__'])
                    elif 'source' in doc:
                        sources.append(doc['source'])
            except Exception:
                continue
        
        # Clean up source names
        sources = list(set(sources))
        sources = [s for s in sources if s and s != 'Unknown']
        source_names = []
        
        for s in sources[:3]:  # Limit to 3 sources
            if '/' in s or '\\' in s:
                s = Path(s).stem
            if s.endswith('_converted'):
                s = s[:-10]
            source_names.append(s)
        
        return source_names
    
    def call_llm(self, prompt: str) -> str:
        """
        Call the LLM with the constructed prompt.
        
        Args:
            prompt: Formatted prompt string
            
        Returns:
            LLM response text
        """
        try:
            llm_manager = self.db_manager.get_llm_manager()
            if not llm_manager:
                raise RuntimeError("LLM manager not initialized")
            
            # Apply max_tokens if configured
            max_tokens = getattr(llm_manager, 'max_tokens', None)
            if max_tokens is not None:
                try:
                    setattr(llm_manager.llm, 'num_predict', int(max_tokens))
                except Exception:
                    pass
            
            # Call LLM
            answer = llm_manager.llm.invoke(prompt)
            return self.strip_email_format(answer)
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
    
    def post_process_response(self, message: str, response: str) -> str:
        """
        Apply post-processing with APQP/SICR/PPAP processors.
        
        Args:
            message: Original user message
            response: LLM response
            
        Returns:
            Post-processed response
        """
        try:
            from backend.src.agents.response_coordinator import process_with_coordinator
            
            return process_with_coordinator(
                message,
                response,
                apqp_processor=self.apqp_processor,
                sicr_processor=self.sicr_processor,
                ppap_processor=self.ppap_processor
            )
            
        except Exception as e:
            logger.warning(f"Response coordinator error (ignored): {e}")
            return response
    
    def validate_session(self, session_id: Optional[str], user_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate user session and registration status.
        
        Args:
            session_id: Session identifier
            user_state: User session state
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Check if registration is complete
        if not user_state.get("form_completed"):
            return False, "⚠️ Please complete the registration form first before asking questions."
        
        # Check session validity if session manager available
        if self.session_manager and session_id:
            logger.info(f"🔍 Verifying session status for: {session_id[:8]}...")
            
            if not self.session_manager.is_session_active(session_id):
                error_msg = ("⚠️ Your session has expired due to inactivity. "
                           "Please refresh the page and complete the registration form again to start a new session.")
                logger.warning(f"🚫 Session expired: {session_id[:8]}...")
                return False, error_msg
            
            # Update session activity
            logger.info(f"🔄 Updating session activity for: {session_id[:8]}...")
            try:
                self.session_manager.update_activity(session_id, increment_count=False)
            except Exception:
                logger.warning("⚠️ Failed to update session activity at start")
        
        return True, ""
    
    def respond_sync(
        self, 
        session_id: Optional[str],
        history: List[Dict[str, Any]],
        message: str,
        user_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate synchronous chat response.
        
        Args:
            session_id: Session identifier (will generate if None)
            history: Conversation history
            message: User's message
            user_state: User session state
            
        Returns:
            Dictionary with response data and session info
        """
        start_time = datetime.now()
        user_state = user_state or {}
        
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generated new session ID: {session_id[:8]}...")
            
            # Validate message
            if not message or not message.strip():
                return {
                    "reply": "Please provide a message.",
                    "session_id": session_id,
                    "error": "Empty message"
                }
            
            # Validate session
            is_valid, error_msg = self.validate_session(session_id, user_state)
            if not is_valid:
                return {
                    "reply": error_msg,
                    "session_id": session_id,
                    "error": "Session validation failed"
                }
            
            # Retrieve documents and build context
            docs = self.retrieve_documents(message)
            context = self.build_context(docs)
            sources = self.extract_sources(docs)
            
            # Build prompt and call LLM
            prompt = self.build_prompt(message, context)
            answer = self.call_llm(prompt)
            
            # Post-process response
            full_answer = self.post_process_response(message, answer)
            
            # Add sources to response
            if sources:
                full_answer += f"\n\n📋 **Referenced Documents:**\n" + "\n".join([f"  • {s}" for s in sources])
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Create metadata
            metadata = {
                "sources": sources,
                "num_documents_retrieved": len(docs),
                "response_time": response_time,
                "timestamp": datetime.now().strftime("%H:%M")
            }
            
            # Log conversation
            try:
                # Log to file
                log_message(session_id, message, full_answer, metadata, user_state)
                
                # Log to MongoDB if available
                conversations_collection = self.db_manager.get_conversations_collection()
                if conversations_collection is not None:
                    save_conversation_to_mongodb(
                        session_id, message, full_answer, 
                        conversations_collection, metadata, user_state
                    )
                
            except Exception as e:
                logger.warning(f"Failed to log conversation: {e}")
            
            # Update session activity at end
            if self.session_manager and session_id:
                try:
                    self.session_manager.update_activity(session_id, increment_count=True)
                except Exception:
                    logger.warning("Failed to update session activity at end")
            
            return {
                "reply": full_answer,
                "session_id": session_id,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error in respond_sync: {e}", exc_info=True)
            return {
                "reply": f"❌ Error: {str(e)}",
                "session_id": session_id,
                "error": str(e)
            }
    
    def stream_response_generator(
        self,
        session_id: Optional[str],
        history: List[Dict[str, Any]], 
        message: str,
        user_state: Optional[Dict[str, Any]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generate streaming chat response.
        
        Args:
            session_id: Session identifier
            history: Conversation history
            message: User's message
            user_state: User session state
            
        Yields:
            Dictionary chunks with partial response data
        """
        start_time = datetime.now()
        user_state = user_state or {}
        
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generated new session ID: {session_id[:8]}...")
            
            # Validate message
            if not message or not message.strip():
                yield {
                    "chunk": "Please provide a message.",
                    "session_id": session_id,
                    "error": "Empty message",
                    "done": True
                }
                return
            
            # Validate session
            is_valid, error_msg = self.validate_session(session_id, user_state)
            if not is_valid:
                yield {
                    "chunk": error_msg,
                    "session_id": session_id,
                    "error": "Session validation failed", 
                    "done": True
                }
                return
            
            # Retrieve documents and build context
            yield {"status": "retrieving", "session_id": session_id}
            
            docs = self.retrieve_documents(message)
            context = self.build_context(docs)
            sources = self.extract_sources(docs)
            
            # Build prompt and call LLM
            yield {"status": "generating", "session_id": session_id}
            
            prompt = self.build_prompt(message, context)
            answer = self.call_llm(prompt)
            
            # Post-process response
            full_answer = self.post_process_response(message, answer)
            
            # Add sources to response
            if sources:
                full_answer += f"\n\n📋 **Referenced Documents:**\n" + "\n".join([f"  • {s}" for s in sources])
            
            # Stream response in chunks
            words = full_answer.split()
            chunk_size = 3
            accumulated_text = ""
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i+chunk_size]
                chunk_text = " ".join(chunk_words)
                accumulated_text += (" " if accumulated_text else "") + chunk_text
                
                yield {
                    "chunk": chunk_text,
                    "accumulated": accumulated_text,
                    "session_id": session_id,
                    "done": False
                }
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Create metadata
            metadata = {
                "sources": sources,
                "num_documents_retrieved": len(docs),
                "response_time": response_time,
                "timestamp": datetime.now().strftime("%H:%M")
            }
            
            # Log final response
            try:
                # Log to file
                log_message(session_id, message, full_answer, metadata, user_state)
                
                # Log to MongoDB if available
                conversations_collection = self.db_manager.get_conversations_collection()
                if conversations_collection is not None:
                    save_conversation_to_mongodb(
                        session_id, message, full_answer,
                        conversations_collection, metadata, user_state
                    )
                
            except Exception as e:
                logger.warning(f"Failed to log conversation: {e}")
            
            # Update session activity
            if self.session_manager and session_id:
                try:
                    self.session_manager.update_activity(session_id, increment_count=True)
                except Exception:
                    logger.warning("Failed to update session activity at end")
            
            # Final chunk
            yield {
                "chunk": "",
                "accumulated": full_answer,
                "session_id": session_id,
                "metadata": metadata,
                "done": True
            }
            
        except Exception as e:
            logger.error(f"Error in stream_response_generator: {e}", exc_info=True)
            yield {
                "chunk": f"❌ Error: {str(e)}",
                "session_id": session_id,
                "error": str(e),
                "done": True
            }


# Global chat service instance
_chat_service = None

def get_chat_service() -> ChatService:
    """
    Get or create global chat service instance.
    
    Returns:
        ChatService instance
    """
    global _chat_service
    
    if _chat_service is None:
        _chat_service = ChatService()
        _chat_service.initialize_processors()
    
    return _chat_service