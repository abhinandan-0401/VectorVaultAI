"""
RAG (Retrieval Augmented Generation) Processing for VectorVault
"""

import logging
import json
from typing import Dict, List, Any, Optional

import numpy as np
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.schema import Document
import faiss

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default prompts
DEFAULT_PROMPT = """You are VaultGPT, a helpful AI assistant that answers questions based on the provided document context.

CONTEXT INFORMATION:
{context}

QUESTION: {query}

Please provide a detailed, accurate answer based on the information in the context. If the context doesn't contain enough information to answer the question fully, acknowledge what you don't know and provide the best answer possible with the available information. If the answer isn't in the context at all, simply state that you don't have that information.

Your answer should:
1. Be comprehensive and directly address the question
2. Include relevant details from the context
3. Be well-structured and clearly presented
4. Cite specific sources from the context when appropriate
5. Avoid adding information not supported by the context

ANSWER:"""

class RAGProcessor:
    """Handles RAG operations for VectorVault."""
    
    def __init__(self, openai_api_key: str, llm_model: str, index: faiss.Index, doc_store: Dict[int, Dict[str, Any]]):
        """
        Initialize the RAG processor.
        
        Args:
            openai_api_key: OpenAI API key
            llm_model: Name of the LLM model
            index: FAISS index
            doc_store: Document store mapping
        """
        self.openai_api_key = openai_api_key
        self.llm_model = llm_model
        self.index = index
        self.doc_store = doc_store
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=llm_model,
            openai_api_key=openai_api_key,
            temperature=0.1,  # Low temperature for factual responses
        )
        
        # Initialize default prompt
        self.default_prompt = PromptTemplate(
            input_variables=["context", "query"],
            template=DEFAULT_PROMPT
        )
    
    def search(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using the FAISS index.
        
        Args:
            query: The search query
            top_n: Number of top results to return
            
        Returns:
            List of search results with metadata
        """
        from app import get_embedding  # Import here to avoid circular imports
        
        # Embed query
        query_vec = get_embedding(query).reshape(1, -1)
        
        # Search
        distances, indices = self.index.search(query_vec, min(top_n, self.index.ntotal))
        
        # Process results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx in self.doc_store:  # Check for -1 (FAISS no-match indicator)
                doc = self.doc_store[idx]
                results.append({
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "distance": float(distances[0][i]),
                    "score": 1.0 - float(distances[0][i])  # Convert distance to similarity score
                })
        
        return results
    
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
    
    def generate_response(self, query: str, custom_prompt: Optional[str] = None, top_n: int = 5) -> Dict[str, Any]:
        """
        Generate a response using RAG.
        
        Args:
            query: The user query
            custom_prompt: Optional custom prompt
            top_n: Number of documents to retrieve
            
        Returns:
            Response with answer and retrieved documents
        """
        # Search for relevant documents
        documents = self.search(query, top_n=top_n)
        
        if not documents:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "documents": [],
                "query": query
            }
        
        # Prepare context
        context = self._prepare_context(documents)
        
        # Setup prompt
        if custom_prompt:
            prompt = PromptTemplate(
                input_variables=["context", "query"],
                template=custom_prompt
            )
        else:
            prompt = self.default_prompt
        
        # Generate answer
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(context=context, query=query)
        
        # Clean up documents for response (remove embeddings, etc.)
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