# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    
    # Hugging Face Offline Mode
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_DATASETS_OFFLINE'] = '1'
    
    # LLM Config
    LLM_MODEL = os.getenv('LLM_MODEL', 'gemma3:4b')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.3))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', 500))
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    # Embeddings Config
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'fast')
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 500))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 100))
    
    # Vector Store Config
    VECTOR_STORE_PATH = os.getenv('VECTOR_STORE_PATH', 'data/processed/vector_store_json')
    VECTOR_STORE_TYPE = os.getenv('VECTOR_STORE_TYPE', 'faiss')
    
    # Data Paths
    PDF_DATA_PATH = os.getenv('PDF_DATA_PATH', 'data/pdf_backup')
    BOM_CSV_PATH = os.getenv('BOM_CSV_PATH', 'data/raw/bom_data.csv')
    HIERARCHY_CSV_PATH = os.getenv('HIERARCHY_CSV_PATH', 'data/raw/hierarchy_data.csv')
    
    # Agent Config
    MAX_AGENT_ITERATIONS = int(os.getenv('MAX_AGENT_ITERATIONS', 5))
    
    # APQP Guidance Config
    APQP_GUIDANCE_PDF_URL = os.getenv(
        'APQP_GUIDANCE_PDF_URL', 
        'https://drive.google.com/file/d/1pQ67wAzsZ01KLqMRcJvJvtkpFN2Ka8x_/view?usp=drive_link'
    )

    # SICR / Change Management Guidance Config
    SICR_GUIDANCE_PDF_URL = os.getenv(
        'SICR_GUIDANCE_PDF_URL',
        'https://drive.google.com/file/d/10xr2UwKx4aXm6NWrOzER7Zv899uq_5zD/view?usp=sharing'
    )
    
    # Flask Config
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True

def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()