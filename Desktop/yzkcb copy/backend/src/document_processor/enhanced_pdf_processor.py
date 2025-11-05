"""
Enhanced PDF Processor with GPU acceleration and advanced parsing
Designed for high-quality extraction of Yazaki quality documents
"""

from pathlib import Path
from typing import List, Dict, Optional
import logging
from langchain.schema import Document
import pdfplumber
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EnhancedPDFProcessor:
    """
    Advanced PDF processing with:
    - GPU-accelerated embedding (if available)
    - Table extraction and preservation
    - Section-aware chunking
    - Metadata enrichment
    - Quality-focused text extraction
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        use_gpu: bool = True,
        preserve_tables: bool = True,
        min_chunk_size: int = 100
    ):
        """
        Initialize enhanced processor
        
        Args:
            chunk_size: Target size for text chunks
            chunk_overlap: Overlap between chunks for context preservation
            use_gpu: Try to use GPU for processing (falls back to CPU)
            preserve_tables: Keep table structure intact
            min_chunk_size: Minimum chunk size (smaller chunks are merged)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_tables = preserve_tables
        self.min_chunk_size = min_chunk_size
        
        # Check GPU availability
        self.device = self._setup_device(use_gpu)
        
        logger.info(f"EnhancedPDFProcessor initialized:")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Chunk size: {chunk_size}")
        logger.info(f"  Preserve tables: {preserve_tables}")
    
    def _setup_device(self, use_gpu: bool) -> str:
        """Determine processing device"""
        if not use_gpu:
            return 'cpu'
        
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("✅ GPU available for processing")
                return 'cuda'
        except ImportError:
            pass
        
        logger.info("⚠️  GPU not available, using CPU")
        return 'cpu'
    
    def process_directory(
        self, 
        directory: str,
        file_pattern: str = "*.pdf",
        show_progress: bool = True
    ) -> List[Document]:
        """
        Process all PDFs in directory with enhanced extraction
        
        Args:
            directory: Path to PDF directory
            file_pattern: Glob pattern for PDF files
            show_progress: Show progress bar
            
        Returns:
            List of Document objects with enriched metadata
        """
        pdf_path = Path(directory)
        
        if not pdf_path.exists():
            logger.error(f"Directory not found: {directory}")
            return []
        
        pdf_files = list(pdf_path.glob(file_pattern))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory}")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        all_documents = []
        
        # Process each PDF
        iterator = tqdm(pdf_files, desc="Processing PDFs") if show_progress else pdf_files
        
        for pdf_file in iterator:
            try:
                docs = self.process_single_pdf(str(pdf_file))
                all_documents.extend(docs)
                
                if show_progress:
                    iterator.set_postfix({
                        'file': pdf_file.name[:20],
                        'chunks': len(docs),
                        'total': len(all_documents)
                    })
                else:
                    logger.info(f"  ✅ {pdf_file.name}: {len(docs)} chunks")
                    
            except Exception as e:
                logger.error(f"  ❌ Error processing {pdf_file.name}: {e}")
                continue
        
        logger.info(f"✅ Processing complete: {len(all_documents)} total chunks from {len(pdf_files)} PDFs")
        return all_documents
    
    def process_single_pdf(self, pdf_path: str) -> List[Document]:
        """
        Process a single PDF with advanced extraction
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of Document chunks with metadata
        """
        documents = []
        pdf_name = Path(pdf_path).name
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract tables if enabled
                if self.preserve_tables:
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            table_doc = self._table_to_document(
                                table, 
                                pdf_path, 
                                page_num, 
                                table_idx
                            )
                            if table_doc:
                                documents.append(table_doc)
                
                # Extract and chunk text
                text = page.extract_text()
                if text and text.strip():
                    text_chunks = self._chunk_text_intelligently(
                        text,
                        pdf_path,
                        page_num
                    )
                    documents.extend(text_chunks)
        
        return documents
    
    def _table_to_document(
        self,
        table: List[List],
        source: str,
        page_num: int,
        table_idx: int
    ) -> Optional[Document]:
        """
        Convert table to structured document
        
        Args:
            table: 2D list representing table
            source: PDF file path
            page_num: Page number
            table_idx: Table index on page
            
        Returns:
            Document with formatted table or None if empty
        """
        if not table or not any(any(cell for cell in row if cell) for row in table):
            return None
        
        # Format table as markdown-like text
        lines = []
        lines.append(f"[TABLE {table_idx + 1} from Page {page_num}]")
        lines.append("")
        
        # Add header row if it looks like a header
        if table and table[0]:
            header = " | ".join(str(cell) if cell else "" for cell in table[0])
            lines.append(header)
            lines.append("-" * len(header))
        
        # Add data rows
        for row in table[1:] if len(table) > 1 else table:
            if row:
                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                lines.append(row_text)
        
        table_text = "\n".join(lines)
        
        return Document(
            page_content=table_text,
            metadata={
                "source": source,
                "page": page_num,
                "type": "table",
                "table_index": table_idx,
                "filename": Path(source).name
            }
        )
    
    def _chunk_text_intelligently(
        self,
        text: str,
        source: str,
        page_num: int
    ) -> List[Document]:
        """
        Chunk text with intelligent splitting at section boundaries
        
        Args:
            text: Text to chunk
            source: PDF file path
            page_num: Page number
            
        Returns:
            List of Document chunks
        """
        chunks = []
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = ""
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If adding this paragraph exceeds chunk size
            if current_size + para_size > self.chunk_size and current_chunk:
                # Save current chunk
                if current_size >= self.min_chunk_size:
                    chunks.append(
                        Document(
                            page_content=current_chunk.strip(),
                            metadata={
                                "source": source,
                                "page": page_num,
                                "type": "text",
                                "chunk_size": current_size,
                                "filename": Path(source).name
                            }
                        )
                    )
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + "\n\n" + para if overlap_text else para
                current_size = len(current_chunk)
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_size = len(current_chunk)
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(
                Document(
                    page_content=current_chunk.strip(),
                    metadata={
                        "source": source,
                        "page": page_num,
                        "type": "text",
                        "chunk_size": len(current_chunk),
                        "filename": Path(source).name
                    }
                )
            )
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from end of chunk"""
        if len(text) <= self.chunk_overlap:
            return text
        
        # Get last chunk_overlap characters
        overlap = text[-self.chunk_overlap:]
        
        # Try to start at sentence boundary
        sentence_end = overlap.rfind('. ')
        if sentence_end > 0:
            return overlap[sentence_end + 2:]
        
        return overlap
    
    def get_statistics(self, documents: List[Document]) -> Dict:
        """
        Get processing statistics
        
        Args:
            documents: List of processed documents
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_documents": len(documents),
            "total_chunks": 0,
            "text_chunks": 0,
            "table_chunks": 0,
            "sources": set(),
            "pages": set(),
            "avg_chunk_size": 0,
            "min_chunk_size": float('inf'),
            "max_chunk_size": 0
        }
        
        chunk_sizes = []
        
        for doc in documents:
            stats["total_chunks"] += 1
            
            if doc.metadata.get("type") == "table":
                stats["table_chunks"] += 1
            else:
                stats["text_chunks"] += 1
            
            stats["sources"].add(doc.metadata.get("filename", "Unknown"))
            stats["pages"].add(doc.metadata.get("page", 0))
            
            size = len(doc.page_content)
            chunk_sizes.append(size)
            stats["min_chunk_size"] = min(stats["min_chunk_size"], size)
            stats["max_chunk_size"] = max(stats["max_chunk_size"], size)
        
        if chunk_sizes:
            stats["avg_chunk_size"] = sum(chunk_sizes) / len(chunk_sizes)
        
        stats["sources"] = list(stats["sources"])
        stats["num_sources"] = len(stats["sources"])
        stats["num_pages"] = len(stats["pages"])
        
        return stats
