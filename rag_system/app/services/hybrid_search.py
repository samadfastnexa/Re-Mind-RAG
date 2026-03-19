"""
Hybrid search service combining vector similarity and BM25 keyword search.
"""
from typing import List, Dict
from rank_bm25 import BM25Okapi
import numpy as np


class HybridSearcher:
    """Combines dense vector search with sparse BM25 keyword search."""
    
    def __init__(self):
        self.bm25_index = None
        self.documents = []
        self.document_ids = []
        self.metadatas = []
    
    def index_documents(self, documents: List[str], ids: List[str], metadatas: List[Dict]):
        """
        Index documents for BM25 search.
        
        Args:
            documents: List of document texts
            ids: List of document IDs
            metadatas: List of metadata dictionaries
        """
        self.documents = documents
        self.document_ids = ids
        self.metadatas = metadatas
        
        # Tokenize documents for BM25
        tokenized_docs = [doc.lower().split() for doc in documents]
        self.bm25_index = BM25Okapi(tokenized_docs)
    
    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Perform BM25 keyword search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of results with BM25 scores
        """
        if not self.bm25_index or not self.documents:
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                results.append({
                    'content': self.documents[idx],
                    'metadata': self.metadatas[idx],
                    'bm25_score': float(scores[idx]),
                    'id': self.document_ids[idx]
                })
        
        return results
    
    @staticmethod
    def combine_results(
        vector_results: List[Dict],
        bm25_results: List[Dict],
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict]:
        """
        Combine vector and BM25 results with weighted scoring.
        
        Args:
            vector_results: Results from vector similarity search
            bm25_results: Results from BM25 keyword search
            vector_weight: Weight for vector similarity scores
            bm25_weight: Weight for BM25 scores
            
        Returns:
            Combined and reranked results
        """
        # Normalize vector scores (convert distance to similarity)
        max_vector_score = max([1 - r.get('distance', 0) for r in vector_results]) if vector_results else 1
        min_vector_score = min([1 - r.get('distance', 0) for r in vector_results]) if vector_results else 0
        vector_range = max_vector_score - min_vector_score or 1
        
        # Normalize BM25 scores
        max_bm25_score = max([r.get('bm25_score', 0) for r in bm25_results]) if bm25_results else 1
        bm25_range = max_bm25_score or 1
        
        # Create combined score dictionary
        combined_scores = {}
        
        # Add vector results
        for result in vector_results:
            # Use actual ChromaDB ID if present, otherwise construct it
            doc_id = result.get('id') or (
                result.get('metadata', {}).get('document_id', '') +
                '_chunk_' +
                str(result.get('metadata', {}).get('chunk_index', 0))
            )
            similarity = 1 - result.get('distance', 0)
            normalized_score = (similarity - min_vector_score) / vector_range if vector_range > 0 else 0
            
            combined_scores[doc_id] = {
                'result': result,
                'vector_score': normalized_score * vector_weight,
                'bm25_score': 0
            }
        
        # Add BM25 results
        for result in bm25_results:
            doc_id = result.get('id', '')
            normalized_score = result.get('bm25_score', 0) / bm25_range
            
            if doc_id in combined_scores:
                combined_scores[doc_id]['bm25_score'] = normalized_score * bm25_weight
            else:
                combined_scores[doc_id] = {
                    'result': result,
                    'vector_score': 0,
                    'bm25_score': normalized_score * bm25_weight
                }
        
        # Calculate final scores and sort
        final_results = []
        for doc_id, data in combined_scores.items():
            final_score = data['vector_score'] + data['bm25_score']
            result = data['result'].copy()
            result['hybrid_score'] = final_score
            result['vector_contribution'] = data['vector_score']
            result['bm25_contribution'] = data['bm25_score']
            final_results.append(result)
        
        # Sort by hybrid score
        final_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        return final_results


# Global instance
hybrid_searcher = HybridSearcher()
