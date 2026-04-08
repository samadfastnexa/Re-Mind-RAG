"""
ChromaDB vector store service for document embeddings.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
from app.config import settings
from app.services.hybrid_search import hybrid_searcher


class VectorStore:
    """Manage ChromaDB vector store for document embeddings."""
    
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embeddings based on provider
        if settings.llm_provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=settings.openai_api_key,
                model=settings.openai_embedding_model
            )
        else:  # ollama - use configured Ollama embedding model
            try:
                from langchain_ollama import OllamaEmbeddings
                self.embeddings = OllamaEmbeddings(
                    base_url=settings.ollama_embedding_base_url,
                    model=settings.ollama_embedding_model
                )
            except Exception as e:
                print(f"Warning: Falling back to local HuggingFace embeddings: {e}")
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=settings.local_fallback_embedding_model,
                    model_kwargs={'device': settings.local_fallback_embedding_device},
                    encode_kwargs={'normalize_embeddings': settings.local_fallback_normalize_embeddings}
                )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"description": "RAG document embeddings"}
        )
        
        # Initialize hybrid search index
        self._rebuild_hybrid_index()
    
    def _rebuild_hybrid_index(self):
        """Rebuild BM25 index for hybrid search."""
        if not settings.enable_hybrid_search:
            return
        
        try:
            # Get all documents from ChromaDB
            all_data = self.collection.get(include=["documents", "metadatas"])
            
            if all_data and all_data['documents']:
                hybrid_searcher.index_documents(
                    documents=all_data['documents'],
                    ids=all_data['ids'],
                    metadatas=all_data['metadatas']
                )
        except Exception as e:
            print(f"Warning: Could not rebuild hybrid search index: {e}")
    
    def add_documents(self, chunks_with_metadata: List[dict], document_id: str) -> int:
        """
        Add document chunks to vector store.
        
        Args:
            chunks_with_metadata: List of chunks with metadata
            document_id: Unique document identifier
            
        Returns:
            Number of chunks added
        """
        texts = [chunk["text"] for chunk in chunks_with_metadata]
        metadatas = [chunk["metadata"] for chunk in chunks_with_metadata]
        
        # Generate embeddings
        embeddings_list = self.embeddings.embed_documents(texts)
        
        # Create unique IDs for each chunk
        ids = [f"{document_id}_chunk_{i}" for i in range(len(texts))]
        
        # Add to ChromaDB
        self.collection.add(
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        # Rebuild hybrid search index
        self._rebuild_hybrid_index()
        
        return len(texts)
    
    def similarity_search(
        self, 
        query: str, 
        top_k: int = 4,
        filters: Optional[Dict] = None,
        use_hybrid: bool = None
    ) -> List[Dict]:
        """
        Search for similar documents with optional hybrid search and filtering.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters (e.g., {"document_id": "doc_123"})
            use_hybrid: Override hybrid search setting
            
        Returns:
            List of relevant documents with metadata
        """
        # Determine if hybrid search should be used
        use_hybrid_search = use_hybrid if use_hybrid is not None else settings.enable_hybrid_search
        
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Build where clause for filtering
        where_clause = filters if filters else None
        
        # Get more results if using hybrid search (will be narrowed down later)
        retrieval_k = settings.hybrid_top_k if use_hybrid_search else top_k
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=retrieval_k,
            include=["documents", "metadatas", "distances"],
            where=where_clause
        )
        
        # Format vector results
        vector_results = []
        if results and results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                vector_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
        
        # If hybrid search is enabled, combine with BM25
        if use_hybrid_search and vector_results:
            # Get BM25 results
            bm25_results = hybrid_searcher.search(query, top_k=retrieval_k)
            
            # Rebuild hybrid index after deletion
            self._rebuild_hybrid_index()
            # Apply filters to BM25 results if needed
            if filters:
                bm25_results = self._filter_results(bm25_results, filters)
            
            # Combine results
            combined_results = hybrid_searcher.combine_results(
                vector_results,
                bm25_results,
                vector_weight=1 - settings.bm25_weight,
                bm25_weight=settings.bm25_weight
            )
            
            return combined_results[:top_k]
        
        return vector_results
    
    def _filter_results(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """
        Filter results based on metadata.
        
        Args:
            results: List of results to filter
            filters: Metadata filter dictionary
            
        Returns:
            Filtered results
        """
        filtered = []
        for result in results:
            metadata = result.get('metadata', {})
            matches = all(
                metadata.get(key) == value
                for key, value in filters.items()
            )
            if matches:
                filtered.append(result)
        return filtered
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks of a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Number of chunks deleted
        """
        # Get all chunk IDs for this document
        results = self.collection.get(
            where={"document_id": document_id},
            include=["metadatas"]
        )
        
        if results and results['ids']:
            self.collection.delete(ids=results['ids'])
            return len(results['ids'])
        
        return 0
    
    def list_documents(self) -> List[Dict]:
        """
        List all documents in the vector store.
        
        Returns:
            List of document information
        """
        # Get all items
        results = self.collection.get(include=["metadatas"])
        
        if not results or not results['metadatas']:
            return []
        
        # Group by document_id
        documents = {}
        for metadata in results['metadatas']:
            doc_id = metadata.get('document_id')
            if doc_id and doc_id not in documents:
                documents[doc_id] = {
                    'document_id': doc_id,
                    'filename': metadata.get('filename', 'Unknown'),
                    'chunks': 0,
                    'pages': metadata.get('pages')
                }
            if doc_id:
                documents[doc_id]['chunks'] += 1
        
        return list(documents.values())
    
    def get_document_chunks(self, document_id: str) -> List[Dict]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: The document ID to retrieve chunks for
            
        Returns:
            List of chunks with their content and metadata
        """
        results = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"]
        )
        
        if not results or not results['ids']:
            return []
        
        chunks = []
        for i, chunk_id in enumerate(results['ids']):
            # Use chunk_index from metadata, fallback to extracting from chunk_id
            chunk_number = results['metadatas'][i].get('chunk_index', i)
            chunks.append({
                'chunk_id': chunk_id,
                'content': results['documents'][i],
                'chunk_number': chunk_number,
                'metadata': results['metadatas'][i]
            })
        
        # Sort by chunk number
        chunks.sort(key=lambda x: x['chunk_number'])
        
        return chunks
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": settings.collection_name
        }


# Global instance
vector_store = VectorStore()
