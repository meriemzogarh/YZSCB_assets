"""
Enhanced Gradio chatbot with:
- Vector store selection
- Message delete and regenerate options
- Typing effect animation
- Timestamps on messages
- Disabled send while processing
- Session management with inactivity timeout

⚠️ DEPRECATED: This file is deprecated as of the Flask REST API migration.
All functionality has been extracted to:
- backend/db.py (database management)
- backend/services/chat_service.py (chat processing)
- backend/utils/logging_utils.py (logging)
- backend/routes/chat.py (API routes)
- backend/api.py (Flask app)
- frontend/static/ (web UI)

Use the new Flask API instead: python backend/api.py
See MIGRATION_GUIDE.md and API_DOCUMENTATION.md for details.

TODO: Remove this file after Flask API validation is complete.
"""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import gradio as gr
import logging
from pathlib import Path
import subprocess
import json
import time
import uuid
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Setup logging
from backend.src.utils.logger import setup_logging
logger, query_logger = setup_logging()

# Load configuration
from dotenv import load_dotenv
load_dotenv()
from config import get_config

# Import session manager
from backend.src.session import get_session_manager

# Import response processors
from backend.src.agents.apqp_response_processor import APQPResponseProcessor

ASSETS_DIR = Path(__file__).parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)  # safe-create
avatar_path = str(ASSETS_DIR / "src/1ksp_yazaki.png")
# ensure file exists in assets; otherwise leave None
if not Path(avatar_path).exists():
    avatar_path = None

# Global SYSTEM variable
SYSTEM = None

# Session Manager
session_manager = None

# Response Processors
apqp_processor = None
sicr_processor = None
ppap_processor = None

mongodb_connected = False


# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB = os.getenv('MONGODB_DB', 'yazaki_chatbot')
# DEPRECATED: user_registrations collection is no longer used
# All session and user data is now stored in 'sessions' collection via session_manager
MONGODB_COLLECTION = os.getenv('MONGODB_COLLECTION', 'user_registrations')  # Legacy - not used
MONGODB_CONVERSATIONS = os.getenv('MONGODB_CONVERSATIONS', 'conversations')

# MongoDB Client (initialized lazily)
mongo_client = None
mongo_db = None
mongo_collection = None
mongo_conversations = None

def init_mongodb():
    """Initialize MongoDB connection and session manager"""
    global mongo_client, mongo_db, mongo_collection, mongo_conversations, session_manager
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.admin.command('ping')
        mongo_db = mongo_client[MONGODB_DB]
        
        # Legacy collection - kept for backward compatibility but no longer actively used
        mongo_collection = mongo_db[MONGODB_COLLECTION]
        
        # Conversations collection - stores chat history
        mongo_conversations = mongo_db[MONGODB_CONVERSATIONS]
        
        # Create indexes for better query performance
        mongo_conversations.create_index([("session_id", 1)])
        mongo_conversations.create_index([("timestamp", -1)])
        
        logger.info(f"✅ MongoDB connected successfully to {MONGODB_DB}")
        logger.info(f"   Active Collections: conversations, sessions")
        logger.info(f"   Legacy Collection: {MONGODB_COLLECTION} (no longer used)")
        
        # Initialize session manager - handles 'sessions' collection
        session_manager = get_session_manager(MONGODB_URI, MONGODB_DB)
        session_manager.start_monitor()
        logger.info("✅ Session Manager initialized and monitoring started")
        mongodb_connected = True
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e}")
        logger.warning("Form data will not be persisted to database")
        mongodb_connected = False
        return False
    except Exception as e:
        logger.error(f"❌ MongoDB initialization error: {e}")
        mongodb_connected = False
        return False

def save_user_to_mongodb(user_data):
    """
    DEPRECATED: This function is no longer used.
    Session data is now stored directly in the 'sessions' collection via session_manager.
    
    Previously saved user registration data to MongoDB's 'user_registrations' collection.
    Now all session and user info is consolidated in the 'sessions' collection.
    """
    logger.warning("⚠️ save_user_to_mongodb() is deprecated. Use session_manager.create_session() instead.")
    return None

def save_conversation_to_mongodb(session_id, user_message, assistant_message, metadata=None, user_state=None):
    """Save conversation exchange to MongoDB. Accepts optional per-session user_state."""
    try:
        if mongo_conversations is None:
            logger.debug("MongoDB conversations collection not initialized, skipping save")
            return False

        state = user_state or USER_INFO_TEMPLATE or {}
        conversation_data = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "user_message": user_message,
            "assistant_message": assistant_message,
            "metadata": metadata or {},
            "user_info": {
                "full_name": state.get("full_name", ""),
                "company_name": state.get("company_name", ""),
                "project_name": state.get("project_name", "")
            }
        }

        result = mongo_conversations.insert_one(conversation_data)
        logger.debug(f"💬 Conversation saved to MongoDB (Session: {session_id[:8]}...)")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving conversation to MongoDB: {e}")
        return False


def get_ollama_models():
    """Get list of available Ollama models"""
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            models = []
            for line in lines[1:]:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
            return models if models else ['mistral:latest']
        else:
            logger.warning("Could not get Ollama models, using default")
            return ['mistral:latest']
    except Exception as e:
        logger.warning(f"Error getting Ollama models: {e}")
        return ['mistral:latest']

