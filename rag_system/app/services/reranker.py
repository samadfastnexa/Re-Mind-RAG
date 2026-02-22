"""
Reranking service using cross-encoder models for improved relevance.
"""
from typing import List, Dict
from sentence_transformers import CrossEncoder
import os


class Reranker:
    """Rerank search results using a cross-encoder model."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker with a cross-encoder model.
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        try:
            # Suppress transformers warnings
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            self.model = CrossEncoder(model_name, max_length=512)
            self.model_loaded = True
        except Exception as e:
            print(f"Warning: Could not load reranker model: {e}")
            print("Reranking will be disabled")
            self.model_loaded = False
    
    def rerank(self, query: str, results: List[Dict], top_k: int = 6) -> List[Dict]:
        """
        Rerank search results using cross-encoder scoring.
        
        Args:
            query: User's query
            results: List of search results to rerank
            top_k: Number of top results to return
            
        Returns:
            Reranked results with relevance scores
        """
        if not self.model_loaded or not results:
            return results[:top_k]
        
        try:
            # Prepare query-document pairs
            pairs = [(query, result.get('content', '')) for result in results]
            
            # Get relevance scores from cross-encoder
            scores = self.model.predict(pairs)
            
            # Add scores to results
            for result, score in zip(results, scores):
                result['reranker_score'] = float(score)
                result['relevance_score'] = float(score)
            
            # Sort by reranker score
            reranked = sorted(results, key=lambda x: x.get('reranker_score', 0), reverse=True)
            
            return reranked[:top_k]
        
        except Exception as e:
            print(f"Warning: Reranking failed: {e}")
            return results[:top_k]


# Global instance - will be initialized when needed
_reranker_instance = None

def get_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> Reranker:
    """Get or create global reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker(model_name)
    return _reranker_instance
