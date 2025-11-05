# src/document_processor/chunking_strategy.py

from typing import List, Dict, Tuple
import re
import pdfplumber
from langchain.schema import Document

class SmartChunker:
    """
    Chunks PDFs while preserving table context and schemas
    """
    
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_pdf(self, pdf_path: str) -> List[Document]:
        """
        Process PDF with table and schema awareness
        """
        chunks = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract tables with their context
                tables = page.extract_tables()
                text = page.extract_text()
                
                if tables:
                    for table in tables:
                        # Convert table to markdown-like format
                        table_text = self._table_to_text(table)
                        # Keep table with surrounding context
                        context = f"[PAGE {page_num + 1}]\n{table_text}"
                        chunks.append(Document(
                            page_content=context,
                            metadata={
                                "source": pdf_path,
                                "page": page_num + 1,
                                "type": "table",
                                "table_index": len(chunks)
                            }
                        ))
                
                # Process remaining text in intelligent chunks
                text_chunks = self._intelligent_chunk_text(
                    text, page_num + 1, pdf_path
                )
                chunks.extend(text_chunks)
        
        return chunks
    
    def _table_to_text(self, table: List[List]) -> str:
        """Convert table to readable format"""
        lines = []
        for row in table:
            lines.append(" | ".join(str(cell) if cell else "" for cell in row))
        return "\n".join(lines)
    
    def _intelligent_chunk_text(
        self, 
        text: str, 
        page_num: int, 
        source: str
    ) -> List[Document]:
        """
        Split text by sections/headers while respecting chunk size
        """
        chunks = []
        
        # Split by headers (lines starting with numbers, caps, etc.)
        sections = self._split_by_sections(text)
        
        for section_title, section_text in sections:
            # Further chunk if section is too large
            if len(section_text) > self.chunk_size:
                sub_chunks = self._split_by_sentences(
                    section_text, 
                    self.chunk_size
                )
            else:
                sub_chunks = [section_text]
            
            for chunk_text in sub_chunks:
                chunks.append(Document(
                    page_content=f"{section_title}\n{chunk_text}",
                    metadata={
                        "source": source,
                        "page": page_num,
                        "type": "text",
                        "section": section_title
                    }
                ))
        
        return chunks
    
    def _split_by_sections(self, text: str) -> List[Tuple[str, str]]:
        """Extract sections based on headers"""
        # Implementation would identify headers and section boundaries
        pass
    
    def _split_by_sentences(self, text: str, max_size: int) -> List[str]:
        """Smart sentence-based chunking"""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) > max_size and current:
                chunks.append(current)
                current = sentence
            else:
                current += " " + sentence if current else sentence
        
        if current:
            chunks.append(current)
        
        return chunks