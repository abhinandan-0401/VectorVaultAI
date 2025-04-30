# api/rag_processor.py - Enhanced with LangChain conversation memory
"""
RAG (Retrieval Augmented Generation) Processing for VectorVault
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default system prompt
SYSTEM_PROMPT = """You are VaultGPT, a helpful AI assistant that answers questions based on the provided document context.
You provide detailed, accurate answers based on the information in the context. 
If the context doesn't contain enough information to answer the question fully, acknowledge what you don't know.
Your answers should:
1. Be comprehensive and directly address the question
2. Include relevant details from the context
3. Be well-structured and clearly presented
4. Cite specific sources from the context when appropriate
5. Avoid adding information not supported by the context"""

class RAGProcessor:
    """Handles RAG operations for VectorVault."""
    
    def __init__(self, openai_api_key: str, llm_model: str, db):
        """
        Initialize the RAG processor.
        
        Args:
            openai_api_key: OpenAI API key
            llm_model: Name of the LLM model
            db: MongoDB database connection
        """
        self.openai_api_key = openai_api_key
        self.llm_model = llm_model
        self.db = db
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=llm_model,
            openai_api_key=openai_api_key,
            temperature=0.1,  # Low temperature for factual responses
        )
        
        # Initialize chat prompt template with messages
        self.chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("CONTEXT INFORMATION:\n{context}\n\nQUESTION: {query}")
        ])
        
        # Initialize simple prompt template for single questions
        self.simple_prompt = PromptTemplate(
            input_variables=["context", "query"],
            template=f"{SYSTEM_PROMPT}\n\nCONTEXT INFORMATION:\n{{context}}\n\nQUESTION: {{query}}\n\nANSWER:"
        )
    
    def search(self, query: str, user_id: Optional[str] = None, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using MongoDB vector search.
        
        Args:
            query: The search query
            user_id: Optional user ID to filter results
            top_n: Number of top results to return
            
        Returns:
            List of search results with metadata
        """
        from app import get_embedding  # Import here to avoid circular imports
        
        # Embed query
        query_vec = get_embedding(query)

        # Convert NumPy array to Python list if needed
        query_vec_list = query_vec.tolist() if hasattr(query_vec, 'tolist') else query_vec
        
        # Build MongoDB search pipeline using $vectorSearch
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_vec_list,
                    "numCandidates": top_n * 10,  # Fetch more candidates for better results
                    "limit": top_n
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "metadata": 1,
                    "score": {"$meta": "searchScore"}
                }
            }
        ]
        
        # Add user filter if provided
        if user_id:
            pipeline.insert(1, {"$match": {"user_id": user_id}})
        
        try:
            # Execute search
            results = list(self.db.documents.aggregate(pipeline))
            
            # Process results
            processed_results = []
            for doc in results:
                processed_results.append({
                    "id": str(doc["_id"]),
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": doc["score"]
                })
            
            return processed_results
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            
            # Fallback to regular search if vector search fails
            try:
                logger.info("Falling back to regular document search")
                fallback_results = list(self.db.documents.find(
                    {"user_id": user_id} if user_id else {},
                    {"text": 1, "metadata": 1}
                ).limit(top_n))
                
                processed_fallback = []
                for doc in fallback_results:
                    processed_fallback.append({
                        "id": str(doc["_id"]),
                        "text": doc["text"],
                        "metadata": doc["metadata"],
                        "score": 0.0  # No score for fallback results
                    })
                
                return processed_fallback
            except Exception as fallback_err:
                logger.error(f"Fallback search error: {str(fallback_err)}")
                return []
    
    def _prepare_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Prepare the context from the retrieved documents.
        
        Args:
            documents: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Group documents by source
        docs_by_source = {}
        for i, doc in enumerate(documents):
            source = doc["metadata"].get("source", "Unknown")
            page = doc["metadata"].get("page", "Unknown")
            
            if source not in docs_by_source:
                docs_by_source[source] = []
            
            docs_by_source[source].append({
                "text": doc["text"],
                "page": page,
                "score": doc.get("score", 0.0),
                "index": i + 1  # 1-indexed for human readability
            })
        
        # Format context by source
        for source, docs in docs_by_source.items():
            # Add source header
            context_parts.append(f"SOURCE: {source}")
            
            # Add each document from this source
            for doc in docs:
                context_parts.append(f"[Document {doc['index']}, Page {doc['page']}, Relevance: {doc['score']:.2f}]\n{doc['text']}\n")
            
            context_parts.append("")  # Add separator between sources
        
        return "\n".join(context_parts)
    
    def _convert_to_langchain_messages(self, history: List[Dict[str, Any]]) -> List[Any]:
        """
        Convert conversation history to LangChain message format.
        
        Args:
            history: List of message dictionaries with role and content
            
        Returns:
            List of LangChain message objects
        """
        if not history:
            return []
            
        messages = []
        
        # Only use the last 10 messages to keep context manageable
        recent_history = history[-10:] if len(history) > 10 else history
        
        for msg in recent_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
                
        return messages
    
    def generate_response(self, query: str, conversation_history: Optional[List[Dict[str, Any]]] = None, 
                          custom_prompt: Optional[str] = None, top_n: int = 5,
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response using RAG with LangChain conversation memory.
        
        Args:
            query: The user query
            conversation_history: Optional list of previous messages
            custom_prompt: Optional custom prompt
            top_n: Number of documents to retrieve
            user_id: Optional user ID to filter search results
            
        Returns:
            Response with answer and retrieved documents
        """
        # Search for relevant documents
        documents = self.search(query, user_id=user_id, top_n=top_n)
        
        if not documents:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "documents": [],
                "query": query
            }
        
        # Prepare context
        context = self._prepare_context(documents)
        
        # Generate answer based on whether we have conversation history
        if conversation_history:
            # Convert history to LangChain messages
            chat_history = self._convert_to_langchain_messages(conversation_history)
            
            # Use a ConversationBufferMemory to manage history
            memory = ConversationBufferMemory(
                memory_key="chat_history", 
                return_messages=True,
                chat_memory=chat_history
            )
            
            # Create a custom chat prompt if provided
            prompt = self.chat_prompt
            if custom_prompt:
                prompt = ChatPromptTemplate.from_messages([
                    SystemMessagePromptTemplate.from_template(custom_prompt),
                    MessagesPlaceholder(variable_name="chat_history"),
                    HumanMessagePromptTemplate.from_template("CONTEXT INFORMATION:\n{context}\n\nQUESTION: {query}")
                ])
            
            # Create chain with conversation memory
            chain = LLMChain(
                llm=self.llm,
                prompt=prompt,
                verbose=True,
                memory=memory
            )
            
            # Run the chain
            response = chain.predict(context=context, query=query)
            
        else:
            # Use simple prompt for one-off questions
            if custom_prompt:
                simple_prompt = PromptTemplate(
                    input_variables=["context", "query"],
                    template=custom_prompt
                )
            else:
                simple_prompt = self.simple_prompt
                
            # Create standard chain
            chain = LLMChain(llm=self.llm, prompt=simple_prompt)
            response = chain.run(context=context, query=query)
        
        # Clean up documents for response
        clean_docs = []
        for doc in documents:
            clean_doc = {
                "id": doc["id"],
                "text": doc["text"],
                "metadata": {
                    "source": doc["metadata"].get("source", "Unknown"),
                    "page": doc["metadata"].get("page", "Unknown")
                },
                "score": doc.get("score", 0.0)
            }
            clean_docs.append(clean_doc)
        
        return {
            "answer": response,
            "documents": clean_docs,
            "query": query
        }