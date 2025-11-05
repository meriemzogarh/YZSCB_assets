# src/utils/analytics.py

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

class QueryAnalytics:
    """
    Analyze query patterns and performance
    """
    
    def __init__(self, queries_log: str = "logs/queries.jsonl"):
        self.queries_log = Path(queries_log)
    
    def load_queries(self, days: int = 7) -> list:
        """Load queries from last N days"""
        
        if not self.queries_log.exists():
            return []
        
        cutoff = datetime.now() - timedelta(days=days)
        queries = []
        
        with open(self.queries_log, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    log_time = datetime.fromisoformat(log_entry['timestamp'])
                    
                    if log_time > cutoff:
                        queries.append(log_entry)
                except:
                    continue
        
        return queries
    
    def get_statistics(self, days: int = 7) -> dict:
        """Calculate query statistics"""
        
        queries = self.load_queries(days)
        
        if not queries:
            return {
                "total_queries": 0,
                "date_range": f"Last {days} days",
                "message": "No queries found"
            }
        
        response_times = []
        status_counts = defaultdict(int)
        search_types = defaultdict(int)
        
        for q in queries:
            if 'response_time_ms' in q:
                response_times.append(q['response_time_ms'])
            if 'status' in q:
                status_counts[q['status']] += 1
            if 'search_type' in q:
                search_types[q['search_type']] += 1
        
        stats = {
            "total_queries": len(queries),
            "date_range": f"Last {days} days",
            "response_time_ms": {
                "avg": sum(response_times) / len(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
            },
            "status_distribution": dict(status_counts),
            "search_type_distribution": dict(search_types),
            "success_rate": (
                status_counts.get(200, 0) / len(queries) * 100
                if queries else 0
            )
        }
        
        return stats
    
    def get_common_queries(self, limit: int = 10) -> list:
        """Get most common query patterns"""
        
        queries = self.load_queries(days=30)
        query_counts = defaultdict(int)
        
        for q in queries:
            if 'query' in q:
                # Generalize query (remove specific values)
                generic = self._generalize_query(q['query'])
                query_counts[generic] += 1
        
        sorted_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_queries[:limit]
    
    def _generalize_query(self, query: str) -> str:
        """Generalize query to find patterns"""
        import re
        
        # Replace numbers with [NUM]
        query = re.sub(r'\d+', '[NUM]', query)
        # Replace specific part numbers with [PART]
        query = re.sub(r'\b[A-Z]{2,}\d{4,}\b', '[PART]', query)
        
        return query