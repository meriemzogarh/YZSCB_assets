# src/document_processor/schema_detector.py

import re
from typing import List, Dict

class SchemaDetector:
    """
    Detect and preserve process schemas, flowcharts, and hierarchies
    """
    
    # Patterns for Yazaki-specific elements
    PATTERNS = {
        "apqp_phase": r"APQP[- ]Phase\s+([0-9]+)[:\s]+(.+?)(?=APQP|$)",
        "ppap_element": r"PPAP[- ]Element\s+([0-9]+)[:\s]+(.+?)(?=PPAP|$)",
        "buhin_category": r"(M1a|M2|P1|P2|X1|MAM)[:\s]+(.+?)(?=(?:M1a|M2|P1|P2|X1|MAM)|$)",
        "process_step": r"(?:Step|Phase|Stage)\s+([0-9]+)[:\s]+(.+?)(?=Step|Phase|Stage|$)",
        "requirement": r"(?:Requirement|Must|Shall)[:\s]+(.+?)(?=(?:Requirement|Must|Shall)|$)",
    }
    
    def __init__(self):
        self.schemas = {}
    
    def extract_schemas(self, text: str, document_id: str) -> List[Dict]:
        """Extract structured schemas from text"""
        
        schemas = []
        
        for schema_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                schema_doc = {
                    "type": schema_type,
                    "document_id": document_id,
                    "content": match.group(0),
                    "groups": match.groups(),
                    "start_pos": match.start(),
                    "end_pos": match.end()
                }
                
                schemas.append(schema_doc)
        
        return schemas
    
    def structure_apqp_phases(self, text: str) -> Dict:
        """Extract and structure APQP phases"""
        
        phases = {}
        phase_pattern = r"APQP[- ]Phase\s+([0-9]+)[:\s]+(.+?)(?=APQP[- ]Phase|$)"
        
        for match in re.finditer(phase_pattern, text, re.DOTALL):
            phase_num = match.group(1)
            phase_content = match.group(2)
            
            # Parse sub-elements
            elements = self._parse_elements(phase_content)
            
            phases[f"phase_{phase_num}"] = {
                "number": phase_num,
                "content": phase_content,
                "elements": elements
            }
        
        return phases
    
    def _parse_elements(self, text: str) -> List[str]:
        """Extract elements from phase text"""
        # Look for bullet points, numbered lists
        pattern = r"(?:^|\n)[\s]*(?:[-•*]|\d+\.)\s+(.+?)(?=(?:[-•*]|\d+\.)|$)"
        matches = re.findall(pattern, text, re.MULTILINE)
        return [m.strip() for m in matches if m.strip()]