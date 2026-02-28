"""
Smart Query Cache with fuzzy matching for typo tolerance.
Avoids redundant LLM calls by returning cached answers for similar questions.
Uses difflib (standard library) for string similarity - no extra dependencies.
"""
import re
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from collections import OrderedDict


class QueryCache:
    """
    Intelligent query cache that:
    1. Returns cached answers for exact matches (instant)
    2. Returns cached answers for fuzzy matches / typos (instant)
    3. Normalizes questions before comparison
    4. Auto-expires old entries
    5. Tracks cache hit statistics
    """
    
    def __init__(
        self,
        max_cache_size: int = 500,
        similarity_threshold: float = 0.82,
        cache_ttl_hours: int = 24,
    ):
        """
        Args:
            max_cache_size: Maximum number of cached Q&A pairs
            similarity_threshold: Minimum similarity ratio (0-1) to consider a match.
                0.82 catches most typos while avoiding false positives.
            cache_ttl_hours: Hours before a cache entry expires
        """
        self.cache: OrderedDict[str, Dict] = OrderedDict()
        self.max_cache_size = max_cache_size
        self.similarity_threshold = similarity_threshold
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        
        # Statistics
        self.stats = {
            "total_lookups": 0,
            "exact_hits": 0,
            "fuzzy_hits": 0,
            "misses": 0,
        }
    
    # ─── Normalization ────────────────────────────────────────────────
    
    @staticmethod
    def normalize_query(query: str) -> str:
        """
        Normalize a query for better matching:
        - Lowercase
        - Strip extra whitespace
        - Remove punctuation (except apostrophes for contractions)
        - Sort words alphabetically (so "what is battleship" == "battleship is what")
        """
        q = query.lower().strip()
        # Remove punctuation except apostrophes
        q = re.sub(r"[^\w\s']", "", q)
        # Collapse whitespace
        q = re.sub(r"\s+", " ", q).strip()
        return q
    
    @staticmethod
    def _make_key(normalized_query: str) -> str:
        """Create a hash key from normalized query."""
        return hashlib.md5(normalized_query.encode()).hexdigest()
    
    # ─── Fuzzy Matching ───────────────────────────────────────────────
    
    def _similarity(self, a: str, b: str) -> float:
        """
        Compute similarity ratio between two strings using SequenceMatcher.
        Returns value in [0, 1]. Handles common typo patterns well.
        """
        return SequenceMatcher(None, a, b).ratio()
    
    def _find_fuzzy_match(self, normalized_query: str) -> Optional[Dict]:
        """
        Search cache for a fuzzy match above the similarity threshold.
        Returns the best matching cached entry, or None.
        """
        best_match = None
        best_score = 0.0
        
        now = datetime.now()
        
        for key, entry in self.cache.items():
            # Skip expired entries
            if now - entry["cached_at"] > self.cache_ttl:
                continue
            
            score = self._similarity(normalized_query, entry["normalized_query"])
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = entry
        
        if best_match:
            best_match["_match_score"] = best_score
        
        return best_match
    
    # ─── Public API ───────────────────────────────────────────────────
    
    def get(self, question: str, answer_type: str = "default") -> Optional[Dict]:
        """
        Look up a question in the cache.
        
        Args:
            question: The user's raw question
            answer_type: The requested answer type
            
        Returns:
            Cached response dict if found (with 'cache_hit' metadata), else None
        """
        self.stats["total_lookups"] += 1
        normalized = self.normalize_query(question)
        key = self._make_key(normalized + "|" + answer_type)
        
        # 1. Exact match (fastest)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["cached_at"] <= self.cache_ttl:
                self.stats["exact_hits"] += 1
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return self._build_cached_response(entry, "exact", 1.0)
            else:
                # Expired – remove
                del self.cache[key]
        
        # 2. Fuzzy match (handles typos)
        fuzzy_entry = self._find_fuzzy_match(normalized)
        if fuzzy_entry and fuzzy_entry.get("answer_type") == answer_type:
            self.stats["fuzzy_hits"] += 1
            match_score = fuzzy_entry.pop("_match_score", 0.0)
            return self._build_cached_response(fuzzy_entry, "fuzzy", match_score)
        
        self.stats["misses"] += 1
        return None
    
    def put(
        self,
        question: str,
        answer: str,
        sources: List[Dict],
        answer_type: str = "default",
        metadata: Optional[Dict] = None,
    ):
        """
        Store a Q&A pair in the cache.
        
        Args:
            question: The original question
            answer: The LLM-generated answer
            sources: Source citations
            answer_type: Answer type used
            metadata: Any extra retrieval metadata
        """
        normalized = self.normalize_query(question)
        key = self._make_key(normalized + "|" + answer_type)
        
        self.cache[key] = {
            "original_question": question,
            "normalized_query": normalized,
            "answer": answer,
            "sources": sources,
            "answer_type": answer_type,
            "metadata": metadata or {},
            "cached_at": datetime.now(),
            "hit_count": 0,
        }
        
        # Evict oldest if over limit
        while len(self.cache) > self.max_cache_size:
            self.cache.popitem(last=False)
    
    def _build_cached_response(self, entry: Dict, match_type: str, score: float) -> Dict:
        """Build a response dict from a cache entry."""
        entry["hit_count"] = entry.get("hit_count", 0) + 1
        
        retrieval_metadata = entry.get("metadata", {}).copy()
        retrieval_metadata["cache_hit"] = True
        retrieval_metadata["cache_match_type"] = match_type
        retrieval_metadata["cache_match_score"] = round(score, 4)
        
        return {
            "question": entry["original_question"],
            "answer": entry["answer"],
            "sources": entry["sources"],
            "answer_type": entry["answer_type"],
            "retrieval_metadata": retrieval_metadata,
        }
    
    # ─── Management ───────────────────────────────────────────────────
    
    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove all expired entries."""
        now = datetime.now()
        expired_keys = [
            k for k, v in self.cache.items()
            if now - v["cached_at"] > self.cache_ttl
        ]
        for k in expired_keys:
            del self.cache[k]
    
    def get_stats(self) -> Dict:
        """Return cache statistics."""
        total = self.stats["total_lookups"]
        hits = self.stats["exact_hits"] + self.stats["fuzzy_hits"]
        return {
            **self.stats,
            "total_hits": hits,
            "hit_rate": f"{(hits / total * 100):.1f}%" if total > 0 else "0%",
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
        }


# Global instance
query_cache = QueryCache(
    max_cache_size=500,
    similarity_threshold=0.82,
    cache_ttl_hours=24,
)
