"""
RAG chain implementation using LangChain with OpenAI or Ollama.
Enhanced with hybrid search, reranking, and multiple answer types.
"""
from typing import Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.services.vector_store import vector_store
from app.services.reranker import get_reranker
from app.services.conversation_history import conversation_history


class RAGChain:
    """RAG chain for question answering over documents with advanced features."""
    
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
        
        # Initialize reranker if enabled
        self.reranker = get_reranker(settings.reranker_model) if settings.enable_reranking else None
        
        # Define answer type templates
        self.answer_type_prompts = {
            "default": self._create_default_prompt(),
            "summary": self._create_summary_prompt(),
            "detailed": self._create_detailed_prompt(),
            "bullet_points": self._create_bullet_points_prompt(),
            "compare": self._create_compare_prompt(),
            "explain_simple": self._create_simple_explanation_prompt()
        }
    
    def _create_default_prompt(self) -> ChatPromptTemplate:
        """Standard Q&A prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a precise and knowledgeable AI assistant. Your task is to answer questions using ONLY the information provided in the context below.

CRITICAL RULES:
1. Answer ONLY based on the context provided - never make assumptions or add external knowledge
2. If the context contains the answer, provide a clear, detailed, and well-structured response
3. If the context does NOT contain the answer, simply say: "I cannot answer this question based on the provided documents."
4. NEVER contradict yourself - if you don't know, say so; if you do know, provide the answer
5. Always cite which document and section your information comes from
6. Be specific, accurate, and factual
7. Use clear formatting with bullet points or paragraphs as appropriate

{conversation_context}

CONTEXT FROM DOCUMENTS:
{context}

Based ONLY on the context above, provide an accurate answer to the question below."""),
            ("human", "{question}")
        ])
    
    def _create_summary_prompt(self) -> ChatPromptTemplate:
        """Summarization prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at creating concise, informative summaries.

Your task is to summarize the key information from the provided context that is relevant to the user's question.

GUIDELINES:
1. Focus on the most important points
2. Be concise but comprehensive
3. Use bullet points for clarity
4. Maintain factual accuracy
5. Only use information from the context

CONTEXT:
{context}"""),
            ("human", "Summarize the following: {question}")
        ])
    
    def _create_detailed_prompt(self) -> ChatPromptTemplate:
        """Detailed explanation prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert analyst providing in-depth, comprehensive explanations.

Your task is to provide a thorough, detailed answer using ALL relevant information from the context.

GUIDELINES:
1. Include all relevant details and nuances
2. Explain concepts thoroughly
3. Provide examples when available
4. Use structured formatting (headings, bullet points)
5. Cite specific sources for each point
6. Only use information from the context

CONTEXT:
{context}"""),
            ("human", "Provide a detailed explanation: {question}")
        ])
    
    def _create_bullet_points_prompt(self) -> ChatPromptTemplate:
        """Bullet point extraction prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting and organizing key information.

Your task is to extract the most important points from the context and present them as clear, concise bullet points.

GUIDELINES:
1. Use bullet points for each key piece of information
2. Be concise and specific
3. Group related information together
4. Maintain factual accuracy
5. Only use information from the context

CONTEXT:
{context}"""),
            ("human", "Extract key points about: {question}")
        ])
    
    def _create_compare_prompt(self) -> ChatPromptTemplate:
        """Comparison prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at comparative analysis.

Your task is to compare and contrast the items mentioned in the question using information from the context.

GUIDELINES:
1. Create a clear comparison structure
2. Highlight similarities and differences
3. Use tables or bullet points for clarity
4. Be objective and factual
5. Only use information from the context

CONTEXT:
{context}"""),
            ("human", "Compare: {question}")
        ])
    
    def _create_simple_explanation_prompt(self) -> ChatPromptTemplate:
        """Simple explanation prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at explaining complex topics in simple, easy-to-understand language.

Your task is to explain the topic in the question using simple words and clear examples.

GUIDELINES:
1. Use simple, everyday language
2. Avoid technical jargon when possible
3. Use analogies and examples
4. Break down complex concepts
5. Only use information from the context

CONTEXT:
{context}"""),
            ("human", "Explain in simple terms: {question}")
        ])
    
    def format_context(self, search_results: List[Dict]) -> str:
        """
        Format search results into context string with enhanced source information.
        
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
            position = metadata.get('position_percent', 0)
            
            # Include score information for transparency
            score_info = ""
            if result.get('reranker_score'):
                score_info = f" [Relevance: {result['reranker_score']:.2f}]"
            elif result.get('hybrid_score'):
                score_info = f" [Hybrid Score: {result['hybrid_score']:.2f}]"
            
            context_parts.append(
                f"[Source {i}: {filename}, Section {chunk_index + 1} ({position:.0f}% through document){score_info}]\n{content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def format_sources(self, search_results: List[Dict]) -> List[Dict]:
        """
        Format sources for response with enhanced metadata.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of formatted source information
        """
        sources = []
        for i, result in enumerate(search_results):
            metadata = result.get('metadata', {})
            
            # Calculate relevance score (use reranker if available, else hybrid, else distance)
            relevance_score = 0.0
            if result.get('reranker_score'):
                relevance_score = float(result['reranker_score'])
            elif result.get('hybrid_score'):
                relevance_score = float(result['hybrid_score'])
            else:
                relevance_score = 1 - result.get('distance', 0)
            
            # Truncate content preview
            content_preview = result.get('content', '')
            if len(content_preview) > 200:
                content_preview = content_preview[:200] + "..."
            
            sources.append({
                "source_id": i + 1,
                "document_id": metadata.get('document_id', 'unknown'),
                "document": metadata.get('filename', 'Unknown'),
                "chunk": metadata.get('chunk_index', 0) + 1,
                "total_chunks": metadata.get('total_chunks', 1),
                "position_percent": metadata.get('position_percent', 0),
                "content": content_preview,
                "relevance_score": round(relevance_score, 4),
                "chunk_length": metadata.get('chunk_length', len(result.get('content', '')))
            })
        
        return sources
    
    def query(
        self, 
        question: str, 
        top_k: int = 4,
        answer_type: str = "default",
        filters: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Query the RAG system with advanced features.
        
        Args:
            question: User's question
            top_k: Number of relevant chunks to retrieve
            answer_type: Type of answer to generate (default, summary, detailed, etc.)
            filters: Optional metadata filters
            session_id: Optional conversation session ID for context
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Get conversation context if session provided
        conversation_context = ""
        if session_id and settings.enable_conversation_history:
            history = conversation_history.get_context_string(session_id, last_n=3)
            if history:
                conversation_context = f"\nPREVIOUS CONVERSATION:\n{history}\n"
        
        # Retrieve relevant documents with hybrid search
        search_results = vector_store.similarity_search(
            question, 
            top_k=settings.hybrid_top_k if settings.enable_hybrid_search else top_k,
            filters=filters
        )
        
        if not search_results:
            no_docs_response = {
                "question": question,
                "answer": "I don't have any documents to answer this question. Please upload some documents first.",
                "sources": [],
                "answer_type": answer_type
            }
            
            # Add to conversation history if session provided
            if session_id and settings.enable_conversation_history:
                conversation_history.add_message(session_id, "user", question)
                conversation_history.add_message(session_id, "assistant", no_docs_response["answer"])
            
            return no_docs_response
        
        # Apply reranking if enabled
        if settings.enable_reranking and self.reranker:
            search_results = self.reranker.rerank(question, search_results, top_k=top_k)
        else:
            search_results = search_results[:top_k]
        
        # Format context
        context = self.format_context(search_results)
        
        # Select prompt template based on answer type
        prompt_template = self.answer_type_prompts.get(answer_type, self.answer_type_prompts["default"])
        
        # Create chain
        chain = (
            {
                "context": lambda x: context, 
                "question": RunnablePassthrough(),
                "conversation_context": lambda x: conversation_context
            }
            | prompt_template
            | self.llm
            | StrOutputParser()
        )
        
        # Get answer
        answer = chain.invoke(question)
        
        # Format sources with enhanced metadata
        sources = self.format_sources(search_results)
        
        response = {
            "question": question,
            "answer": answer,
            "sources": sources,
            "answer_type": answer_type,
            "retrieval_metadata": {
                "total_sources": len(sources),
                "hybrid_search_used": settings.enable_hybrid_search,
                "reranking_used": settings.enable_reranking,
                "filters_applied": filters is not None
            }
        }
        
        # Add to conversation history if session provided
        if session_id and settings.enable_conversation_history:
            conversation_history.add_message(
                session_id, 
                "user", 
                question
            )
            conversation_history.add_message(
                session_id, 
                "assistant", 
                answer,
                metadata={"sources": sources, "answer_type": answer_type}
            )
        
        return response


# Global instance
rag_chain = RAGChain()
