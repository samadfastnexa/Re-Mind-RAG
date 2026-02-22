"""
RAG chain implementation using LangChain with OpenAI or Ollama.
"""
from typing import Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.services.vector_store import vector_store


class RAGChain:
    """RAG chain for question answering over documents."""
    
    def __init__(self):
        # Initialize LLM based on provider
        if settings.llm_provider == "openai":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                openai_api_key=settings.openai_api_key,
                model=settings.openai_model,
                temperature=0.7
            )
        else:  # ollama
            from langchain_ollama import ChatOllama
            self.llm = ChatOllama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=0.1,  # Very low for maximum accuracy
                num_predict=512,  # Longer responses
                top_k=10,  # More focused selection
                top_p=0.85  # Slightly lower for better quality
            )
        
        # Define enhanced RAG prompt template for maximum quality and accuracy
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a precise and knowledgeable AI assistant. Your task is to answer questions using ONLY the information provided in the context below.

CRITICAL RULES:
1. Answer ONLY based on the context provided - never make assumptions or add external knowledge
2. If the context contains the answer, provide a clear, detailed, and well-structured response
3. If the context does NOT contain the answer, simply say: "I cannot answer this question based on the provided documents."
4. NEVER contradict yourself - if you don't know, say so; if you do know, provide the answer
5. Always cite which document and section your information comes from
6. Be specific, accurate, and factual
7. Use clear formatting with bullet points or paragraphs as appropriate

CONTEXT FROM DOCUMENTS:
{context}

Based ONLY on the context above, provide an accurate answer to the question below."""),
            ("human", "{question}")
        ])
    
    def format_context(self, search_results: List[Dict]) -> str:
        """
        Format search results into context string.
        
        Args:
            search_results: List of search results from vector store
            
        Returns:
            Formatted context string
        """
        context_parts = []
        for i, result in enumerate(search_results, 1):
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            filename = metadata.get('filename', 'Unknown')
            chunk_index = metadata.get('chunk_index', 0)
            
            context_parts.append(
                f"[Source {i}: {filename}, Chunk {chunk_index + 1}]\n{content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def format_sources(self, search_results: List[Dict]) -> List[Dict]:
        """
        Format sources for response.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of formatted source information
        """
        sources = []
        for result in search_results:
            metadata = result.get('metadata', {})
            sources.append({
                "document": metadata.get('filename', 'Unknown'),
                "chunk": metadata.get('chunk_index', 0) + 1,
                "content": result.get('content', '')[:200] + "...",  # First 200 chars
                "relevance_score": 1 - result.get('distance', 0)  # Convert distance to similarity
            })
        return sources
    
    def query(self, question: str, top_k: int = 4) -> Dict:
        """
        Query the RAG system.
        
        Args:
            question: User's question
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            Dictionary with answer and sources
        """
        # Retrieve relevant documents
        search_results = vector_store.similarity_search(question, top_k=top_k)
        
        if not search_results:
            return {
                "question": question,
                "answer": "I don't have any documents to answer this question. Please upload some documents first.",
                "sources": []
            }
        
        # Format context
        context = self.format_context(search_results)
        
        # Create chain
        chain = (
            {"context": lambda x: context, "question": RunnablePassthrough()}
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )
        
        # Get answer
        answer = chain.invoke(question)
        
        # Format sources
        sources = self.format_sources(search_results)
        
        return {
            "question": question,
            "answer": answer,
            "sources": sources
        }


# Global instance
rag_chain = RAGChain()
