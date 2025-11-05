# src/document_processor/pdf_handler.py

from pathlib import Path
from typing import List
from langchain.schema import Document
from .chunking_strategy import SmartChunker

class PDFHandler:
    """
    Handle PDF processing for vector store
    """
    
    def __init__(self):
        self.chunker = SmartChunker(chunk_size=500, overlap=100)
    
    def process_directory(self, directory: str) -> List[Document]:
        """Process all PDFs in directory"""
        
        pdf_path = Path(directory)
        documents = []
        
        for pdf_file in pdf_path.glob('*.pdf'):
            print(f"Processing {pdf_file.name}...")
            chunks = self.chunker.chunk_pdf(str(pdf_file))
            documents.extend(chunks)
        
        print(f"Total documents created: {len(documents)}")
        return documents