def initialize_system(vector_store_name='vector_store_json'):
    """Initialize all system components with selected vector store"""
    global SYSTEM, apqp_processor, sicr_processor, ppap_processor
    
    logger.info(f"Starting system initialization with vector store: {vector_store_name}")
    
    try:
        from backend.src.document_processor.pdf_handler import PDFHandler
        from backend.src.document_processor.advanced_csv_handler import AdvancedCSVProcessor
        from backend.src.rag_system.embeddings import LangchainEmbeddingAdapter
        from backend.src.rag_system.vector_store import VectorStoreManager
        from backend.src.rag_system.hybrid_retriever import HybridRetriever
        from backend.src.llm.local_llm import LocalLLMManager
        from backend.src.agents.conversation_manager import ConversationManager
        from scripts.embed_json_data import JsonEmbeddingManager
        
        config = get_config()
        
        # Initialize APQP, SICR, and PPAP response processors
        logger.info("Initializing APQP response processor...")
        apqp_processor = APQPResponseProcessor(pdf_url=config.APQP_GUIDANCE_PDF_URL)
        try:
            logger.info("Initializing SICR response processor...")
            from backend.src.agents.sicr_response_processor import SICRResponseProcessor
            sicr_processor = SICRResponseProcessor(pdf_url=config.SICR_GUIDANCE_PDF_URL)
        except Exception as e:
            logger.warning(f"Failed to initialize SICR processor (skipped): {e}")
        
        try:
            logger.info("Initializing PPAP response processor...")
            from backend.src.agents.ppap_response_processor import PPAPResponseProcessor
            ppap_processor = PPAPResponseProcessor()
        except Exception as e:
            logger.warning(f"Failed to initialize PPAP processor (skipped): {e}")
        
        # 1. Initialize embeddings
        logger.info("Loading embedding model...")
        try:
            embeddings = JsonEmbeddingManager(model_name=config.EMBEDDING_MODEL)
        except Exception as e:
            logger.warning(f"Failed to load configured embedding model: {e}")
            fallback_model = 'all-MiniLM-L6-v2'
            logger.info(f"Falling back to: {fallback_model}")
            embeddings = JsonEmbeddingManager(model_name=fallback_model)

        embedding_adapter = LangchainEmbeddingAdapter(embeddings.model)
        
        # 2. Setup vector store with selected store
        logger.info(f"Setting up vector store: {vector_store_name}")
        vector_store_path = Path(config.VECTOR_STORE_PATH).parent / vector_store_name
        vector_store = VectorStoreManager(str(vector_store_path))
        
        if os.path.exists(f"{vector_store_path}/faiss_index"):
            logger.info("Loading existing vector store...")
            vector_store.load_store(embedding_adapter)
        else:
            logger.info("Creating new vector store...")
            pdf_handler = PDFHandler()
            documents = pdf_handler.process_directory(config.PDF_DATA_PATH)
            if documents:
                vector_store.create_store(documents, embedding_adapter)
            else:
                logger.warning("No PDF documents found")
                from langchain_core.documents import Document
                dummy_doc = [Document(page_content="Placeholder", metadata={"source": "placeholder"})]
                vector_store.create_store(dummy_doc, embedding_adapter)
        
        # Skip CSV processing for JSON testing
        logger.info("Skipping CSV processing for JSON testing...")
        bom_index = None
        hierarchy_tree = None
        
        # 4. Initialize LLM
        logger.info("Initializing LLM...")
        llm_manager = LocalLLMManager(
            model_name=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE
        )
        
        # 5. Setup retriever
        logger.info("Setting up hybrid retriever...")
        retriever = HybridRetriever(vector_store, embeddings, bom_index, hierarchy_tree)
        
        SYSTEM = {
            "vector_store_json": vector_store,
            "retriever": retriever,
            "bom_index": bom_index,
            "hierarchy_tree": hierarchy_tree,
            "embeddings": embeddings,
            "llm_manager": llm_manager,
            "conversation_manager": ConversationManager()
        }
        
        logger.info("System initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"System initialization failed: {str(e)}", exc_info=True)
        return False

print("\n" + "="*60)
print("Initializing Yazaki Chatbot...")
print("="*60 + "\n")

# Initialize system with default vector store
if not initialize_system():
    print("ERROR: System initialization failed!")
    exit(1)

print("\n✅ System initialized successfully!\n")

# Initialize MongoDB
print("🔌 Connecting to MongoDB...")
mongodb_connected = init_mongodb()
if mongodb_connected:
    print("✅ MongoDB connection established\n")
else:
    print("⚠️ MongoDB not available - running without database\n")

# Global state for user information
USER_INFO_TEMPLATE = {
    "form_completed": False,
    "session_id": None,
    "full_name": "",
    "email": "",
    "company_name": "",
    "project_name": "",
    "supplier_type": "",
    "city": "",
    "country": ""
}

def strip_email_format(text):
    """Remove email/letter formatting from LLM responses and filter non-English characters"""
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

def check_and_set_model(model_name: str, temperature: float, max_tokens: int):
    """Verify the chosen Ollama model exists locally and set the LLM manager"""
    try:
        models = get_ollama_models()
        if model_name not in models:
            return (f"❌ Error: Model '{model_name}' not found locally.\n\n💡 Pull it with: ollama pull {model_name}", False)

        from backend.src.llm.local_llm import LocalLLMManager
        logger.info(f"Setting model: {model_name}, temp: {temperature}, max_tokens: {max_tokens}")
        llm_manager = LocalLLMManager(model_name=model_name, temperature=temperature)
        setattr(llm_manager, 'max_tokens', int(max_tokens))
        SYSTEM['llm_manager'] = llm_manager
        return (f"✅ Model Ready!\n\n🤖 Model: {model_name}\n🌡️ Temperature: {temperature}\n📝 Max Tokens: {max_tokens}\n\n👍 You can start chatting now!", True)
    except Exception as e:
        logger.error(f"Error initializing model: {e}")
        return (f"❌ Error initializing model '{model_name}':\n{str(e)}\n\n💡 Make sure Ollama is running: ollama serve", False)

############################################
import asyncio  # add this at top of file (only once)

async def chat_with_typing(message, history, enable_typing=False, user_state=None):
    """Async chat handler that yields (chatbot_history, submit_btn_update, msg_value, user_state)."""
    try:
        state = user_state or {}

        # If empty message -> ensure send is enabled and clear input
        if not message or not message.strip():
            yield history, gr.update(interactive=True), "", state
            return

        # NOTE: removed the previous immediate yield that disabled/cleared input
        # right away. We now append the user's message and the typing indicator
        # first so the question bubble appears immediately in the chat UI,
        # then disable the send button to prevent double-submits.

        # Check registration
        if not state.get("form_completed"):
            error_msg = "⚠️ Please complete the registration form first before asking questions."
            if not isinstance(history, list):
                history = []
            history.append({
                "role": "assistant",
                "content": error_msg,
                "metadata": {"timestamp": datetime.now().strftime("%H:%M")}
            })
            # Re-enable send and clear input
            yield history, gr.update(interactive=True), "", state
            return

        # Verify session status (same logic as before)
        if session_manager and state.get("session_id"):
            session_id = state["session_id"]
            logger.info(f"🔍 Verifying session status for: {session_id[:8]}...")
            if not session_manager.is_session_active(session_id):
                error_msg = ("⚠️ Your session has expired due to inactivity. "
                             "Please refresh the page and complete the registration form again to start a new session.")
                if not isinstance(history, list):
                    history = []
                history.append({
                    "role": "assistant",
                    "content": error_msg,
                    "metadata": {"timestamp": datetime.now().strftime("%H:%M")}
                })
                logger.warning(f"🚫 Session expired: {session_id[:8]}...")
                yield history, gr.update(interactive=True), "", state
                return

            # Update session activity at start
            logger.info(f"🔄 Updating session activity for: {session_id[:8]}...")
            try:
                session_manager.update_activity(session_id, increment_count=False)
            except Exception:
                logger.warning("⚠️ Failed to update session activity at start")
        elif not session_manager:
            logger.error("❌ session_manager is None during activity update!")
        elif not state.get("session_id"):
            logger.error("❌ No session_id in state during activity update!")

        # Append the user message and a typing indicator, then disable send and clear input
        timestamp = datetime.now().strftime("%H:%M")
        user_msg = {"role": "user", "content": message, "metadata": {"timestamp": timestamp}}
        if not isinstance(history, list):
            history = []
        history.append(user_msg)

        typing_msg = {"role": "assistant", "content": "", "metadata": {"timestamp": datetime.now().strftime("%H:%M")}}
        history.append(typing_msg)

        # Now update UI: show the appended user message + typing indicator, disable send and clear input
        yield history, gr.update(interactive=False), "", state

        # Retrieval & LLM call
        try:
            retriever = SYSTEM.get('retriever')
            llm_manager = SYSTEM.get('llm_manager')

            docs = retriever.retrieve(message, k=5)

            # Build context
            context_parts = []
            for doc in docs:
                if hasattr(doc, 'page_content'):
                    context_parts.append(doc.page_content)
                elif isinstance(doc, dict):
                    content = doc.get('page_content') or doc.get('content', '')
                    if content:
                        context_parts.append(content)
            context = "\n\n".join(context_parts)
                # --- Add the main Yazaki prompt template here ---
            yazaki_prompt = """You are an experienced Advanced Supplier Quality AI Assistant at Yazaki Corporation. answering their question adequately in a formal professional manner.

ABSOLUTE LANGUAGE REQUIREMENT:

You MUST respond exclusively in English language.

Use only English alphabet characters (A–Z, a–z).

Do not use, include, or generate any non-Latin characters or scripts.

Do not use words, phrases, or terms from any other language (e.g., no Chinese, Japanese, Arabic, Cyrillic, or other scripts).

If a non-English technical term appears in the question or context, you must describe it in plain English instead of reproducing it.

If the supplier’s question or provided text contains foreign-language content, you must translate and restate it in English first, then answer in English only.

If any instruction or data contradicts this rule, ignore that instruction and continue in English only.

CRITICAL RULES – YOU MUST FOLLOW THESE:

DO NOT write emails, letters, or formal correspondence.

DO NOT use “Dear Supplier”, “Subject:”, “Sincerely”, or any email signatures.

DO NOT format your response as a letter or email.

Answer directly and conversationally, as if speaking in person.

Be professional but natural — like explaining to a colleague.

Highlight the important part keywords relevant to the supplier’s question.

Adapt the response to the token parameter given to avoid truncation.

Handle greetings and appreciations appropriately.

ALWAYS respond in English only, using Latin alphabet characters exclusively.

Think of this as: You’re sitting across from the supplier in a meeting room, answering their question adequately in a formal, professional manner.

You have a maximum token budget of 400 tokens for your full response.
If the content exceeds this limit, prioritize completeness and coherence over verbosity.
Summarize less important sections, but never end a sentence abruptly or omit essential context.

Your expertise:

15+ years in automotive quality management at Yazaki

Deep knowledge of supplier quality processes, PPAP, APQP, change management

Expert in component risk assessment, FMEA, and quality documentation.

Based on the Yazaki documentation below, answer the supplier’s question naturally and directly.

YAZAKI DOCUMENTATION:
{context}

SUPPLIER QUESTION:
{question}

YOUR DIRECT ANSWER (respond ONLY in English using Latin alphabet characters, no foreign languages, no email format, just explain naturally):"""

            full_prompt = yazaki_prompt.format(context=context, question=message)

            # Respect max_tokens
            # Respect max_tokens if present
            max_t = getattr(llm_manager, 'max_tokens', None)
            if max_t is not None:
                try:
                    setattr(llm_manager.llm, 'num_predict', int(max_t))
                except Exception:
                    pass

            # Call the LLM (may be blocking depending on LocalLLMManager)
            answer = llm_manager.llm.invoke(full_prompt)
            answer = strip_email_format(answer)

            # Collect sources (defensive)
            sources = []
            for doc in docs:
                if hasattr(doc, 'metadata'):
                    source = (doc.metadata.get('filename') or doc.metadata.get('__source_file__') or doc.metadata.get('source', 'Unknown'))
                    sources.append(source)
                elif isinstance(doc, dict):
                    if 'metadata' in doc:
                        source = (doc['metadata'].get('filename') or doc['metadata'].get('__source_file__') or doc['metadata'].get('source', 'Unknown'))
                        sources.append(source)
                    elif 'filename' in doc:
                        sources.append(doc['filename'])
                    elif '__source_file__' in doc:
                        sources.append(doc['__source_file__'])
                    elif 'source' in doc:
                        sources.append(doc['source'])

            sources = list(set(sources))
            sources = [s for s in sources if s and s != 'Unknown']
            source_names = []
            for s in sources[:3]:
                if '/' in s or '\\' in s:
                    s = Path(s).stem
                if s.endswith('_converted'):
                    s = s[:-10]
                source_names.append(s)

            if source_names:
                full_answer = f"{answer}\n\n📋 **Referenced Documents:**\n" + "\n".join([f"  • {s}" for s in source_names])
            else:
                full_answer = answer

            # Coordinate APQP, SICR, and PPAP post-processing so multiple docs can be
            # presented together when appropriate.
            try:
                from backend.src.agents.response_coordinator import process_with_coordinator
                full_answer = process_with_coordinator(
                    message,
                    full_answer,
                    apqp_processor=apqp_processor,
                    sicr_processor=sicr_processor,
                    ppap_processor=ppap_processor
                )
            except Exception as e:
                logger.warning(f"Response coordinator error (ignored): {e}")



            assistant_timestamp = datetime.now().strftime("%H:%M")

            # Typing animation (non-blocking)
            if enable_typing:
                words = full_answer.split()
                chunk_size = 3
                accumulated_text = " ".join(words[:chunk_size])
                # Replace the typing indicator with first chunk
                history[-1] = {"role": "assistant", "content": accumulated_text, "metadata": {"timestamp": assistant_timestamp}}
                yield history, gr.update(interactive=False), "", state

                for i in range(chunk_size, len(words), chunk_size):
                    accumulated_text = " ".join(words[:i+chunk_size])
                    history[-1] = {"role": "assistant", "content": accumulated_text, "metadata": {"timestamp": assistant_timestamp}}
                    yield history, gr.update(interactive=False), "", state
                    await asyncio.sleep(0.05)

                # Finalize to full answer and re-enable
                history[-1] = {"role": "assistant", "content": full_answer, "metadata": {"timestamp": assistant_timestamp}}
                yield history, gr.update(interactive=True), "", state
            else:
                # No typing animation - replace typing indicator with full message and re-enable button
                history[-1] = {"role": "assistant", "content": full_answer, "metadata": {"timestamp": assistant_timestamp}}
                yield history, gr.update(interactive=True), "", state

            # Save conversation — pass per-session state if available
            if mongodb_connected and state.get("session_id"):
                conversation_metadata = {"sources": source_names, "num_documents_retrieved": len(docs), "response_time": assistant_timestamp}
                try:
                    save_conversation_to_mongodb(session_id=state["session_id"], user_message=message, assistant_message=full_answer, metadata=conversation_metadata, user_state=state)
                except Exception as e:
                    logger.warning(f"Failed to save conversation to MongoDB: {e}")

            # Update session activity at end
            if session_manager and state.get("session_id"):
                try:
                    session_manager.update_activity(state["session_id"], increment_count=True)
                except Exception:
                    logger.warning("Failed to update session activity at end")

            return

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            if not isinstance(history, list):
                history = []
            history.append({"role": "assistant", "content": error_msg, "metadata": {"timestamp": datetime.now().strftime("%H:%M")}})
            # Ensure button re-enabled
            yield history, gr.update(interactive=True), "", state
            return

    except Exception as e:
        logger.error(f"Error in chat handler: {e}")
        err_hist = [{"role": "assistant", "content": f"❌ Error: {str(e)}", "metadata": {"timestamp": datetime.now().strftime("%H:%M")}}]
        yield err_hist, gr.update(interactive=True), "", {}
        return
    
#######################################################
def delete_message(history, index):
    """Handle message deletion by index (Gradio 4.x)"""
    if not isinstance(history, list):
        return []
    if 0 <= index < len(history):
        history.pop(index)
    return history

def regenerate_last_response(history):
    """Regenerate the last assistant response"""
    if not isinstance(history, list) or len(history) < 2:
        return history, ""
    
    # Find the last user message
    last_user_msg = None
    user_msg_idx = -1
    
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("role") == "user":
            last_user_msg = history[i].get("content")
            user_msg_idx = i
            break
    
    if not last_user_msg:
        return history, ""
    
    # Remove all messages after the last user message
    history = history[:user_msg_idx + 1]
    
    # Trigger regeneration by returning the user message
    return history, last_user_msg

# Get available models and vector stores
raw_models = get_ollama_models()
seen = set()
available_models = []
for m in raw_models:
    if not m or m in seen:
        continue
    if 'embed' in m.lower() or 'nomic' in m.lower():
        continue
    seen.add(m)
    available_models.append(m)
if not available_models:
    available_models = ['mistral:latest']

logger.info(f"Available Ollama models: {available_models}")

print("🚀 Launching Enhanced Gradio interface...\n")

# Custom CSS for better message display with timestamps
custom_css = """
.message-wrap {
    padding: 2px 4px !important;
    margin: 2px 0 !important;
}
.message-wrap .message {
    padding: 6px 10px !important;
    border-radius: 6px !important;
    font-size: 0.875rem !important;
    line-height: 1.7 !important;
    max-width: 95% !important;
    width: fit-content !important;
    word-wrap: normal !important;
    overflow-wrap: normal !important;
}
.message-wrap[data-role='user'] .message {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
}
.message-wrap[data-role='assistant'] .message {
    background: #f3f4f6 !important;
    border: 1px solid #e5e7eb !important;
}
.timestamp {
    font-size: 0.65rem;
    color: #6b7280;
    margin-top: 1px;
}
/* Compact layout */
.gradio-container {
    max-width: 100% !important;
    padding: 1rem !important;
}
h1 {
    margin-bottom: 0.5rem !important;
    font-size: 1.75rem !important;
}
.block {
    padding: 0.5rem !important;
}
/* Input area styling */
.input-row {
    margin-bottom: 0.5rem !important;
}
/* Message input with inline send button */
.input-with-button {
    gap: 0 !important;
    align-items: center !important;
    background: white !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
    padding: 4px !important;
    margin-bottom: 0.5rem !important;
}
.input-with-button textarea {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 8px 12px !important;
}
.input-with-button button {
    margin: 0 !important;
    height: 36px !important;
    border-radius: 6px !important;
}
"""

with gr.Blocks(theme=gr.themes.Soft(primary_hue="purple", secondary_hue="blue"), css=custom_css) as demo:
    gr.Markdown("# 🏭 Yazaki Advanced Supplier Quality Manager")
    gr.Markdown("Ask questions about supplier quality, change management, procedures, and quality standards.")
    
    # Add state persistence JavaScript
    gr.HTML("""
    <script>
    // State persistence for browser navigation
    (function() {
        // Save state when form is completed
        function saveUIState(isFormCompleted, sessionId) {
            localStorage.setItem('yazaki_form_completed', isFormCompleted);
            localStorage.setItem('yazaki_session_id', sessionId || '');
            console.log('Saved UI state:', isFormCompleted, sessionId);
        }
        
        // Restore state on page load
        function restoreUIState() {
            const formCompleted = localStorage.getItem('yazaki_form_completed') === 'true';
            const sessionId = localStorage.getItem('yazaki_session_id');
            
            console.log('Restoring UI state:', formCompleted, sessionId);
            
            if (formCompleted && sessionId) {
                // Wait for elements to be rendered with multiple attempts
                let attempts = 0;
                const maxAttempts = 10;
                
                function attemptRestore() {
                    attempts++;
                    
                    // Try multiple selection strategies
                    let formElement = null;
                    let chatElement = null;
                    
                    // Strategy 1: Look for groups/blocks by content
                    const allElements = document.querySelectorAll('div, section, form');
                    
                    for (let element of allElements) {
                        const innerHTML = element.innerHTML || '';
                        const textContent = element.textContent || '';
                        
                        // Find form element
                        if (!formElement && (
                            innerHTML.includes('Registration Form') || 
                            innerHTML.includes('Submit Registration') ||
                            innerHTML.includes('Supplier Registration') ||
                            textContent.includes('Please complete the form')
                        )) {
                            // Find the parent container
                            formElement = element.closest('[style*="display"], .block, .group') || element;
                        }
                        
                        // Find chat element
                        if (!chatElement && (
                            innerHTML.includes('chatbot') || 
                            innerHTML.includes('Chat') ||
                            element.classList.contains('chatbot') ||
                            innerHTML.includes('message') ||
                            innerHTML.includes('Example Questions')
                        )) {
                            // Find the parent container
                            chatElement = element.closest('[style*="display"], .block, .group') || element;
                        }
                    }
                    
                    // Strategy 2: If not found, try by gradio component structure
                    if (!formElement || !chatElement) {
                        const blocks = document.querySelectorAll('.block, [data-testid*="block"]');
                        for (let block of blocks) {
                            const content = block.innerHTML || '';
                            
                            if (!formElement && (content.includes('Full Name') || content.includes('Email') || content.includes('Company'))) {
                                formElement = block;
                            }
                            
                            if (!chatElement && (content.includes('chatbot') || content.includes('Chat') || content.includes('Send'))) {
                                chatElement = block;
                            }
                        }
                    }
                    
                    if (formElement && chatElement) {
                        // Hide form, show chat
                        formElement.style.display = 'none';
                        chatElement.style.display = 'block';
                        
                        // Also hide any parent containers if needed
                        let parent = formElement.parentElement;
                        while (parent && parent !== document.body) {
                            if (parent.style.display === 'none') {
                                break;
                            }
                            if (parent.innerHTML.includes('Registration Form')) {
                                parent.style.display = 'none';
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        
                        console.log('UI state restored - showing chat interface');
                        return true;
                    } else {
                        console.log(`Restore attempt ${attempts}: Form=${!!formElement}, Chat=${!!chatElement}`);
                        
                        if (attempts < maxAttempts) {
                            setTimeout(attemptRestore, 500);
                        } else {
                            console.log('Could not restore UI state after maximum attempts');
                        }
                        return false;
                    }
                }
                
                // Start restoration attempts
                setTimeout(attemptRestore, 100);
            }
        }
        
        // Listen for state changes
        window.addEventListener('yazaki-state-change', function(e) {
            saveUIState(e.detail.formCompleted, e.detail.sessionId);
        });
        
        // Restore on page load
        document.addEventListener('DOMContentLoaded', restoreUIState);
        
        // Also try immediate restore in case DOM is already loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', restoreUIState);
        } else {
            restoreUIState();
        }
        
        // Additional restore attempts on window load and after a delay
        window.addEventListener('load', () => setTimeout(restoreUIState, 500));
        setTimeout(restoreUIState, 2000);
    })();
    </script>
    """)
    
    user_state = gr.State(USER_INFO_TEMPLATE.copy())

    # Registration Form (shown initially)
    with gr.Group(visible=True) as form_row:
        gr.Markdown("## 📋 Supplier Registration Form")
        gr.Markdown("Please complete the form below to begin:")
        
        with gr.Row():
            with gr.Column(scale=1):
                form_full_name = gr.Textbox(
                    label="Full Name *",
                    placeholder="Enter your full name",
                    lines=1
                )
                form_email = gr.Textbox(
                    label="Email Address *",
                    placeholder="Enter your email address",
                    lines=1,
                    type="email"
                )
                form_company_name = gr.Textbox(
                    label="Company Name *",
                    placeholder="Enter your company name",
                    lines=1
                )
                form_project_name = gr.Textbox(
                    label="Project Name (Optional)",
                    placeholder="Enter project name if applicable",
                    lines=1
                )
            with gr.Column(scale=1):
                form_supplier_type = gr.Radio(
                    choices=["New Supplier", "Current Supplier"],
                    label="Supplier Type *",
                    value="New Supplier"
                )
                form_city = gr.Textbox(
                    label="City *",
                    placeholder="Enter city",
                    lines=1
                )
                form_country = gr.Textbox(
                    label="Country *",
                    placeholder="Enter country",
                    lines=1
                )
        
        form_submit_btn = gr.Button("✅ Submit Registration", variant="primary", size="lg")
        form_status = gr.Markdown("")
        # Hidden HTML component for executing JavaScript
        js_trigger = gr.HTML("", visible=False)

    # Chat Interface (hidden initially)
    with gr.Group(visible=False) as chat_interface:
        with gr.Row():
            with gr.Column(scale=2):
                # safe default pick for dropdown value
                default_model = None
                if len(available_models) > 2:
                    default_model = available_models[2]
                elif len(available_models) > 0:
                    default_model = available_models[0]
                else:
                    default_model = 'gemma3:4b'

                model_dropdown = gr.Dropdown(
                    choices=available_models,
                    value=default_model,
                    label="🤖 LLM Model"
                )
            with gr.Column(scale=1):
                temp_slider = gr.Slider(
                    minimum=0.0, 
                    maximum=1.0, 
                    value=0, 
                    step=0.05, 
                    label="🌡️ Temperature"
                )
            with gr.Column(scale=1):
                tokens_slider = gr.Slider(
                    minimum=100, 
                    maximum=2000, 
                    value=200, 
                    step=50, 
                    label="📝 Max Tokens"
                )
        
        with gr.Row():
            typing_effect_checkbox = gr.Checkbox(
                label="⌨️ Enable Typing Effect",
                value=False,
                info="Show animated typing effect (may cause slowdown on some systems)"
            )

        with gr.Row():
            set_model_button = gr.Button("✅ Set Model", variant="primary")

        status = gr.Textbox(label="System Status", interactive=False, lines=3)
        
        # Chat area with delete support
        chatbot = gr.Chatbot(
            type='messages',
            label="Chat",
            height=700,
            show_copy_button=True,
            avatar_images=(None, avatar_path),
            value=[],
            latex_delimiters=[
                {"left": "$$", "right": "$$", "display": True},
                {"left": "$", "right": "$", "display": False}
            ],
            sanitize_html=False,
            render_markdown=True,
            line_breaks=True
        )
        
        with gr.Row():
            regenerate_btn = gr.Button("🔁 Regenerate", scale=1, variant="secondary")
            clear_btn = gr.Button("🗑️ Clear Chat", scale=1)

        # Message input below chat with inline send button
        with gr.Row(elem_classes="input-with-button"):
            msg = gr.Textbox(
                label="",
                placeholder="Type your message here...",
                lines=1,
                show_label=False,
                scale=20,
                container=False
            )
            submit_btn = gr.Button("📤 Send", variant="primary", scale=1, size="sm")

        # Example questions (compact) with hover and click functionality
        with gr.Accordion("📚 Example Questions", open=False):
            example_questions = [
                "What are Yazaki's quality standards for suppliers?",
                "How do I submit a change request?",
                "What is the supplier quality concern management process?",
                "Explain the component risk assessment procedure",
                "What are my responsibilities as a supplier?",
                "What is the APQP process?"
            ]
            
            # Add custom CSS for hover effects
            gr.HTML("""
            <style>
                /* Multiple selectors for accordion header hover effect */
                .accordion .accordion-header,
                button[aria-expanded],
                .accordion-button,
                .gr-accordion button,
                details summary,
                [role="button"][aria-expanded] {
                    transition: all 0.2s ease !important;
                    cursor: pointer !important;
                }
                
                .accordion .accordion-header:hover,
                button[aria-expanded]:hover,
                .accordion-button:hover,
                .gr-accordion button:hover,
                details summary:hover,
                [role="button"][aria-expanded]:hover {
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
                    color: white !important;
                    transform: translateY(-1px) !important;
                    box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3) !important;
                    border-radius: 6px !important;
                }
                
                /* Broad selector for any clickable element containing "Example Questions" */
                *:has-text("Example Questions"):hover,
                *[aria-label*="Example Questions"]:hover,
                .block:has(*:contains("📚 Example Questions")) button:hover {
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
                    color: white !important;
                    transform: translateY(-1px) !important;
                    box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3) !important;
                    border-radius: 6px !important;
                }
                
                .example-btn {
                    margin: 4px 2px !important;
                    transition: all 0.2s ease !important;
                    border-radius: 8px !important;
                    font-size: 13px !important;
                    padding: 8px 12px !important;
                }
                
                .example-btn:hover {
                    transform: translateY(-1px) !important;
                    box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3) !important;
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
                    border-color: #0056b3 !important;
                }
                
                .example-btn:active {
                    transform: translateY(0) !important;
                    box-shadow: 0 2px 6px rgba(0, 123, 255, 0.2) !important;
                }
            </style>
            
            <script>
                // JavaScript to ensure accordion header hover effect works
                document.addEventListener('DOMContentLoaded', function() {
                    function addAccordionHover() {
                        // Find all elements that might be the accordion header
                        const selectors = [
                            'button[aria-expanded]',
                            '.accordion-button',
                            'details summary',
                            '[role="button"]'
                        ];
                        
                        selectors.forEach(selector => {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(element => {
                                if (element.textContent.includes('📚 Example Questions') || 
                                    element.textContent.includes('Example Questions')) {
                                    
                                    element.addEventListener('mouseenter', function() {
                                        this.style.background = 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)';
                                        this.style.color = 'white';
                                        this.style.transform = 'translateY(-1px)';
                                        this.style.boxShadow = '0 4px 12px rgba(0, 123, 255, 0.3)';
                                        this.style.borderRadius = '6px';
                                        this.style.transition = 'all 0.2s ease';
                                    });
                                    
                                    element.addEventListener('mouseleave', function() {
                                        this.style.background = '';
                                        this.style.color = '';
                                        this.style.transform = '';
                                        this.style.boxShadow = '';
                                    });
                                }
                            });
                        });
                    }
                    
                    // Run immediately and also after a delay to catch dynamically loaded content
                    addAccordionHover();
                    setTimeout(addAccordionHover, 1000);
                    setTimeout(addAccordionHover, 3000);
                });
            </script>
            """)
            
            # Create clickable buttons for each example question
            example_buttons = []
            for i, question in enumerate(example_questions):
                btn = gr.Button(
                    f"💬 {question}", 
                    variant="secondary", 
                    size="sm",
                    elem_classes=["example-btn"]
                )
                example_buttons.append(btn)

    def handle_form_submission(full_name, email, company_name, project_name, supplier_type, city, country, user_state):
        """Handle form submission (per-session state via gr.State)"""
        state = user_state or {}

        # Validate required fields
        if not full_name or not email or not company_name or not supplier_type or not city or not country:
            return (
                "❌ **Error**: Please fill in all required fields (marked with *).",  # form_status
                [],                                                                 # chatbot
                gr.update(visible=True),                                             # form_row
                gr.update(visible=False),                                            # chat_interface
                state,                                                               # user_state
                ""                                                                   # js_trigger
            )

        # Validate email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return (
                "❌ **Error**: Please enter a valid email address.",  # form_status
                [],                                                   # chatbot
                gr.update(visible=True),                              # form_row
                gr.update(visible=False),                             # chat_interface
                state,                                                # user_state
                ""                                                    # js_trigger
            )

        # Generate session id and update state
        session_id = str(uuid.uuid4())
        state.update({
            "form_completed": True,
            "session_id": session_id,
            "full_name": full_name.strip(),
            "email": email.strip().lower(),
            "company_name": company_name.strip(),
            "project_name": project_name.strip() if project_name else "N/A",
            "supplier_type": supplier_type,
            "city": city.strip(),
            "country": country.strip()
        })

        # Save session to DB if available (same as your code but using `state`)
        db_status = ""
        if mongodb_connected and session_manager:
            success = session_manager.create_session(session_id, {
                "full_name": state["full_name"],
                "email": state["email"],
                "company_name": state["company_name"],
                "project_name": state["project_name"],
                "supplier_type": state["supplier_type"],
                "city": state["city"],
                "country": state["country"]
            })
            db_status = ("\n\n💾 Your session has been created successfully." if success else "\n\n⚠️ Note: Could not save session to database, but you can still continue.")
        else:
            if not mongodb_connected:
                db_status = "\n\n⚠️ Note: Database not connected, session will not be persisted."

        # Build welcome message
        welcome_msg = f"""✅ **Registration Complete!**

Thank you, **{state['full_name']}** from **{state['company_name']}**!

**Your Information:**
• 👤 Name: {state['full_name']}
• 📧 Email: {state['email']}
• 🏢 Company: {state['company_name']}
• 📁 Project: {state['project_name']}
• 🏷️ Supplier Type: {state['supplier_type']}
• 📍 Location: {state['city']}, {state['country']}
• 🆔 Session ID: {session_id[:8]}...{db_status}

You can now ask questions about supplier quality, change management, procedures, and quality standards. I'm here to help!

Feel free to ask me anything related to Yazaki's supplier quality requirements. 🚀"""

        # JavaScript to save UI state
        js_code = f"""
        <script>
        setTimeout(() => {{
            window.dispatchEvent(new CustomEvent('yazaki-state-change', {{
                detail: {{ formCompleted: true, sessionId: '{session_id}' }}
            }}));
        }}, 100);
        </script>
        """

        return (
            "",  # form_status cleared
            [{
                "role": "assistant",
                "content": welcome_msg,
                "metadata": {"timestamp": datetime.now().strftime("%H:%M")}
            }],
            gr.update(visible=False),  # hide form_row
            gr.update(visible=True),   # show chat_interface
            state,                     # updated user_state
            js_code                    # js_trigger with JavaScript
        )


    form_submit_btn.click(
        handle_form_submission,
        inputs=[form_full_name, form_email, form_company_name, form_project_name,
                form_supplier_type, form_city, form_country, user_state],
        outputs=[form_status, chatbot, form_row, chat_interface, user_state, js_trigger]
    )


    # Wire up set model button
    def on_set_model(model_name, temperature, max_tokens):
        """
        Robust wrapper around check_and_set_model.
        Returns a single string for the status Textbox (so it's safe even if check_and_set_model fails).
        """
        try:
            result = check_and_set_model(model_name, temperature, max_tokens)
        except Exception as e:
            logger.exception("Exception calling check_and_set_model")
            return f"❌ Error initializing model: {e}"

        # If function returned None (or falsy), handle gracefully
        if result is None:
            return "❌ Error: check_and_set_model returned no result."

        # Accept either (msg, ok) or a plain string
        if isinstance(result, tuple) and len(result) >= 1:
            msg = str(result[0])
        else:
            msg = str(result)

        return msg


    set_model_button.click(
        on_set_model, 
        inputs=[model_dropdown, temp_slider, tokens_slider], 
        outputs=[status]
    )

    # Wire up chat send with typing effect
    # Wire up chat send with typing effect (use 4 outputs: chatbot, submit_btn, msg, user_state)
    submit_btn.click(
        chat_with_typing,
        inputs=[msg, chatbot, typing_effect_checkbox, user_state],
        outputs=[chatbot, submit_btn, msg, user_state]
    ).then(
        lambda: "",
        None,
        msg
    )

    # Also trigger on Enter key
    msg.submit(
        chat_with_typing,
        inputs=[msg, chatbot, typing_effect_checkbox, user_state],
        outputs=[chatbot, submit_btn, msg, user_state]
    ).then(
        lambda: "",
        None,
        msg
    )


    # Wire up regenerate button
    regenerate_btn.click(
        regenerate_last_response,
        inputs=[chatbot],
        outputs=[chatbot, msg]
    ).then(
    chat_with_typing,
    inputs=[msg, chatbot, typing_effect_checkbox, user_state],
    outputs=[chatbot, submit_btn, msg, user_state]
    ).then(
        lambda: "",
        None,
        msg
    )

    # Wire up clear button
    def clear_chat_and_reset_form(user_state=None):
        """Clear chat and reset per-session form state."""
        state = user_state or {}
        # reset fields
        state.update({
            "form_completed": False,
            "session_id": None,
            "full_name": "",
            "company_name": "",
            "project_name": "",
            "supplier_type": "",
            "city": "",
            "country": ""
        })
        
        # Clear localStorage
        clear_storage_js = """
        <script>
        localStorage.removeItem('yazaki_form_completed');
        localStorage.removeItem('yazaki_session_id');
        console.log('Cleared localStorage state');
        </script>
        """
        
        return (
            [],                                # chatbot
            gr.update(visible=True),           # form_row
            gr.update(visible=False),          # chat_interface
            "",                                # form_full_name
            "",                                # form_company_name
            "",                                # form_project_name
            "New Supplier",                    # form_supplier_type
            "",                                # form_city
            "",                                # form_country
            clear_storage_js,                  # form_status (includes JS)
            state                              # user_state
        )

    
    clear_btn.click(
        clear_chat_and_reset_form,
        inputs=[user_state],   # or None, user_state depending on your previous wiring
        outputs=[chatbot, form_row, chat_interface, form_full_name, form_company_name, form_project_name, form_supplier_type, form_city, form_country, form_status, user_state]
    )

    # Wire up example question buttons
    # Wire up example question buttons
    def handle_example_click(question, chatbot_history, user_state):
        """Handle example question button click - immediately show user message and typing indicator"""
        from datetime import datetime
        
        # Create user message with timestamp
        timestamp = datetime.now().strftime("%H:%M")
        user_msg = {"role": "user", "content": question, "metadata": {"timestamp": timestamp}}
        
        # Create typing indicator message with content
        typing_msg = {"role": "assistant", "content": "", "metadata": {"timestamp": datetime.now().strftime("%H:%M")}}
        
        # Add both messages to history immediately
        updated_history = chatbot_history + [user_msg, typing_msg]
        
        # Return: updated chatbot, disabled submit button, question in msg field, user_state
        return updated_history, gr.update(interactive=False), question, user_state
    
    for i, btn in enumerate(example_buttons):
        question = example_questions[i]
        
        # Create a proper closure to capture the specific question
        def create_click_handler(q):
            def click_handler(chatbot_history, user_state):
                return handle_example_click(q, chatbot_history, user_state)
            return click_handler
        
        btn.click(
            create_click_handler(question),
            inputs=[chatbot, user_state],
            outputs=[chatbot, submit_btn, msg, user_state]
        ).then(
            chat_with_typing,
            inputs=[msg, chatbot, typing_effect_checkbox, user_state],
            outputs=[chatbot, submit_btn, msg, user_state]
        )

if __name__ == "__main__":
    def launch(server_name: str = "localhost", server_port: int = 7861, share: bool = False):
        """Programmatic entrypoint to launch the Gradio demo."""
        demo.launch(server_name=server_name, server_port=server_port, share=share)


    if __name__ == "__main__":
        launch()
