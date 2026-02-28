"""
RAG chain implementation using LangChain with OpenAI or Ollama.
Enhanced with hybrid search, reranking, query caching, and multiple answer types.
"""
from typing import Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.services.vector_store import vector_store
from app.services.reranker import get_reranker
from app.services.conversation_history import conversation_history
from app.services.query_cache import query_cache


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
                temperature=0.15,  # Very low for maximum accuracy
                num_predict=1024,  # Longer, more complete responses
                top_k=15,  # Balanced selection
                top_p=0.9,  # Good diversity while staying focused
                repeat_penalty=1.15  # Reduce repetitive text
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
            ("system", """You are a precise, knowledgeable AI assistant. Answer questions using ONLY the provided context.

RULES:
1. Answer ONLY from the context — no external knowledge or assumptions
2. If the answer IS in the context, give a clear, complete, well-structured response
3. If the answer is NOT in the context, say: "I cannot answer this question based on the provided documents."
4. Interpret the user's intent even if there are typos or unclear phrasing
5. Be thorough — include all relevant details from the context
6. Never contradict the source material

FORMATTING:
- **Bold** key terms and important concepts
- Use bullet points or numbered lists for multiple items/steps
- Use ### headings for longer answers with multiple topics
- Use `code formatting` for file names, commands, technical terms
- Use > blockquotes for direct quotes from documents
- Keep short answers concise; expand only when the context is rich

{conversation_context}

CONTEXT FROM DOCUMENTS:
{context}

Answer the question below accurately and completely using ONLY the context above."""),
            ("human", "{question}")
        ])
    
    def _create_summary_prompt(self) -> ChatPromptTemplate:
        """Summarization prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at creating concise, informative summaries.

Your task is to summarize the key information from the provided context that is relevant to the user's question.

GUIDELINES:
1. Start with a one-sentence **TL;DR** in bold
2. Follow with 3-7 bullet points covering the key information
3. Use **bold** for the main idea of each bullet point
4. End with a brief conclusion sentence if appropriate
5. Maintain factual accuracy — only use information from the context
6. Reference [Source N] for each point where applicable

FORMAT EXAMPLE:
**TL;DR: [one-sentence summary]**

• **Key Point 1** — explanation [Source 1]
• **Key Point 2** — explanation [Source 2]

{conversation_context}

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
2. Explain concepts thoroughly with clear language
3. Provide examples when available
4. Only use information from the context

FORMATTING RULES:
- Start with a brief **overview** paragraph
- Use ### headings to organize into sections
- Use **bold** for key terms and important concepts
- Use numbered lists for sequential steps or processes
- Use bullet points for non-sequential items
- Use > blockquotes for direct references from documents
- Add [Source N] citations inline
- End with a **Key Takeaways** section using bullet points

{conversation_context}

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
1. Be concise and specific — one idea per bullet
2. Group related information under ### sub-headings when there are many points
3. Use **bold** for the key term or concept at the start of each bullet
4. Maintain factual accuracy — only use information from the context
5. Add [Source N] at the end of each bullet

FORMAT EXAMPLE:
### Category Name
• **Key Term** — concise explanation [Source 1]
• **Another Term** — concise explanation [Source 2]

{conversation_context}

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
1. Be objective and factual — only use information from the context
2. Highlight both similarities and differences clearly

FORMATTING RULES:
- Start with a brief overview of what is being compared
- Use a markdown table when comparing features/attributes:
  | Feature | Item A | Item B |
  |---------|--------|--------|
  | ...     | ...    | ...    |
- After the table, add ### Similarities and ### Differences sections with bullet points
- Use **bold** for key differentiators
- Add [Source N] citations
- End with a brief **Conclusion** paragraph

{conversation_context}

CONTEXT:
{context}"""),
            ("human", "Compare: {question}")
        ])
    
    def _create_simple_explanation_prompt(self) -> ChatPromptTemplate:
        """Simple explanation prompt."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at explaining complex topics in simple, easy-to-understand language — like explaining to a curious friend.

Your task is to explain the topic using simple words and clear examples.

GUIDELINES:
1. Use simple, everyday language — avoid jargon
2. Use analogies and real-world examples
3. Break down complex concepts step by step
4. Only use information from the context

FORMATTING RULES:
- Start with a one-sentence **simple answer** in bold
- Then explain "why" or "how" in 2-3 short paragraphs
- Use **bold** for important terms, followed by a simple definition in parentheses
- Use analogies formatted as: 💡 *Think of it like...*
- Use numbered steps if explaining a process
- Keep sentences short — max 20 words each when possible

{conversation_context}

CONTEXT:
{context}"""),
            ("human", "Explain in simple terms: {question}")
        ])
    
    def format_context(self, search_results: List[Dict]) -> str:
        """
        Format search results into context string with enhanced source information.
        Cleans and deduplicates content.
        
        Args:
            search_results: List of search results from vector store
            
        Returns:
            Formatted context string
        """
        context_parts = []
        seen_content = set()
        
        for i, result in enumerate(search_results, 1):
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            # Clean content - remove page markers and normalize whitespace
            content = content.replace('--- Page', '').strip()
            content = ' '.join(content.split())
            
            # Skip duplicate content
            content_key = content[:150].lower()
            if content_key in seen_content:
                continue
            seen_content.add(content_key)
            
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
                f"[Source {len(context_parts) + 1}: {filename}, Section {chunk_index + 1} ({position:.0f}% through document){score_info}]\n{content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def format_sources(self, search_results: List[Dict]) -> List[Dict]:
        """
        Format sources for response with enhanced metadata.
        Filters out duplicate/similar chunks and cleans content.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of formatted source information
        """
        sources = []
        seen_content = set()
        
        for i, result in enumerate(search_results):
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            # Clean content - remove page markers and excessive whitespace
            content = content.replace('--- Page', '').strip()
            content = ' '.join(content.split())
            
            # Skip if this is too similar to already seen content (simple deduplication)
            content_key = content[:100].lower()  # First 100 chars as key
            if content_key in seen_content:
                continue
            seen_content.add(content_key)
            
            # Calculate relevance score (use reranker if available, else hybrid, else distance)
            relevance_score = 0.0
            if result.get('reranker_score'):
                relevance_score = float(result['reranker_score'])
            elif result.get('hybrid_score'):
                relevance_score = float(result['hybrid_score'])
            else:
                relevance_score = 1 - result.get('distance', 0)
            
            # Create meaningful content preview
            content_preview = content
            if len(content_preview) > 300:
                content_preview = content_preview[:300] + "..."
            
            sources.append({
                "source_id": len(sources) + 1,  # Renumber after deduplication
                "document_id": metadata.get('document_id', 'unknown'),
                "document": metadata.get('filename', 'Unknown'),
                "chunk": metadata.get('chunk_index', 0) + 1,
                "total_chunks": metadata.get('total_chunks', 1),
                "position_percent": metadata.get('position_percent', 0),
                "content": content_preview,
                "relevance_score": round(relevance_score, 4),
                "chunk_length": len(content)
            })
        
        return sources
    
    def query(
        self, 
        question: str, 
        top_k: int = 4,
        answer_type: str = "default",
        filters: Optional[Dict] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Query the RAG system with advanced features.
        
        Args:
            question: User's question
            top_k: Number of relevant chunks to retrieve
            answer_type: Type of answer to generate (default, summary, detailed, etc.)
            filters: Optional metadata filters
            session_id: Optional conversation session ID for context
            user_id: Optional user identifier for query logging
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # ─── Check cache first (exact + fuzzy/typo matching) ─────────
        cached = query_cache.get(question, answer_type)
        if cached:
            # Cache hit — return instantly without LLM call
            cached["question"] = question  # Use the actual question asked
            
            # Still log to conversation history
            if session_id and settings.enable_conversation_history:
                conversation_history.add_message(session_id, "user", question, user_id=user_id)
                conversation_history.add_message(
                    session_id, "assistant", cached["answer"],
                    metadata={"sources": cached["sources"], "answer_type": answer_type, "cache_hit": True},
                    user_id=user_id
                )
            
            return cached
        
        # ─── Cache miss — proceed with full RAG pipeline ──────────
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
                conversation_history.add_message(session_id, "user", question, user_id=user_id)
                conversation_history.add_message(session_id, "assistant", no_docs_response["answer"], user_id=user_id)
            
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
        
        retrieval_metadata = {
            "total_sources": len(sources),
            "hybrid_search_used": settings.enable_hybrid_search,
            "reranking_used": settings.enable_reranking,
            "filters_applied": filters is not None,
            "cache_hit": False
        }
        
        response = {
            "question": question,
            "answer": answer,
            "sources": sources,
            "answer_type": answer_type,
            "retrieval_metadata": retrieval_metadata
        }
        
        # ─── Store in cache for future lookups ────────────────────
        query_cache.put(
            question=question,
            answer=answer,
            sources=sources,
            answer_type=answer_type,
            metadata=retrieval_metadata
        )
        
        # Add to conversation history if session provided
        if session_id and settings.enable_conversation_history:
            conversation_history.add_message(
                session_id, 
                "user", 
                question,
                user_id=user_id
            )
            conversation_history.add_message(
                session_id, 
                "assistant", 
                answer,
                metadata={"sources": sources, "answer_type": answer_type},
                user_id=user_id
            )
        
        return response


# Global instance
rag_chain = RAGChain()
