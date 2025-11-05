# src/document_processor/csv_handler.py

import pandas as pd
import json
from typing import Dict, List

class CSVProcessor:
    """
    Handle BOM and hierarchy CSVs
    """
    
    def __init__(self):
        self.bom_data = None
        self.hierarchy_data = None
    
    def process_bom(self, csv_path: str) -> Dict:
        """
        Load and structure BOM data
        Don't store raw CSV, create indexed structure
        """
        df = pd.read_csv(csv_path)
        
        # Create searchable index
        bom_index = {}
        
        for idx, row in df.iterrows():
            project_id = row.get('project_id') or row.get('Project ID')
            if project_id not in bom_index:
                bom_index[project_id] = []
            
            bom_index[project_id].append({
                'part_number': row.get('part_number', row.get('Part Number')),
                'part_name': row.get('part_name', row.get('Part Name')),
                'supplier': row.get('supplier', row.get('Supplier')),
                'category': row.get('category', row.get('Category')),
                'status': row.get('status', row.get('Status'))
            })
        
        return bom_index
    
    def process_hierarchy(self, csv_path: str) -> Dict:
        """
        Load and structure item class hierarchy
        """
        df = pd.read_csv(csv_path)
        
        hierarchy = {}
        
        for idx, row in df.iterrows():
            class_id = row.get('class_id', row.get('Class ID'))
            hierarchy[class_id] = {
                'name': row.get('class_name', row.get('Class Name')),
                'parent': row.get('parent_id', row.get('Parent ID')),
                'requirements': row.get('requirements', '').split(';'),
                'properties': row.get('properties', '').split(';')
            }
        
        return hierarchy