# src/llm/local_llm.py

try:
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    # Fallback to old import if new package not installed
    from langchain_community.llms import Ollama
    import warnings
    warnings.warn("Please install langchain-ollama: pip install langchain-ollama", DeprecationWarning)

from langchain_core.callbacks.manager import CallbackManager
from langchain_core.callbacks import StreamingStdOutCallbackHandler
from .response_cleaner import ResponseCleaner, clean_chatbot_response

class LocalLLMManager:
    """
    Manage Ollama/local LLM integration
    """
    
    def __init__(
        self,
        model_name: str = "gemma3:4b",
        temperature: float = 0.3,  # Lower for factual responses
        top_p: float = 0.9,
        top_k: int = 40
    ):
        """
        Initialize local LLM via Ollama
        
        Args:
            model_name: Model to use (gemma3:4b, neural-chat, etc.)
            temperature: Lower = more factual, Higher = more creative
            top_p: Diversity parameter
            top_k: Top-k sampling
        """
        
        # Verify Ollama is running
        self._verify_ollama_running()
        
        self.llm = Ollama(
            model=model_name,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            base_url="http://127.0.0.1:11434",  # Use 127.0.0.1 for better Windows compatibility
            callback_manager=CallbackManager(
                [StreamingStdOutCallbackHandler()]
            )
        )
        self.model_name = model_name
        
        # Initialize response cleaner
        self.response_cleaner = ResponseCleaner(llm_manager=self)
    
    def _verify_ollama_running(self):
        """Check if Ollama service is running"""
        import requests
        try:
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=10)  # Increased timeout for Windows
            if response.status_code != 200:
                raise Exception("Ollama service not responding correctly")
        except requests.ConnectionError:
            raise Exception(
                "Ollama service not running. Start it with: ollama serve"
            )
    
    def get_completion(self, prompt: str, max_tokens: int = 500) -> str:
        """Get completion from local LLM"""
        response = self.llm.invoke(prompt)
        return response
    
    def get_qa_response(
        self,
        question: str,
        context: str,
        system_prompt: str = None
    ) -> str:
        """
        Get QA response with context (for RAG)
        """
        if system_prompt is None:
            system_prompt = """You are a Yazaki Supplier Quality Assistant. 
            Answer questions based on the provided context from Yazaki procedures and documentation.
            Be precise and cite document sections when relevant.
            If you don't know, say 'I don't have this information in the Yazaki documentation.'"""
        
        prompt = f"""{system_prompt}

Context from Yazaki Documentation:
{context}

Question: {question}

Answer:"""
        
        return self.llm.invoke(prompt)
    
    def get_cleaned_qa_response(
        self,
        question: str,
        context: str,
        system_prompt: str = None,
        use_llm_cleaning: bool = False
    ) -> dict:
        """
        Get QA response with automatic cleaning
        
        Args:
            question: User question
            context: Context from retrieval
            system_prompt: Optional system prompt
            use_llm_cleaning: Whether to use LLM-based cleaning
            
        Returns:
            Dictionary with 'response', 'rationale', and 'cleaning_metadata'
        """
        # Get raw response
        raw_response = self.get_qa_response(question, context, system_prompt)
        
        # Clean the response
        if use_llm_cleaning:
            cleaning_result = self.response_cleaner.clean_with_llm(raw_response, context)
        else:
            cleaning_result = self.response_cleaner.clean_response(raw_response, context)
        
        return {
            'response': cleaning_result.cleaned_response,
            'rationale': cleaning_result.rationale,
            'cleaning_metadata': {
                'original_length': cleaning_result.original_length,
                'cleaned_length': cleaning_result.cleaned_length,
                'changes_made': cleaning_result.changes_made,
                'reduction_percentage': round(
                    (cleaning_result.original_length - cleaning_result.cleaned_length) 
                    / cleaning_result.original_length * 100, 1
                ) if cleaning_result.original_length > 0 else 0
            }
        }