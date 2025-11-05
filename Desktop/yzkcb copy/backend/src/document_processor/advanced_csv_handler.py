# src/document_processor/advanced_csv_handler.py

import pandas as pd
from typing import Dict, List
import json

class AdvancedCSVProcessor:
    """
    Advanced CSV processing with search indexing
    """
    
    def __init__(self):
        self.bom_search_index = {}
        self.hierarchy_tree = {}
    
    def build_bom_search_index(self, bom_csv_path: str) -> Dict:
        """
        Build efficient search index for BOM
        Don't load entire CSV, create indexed structure
        """
        
        df = pd.read_csv(bom_csv_path)
        
        # Normalize column names
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
        
        # Create multi-dimensional index
        index = {
            "by_project": {},
            "by_supplier": {},
            "by_part_number": {},
            "by_category": {}
        }
        
        for _, row in df.iterrows():
            # Extract key fields
            project = str(row.get('project_id', row.get('project', ''))).strip()
            supplier = str(row.get('supplier', '')).strip()
            part_num = str(row.get('part_number', row.get('part_no', ''))).strip()
            category = str(row.get('category', row.get('buhin_category', ''))).strip()
            
            part_entry = {
                'part_number': part_num,
                'part_name': str(row.get('part_name', row.get('description', ''))).strip(),
                'supplier': supplier,
                'category': category,
                'status': str(row.get('status', 'active')).strip(),
                'specifications': {k: v for k, v in row.items() 
                                  if k not in ['project_id', 'supplier', 'part_number', 'category']
                }
            }
            
            # Index by multiple keys
            if project:
                if project not in index["by_project"]:
                    index["by_project"][project] = []
                index["by_project"][project].append(part_entry)
            
            if supplier:
                if supplier not in index["by_supplier"]:
                    index["by_supplier"][supplier] = []
                index["by_supplier"][supplier].append(part_entry)
            
            if part_num:
                index["by_part_number"][part_num] = part_entry
            
            if category:
                if category not in index["by_category"]:
                    index["by_category"][category] = []
                index["by_category"][category].append(part_entry)
        
        return index
    
    def build_hierarchy_tree(self, hierarchy_csv_path: str) -> Dict:
        """
        Build tree structure for part classification hierarchy
        """
        
        df = pd.read_csv(hierarchy_csv_path)
        
        # Normalize columns
        df.columns = [col.strip().lower() for col in df.columns]
        
        tree = {}
        parent_map = {}
        
        # First pass: create nodes
        for _, row in df.iterrows():
            class_id = str(row.get('class_id', row.get('id', ''))).strip()
            
            if not class_id:
                continue
            
            node = {
                'id': class_id,
                'name': str(row.get('class_name', row.get('name', ''))).strip(),
                'parent_id': str(row.get('parent_id', row.get('parent', ''))).strip() or None,
                'level': int(row.get('level', 0)),
                'requirements': [r.strip() for r in str(row.get('requirements', '')).split(';') if r.strip()],
                'children': []
            }
            
            tree[class_id] = node
            parent_map[class_id] = node.get('parent_id')
        
        # Second pass: build parent-child relationships
        root_nodes = []
        for class_id, node in tree.items():
            parent_id = parent_map.get(class_id)
            if parent_id and parent_id in tree:
                tree[parent_id]['children'].append(class_id)
            elif not parent_id:
                root_nodes.append(class_id)
        
        return {
            'root_nodes': root_nodes,
            'all_nodes': tree
        }
    
    def search_bom(self, index: Dict, query: str, search_type: str = 'all') -> List[Dict]:
        """
        Search BOM with multiple strategies
        
        Args:
            search_type: 'project', 'supplier', 'part', 'category', or 'all'
        """
        
        results = []
        query = query.lower().strip()
        
        def match_item(item, q):
            item_str = str(item).lower()
            return q in item_str or item_str in q
        
        if search_type in ['project', 'all']:
            for proj_id, parts in index['by_project'].items():
                if match_item(proj_id, query):
                    results.extend(parts)
        
        if search_type in ['supplier', 'all']:
            for sup, parts in index['by_supplier'].items():
                if match_item(sup, query):
                    results.extend(parts)
        
        if search_type in ['part', 'all']:
            if query in index['by_part_number']:
                results.append(index['by_part_number'][query])
        
        if search_type in ['category', 'all']:
            for cat, parts in index['by_category'].items():
                if match_item(cat, query):
                    results.extend(parts)
        
        # Remove duplicates
        unique_results = []
        seen = set()
        for item in results:
            key = item.get('part_number', '')
            if key not in seen:
                seen.add(key)
                unique_results.append(item)
        
        return unique_results[:20]  # Limit to 20 results