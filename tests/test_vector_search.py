import pymongo
import numpy as np
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get API keys and configuration from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable is not set")
    sys.exit(1)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Configure OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Connect to MongoDB
client = pymongo.MongoClient('mongodb+srv://vvai_admin:VVAI_admin12345@vectorvault.tbmppar.mongodb.net/?retryWrites=true&w=majority&appName=VectorVault')
db = client['vectorvault-mongo']

def get_embedding(text: str) -> list:
    """
    Generate an embedding vector for the given text using OpenAI API.
    
    Args:
        text: The text to generate an embedding for
        
    Returns:
        A list containing the embedding vector
    """
    try:
        response = client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise ValueError(f"Failed to generate embedding: {str(e)}")

def vector_search(query: str, limit: int = 5):
    """
    Perform vector similarity search using MongoDB.
    
    Args:
        query: The search query text
        limit: Number of results to return (default: 5)
        
    Returns:
        List of matching documents with similarity scores
    """
    # Generate embedding for the query
    query_vector = get_embedding(query)
    
    # Build MongoDB search pipeline
    pipeline = [
        {
            "$search": {
                "index": "vector_index",
                "knnBeta": {
                    "vector": query_vector,
                    "path": "embedding",
                    "k": limit
                }
            }
        },
        {
            "$project": {
                "text": 1, 
                "metadata": 1,
                "score": {"$meta": "searchScore"}
            }
        }
    ]
    
    # Execute search
    results = list(db.documents.aggregate(pipeline))
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_vector_search.py 'your search query'")
        sys.exit(1)
    
    query = sys.argv[1]
    try:
        print(f"Searching for: '{query}'")
        results = vector_search(query)
        
        print(f"\nFound {len(results)} results:")
        for i, doc in enumerate(results):
            print(f"\n--- Result {i+1} (Score: {doc['score']:.4f}) ---")
            
            # Get metadata (if available)
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "Unknown source")
            
            # Print the text (truncated if too long)
            text = doc["text"]
            max_display_length = 300
            if len(text) > max_display_length:
                display_text = text[:max_display_length] + "..."
            else:
                display_text = text
                
            print(f"Source: {source}")
            print(f"Text: {display_text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 