"""
Simple Ollama LLM Manager
"""
import subprocess
import logging

logger = logging.getLogger(__name__)

class OllamaManager:
    def __init__(self, model_name="mistral:latest", temperature=0, max_tokens=None):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def configure(self, model_name=None, temperature=None, max_tokens=None):
        """Configure LLM parameters"""
        if model_name:
            self.model_name = model_name
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        return "✅ LLM configured successfully"

    def invoke(self, prompt: str) -> str:
        """Call Ollama with the prompt"""
        cmd = ["ollama", "run", self.model_name, prompt]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                error = f"Ollama error: {result.stderr}"
                logger.error(error)
                return f"Error: {error}"
        except subprocess.TimeoutExpired:
            return "Error: LLM request timed out"
        except Exception as e:
            logger.exception("Error calling Ollama")
            return f"Error: {str(e)}"