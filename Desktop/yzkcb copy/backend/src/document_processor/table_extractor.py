# src/document_processor/table_extractor.py

import pdfplumber
import pandas as pd
from typing import List, Dict, Tuple

class TablePreserver:
    """
    Extract and preserve table structure for better retrieval
    """
    
    def __init__(self):
        self.tables_cache = {}
    
    def extract_tables_with_context(
        self, 
        pdf_path: str
    ) -> List[Dict]:
        """
        Extract tables while preserving:
        - Table structure (markdown format)
        - Page context
        - Surrounding text (before/after)
        - Table title/caption
        """
        
        results = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                # Extract text with structure
                text = page.extract_text()
                
                # Extract tables
                tables = page.extract_tables()
                
                if not tables:
                    continue
                
                for table_idx, table in enumerate(tables):
                    # Convert to DataFrame for easier handling
                    try:
                        df = pd.DataFrame(table[1:], columns=table[0])
                    except:
                        df = pd.DataFrame(table)
                    
                    # Convert to markdown
                    table_md = self._dataframe_to_markdown(df)
                    
                    # Extract surrounding text (context)
                    context = self._extract_context(text, table_idx)
                    
                    # Store rich representation
                    table_doc = {
                        "source": pdf_path,
                        "page": page_idx + 1,
                        "table_index": table_idx,
                        "format": "markdown",
                        "content": table_md,
                        "context": context,
                        "columns": list(df.columns),
                        "rows": len(df),
                        "metadata": {
                            "is_table": True,
                            "table_type": self._classify_table(df)
                        }
                    }
                    
                    results.append(table_doc)
        
        return results
    
    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to markdown table"""
        return df.to_markdown(index=False)
    
    def _extract_context(self, text: str, table_idx: int) -> str:
        """Extract surrounding context"""
        # Split by common delimiters
        sections = text.split('\n\n')
        
        # Get sections around table position
        context_lines = []
        if table_idx > 0:
            context_lines.append(sections[max(0, table_idx - 1)])
        context_lines.append(sections[min(len(sections)-1, table_idx + 1)])
        
        return '\n'.join(context_lines)[:300]  # Limit to 300 chars
    
    def _classify_table(self, df: pd.DataFrame) -> str:
        """Classify table type for better retrieval"""
        num_cols = len(df.columns)
        num_rows = len(df)
        
        if num_cols > 10:
            return "matrix"  # RASIC, capability matrix
        elif num_rows > 20:
            return "large_list"  # KPI table, requirement list
        elif all(col.lower() in ['yes', 'no', 'true', 'false'] for col in df.iloc[0]):
            return "boolean"  # Checklist, yes/no table
        else:
            return "general"