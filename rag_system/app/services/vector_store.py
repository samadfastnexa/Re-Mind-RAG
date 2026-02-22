"""
ChromaDB vector store service for document embeddings.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
from app.config import settings


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
        else:  # ollama - use local HuggingFace embeddings
            from langchain_community.embeddings import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",  # Fast, small, and accurate
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"description": "RAG document embeddings"}
        )
    
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
        
        return len(texts)
    
    def similarity_search(self, query: str, top_k: int = 4) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant documents with metadata
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results and results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
        
        return formatted_results
    
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
