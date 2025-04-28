import pymongo
import sys
import pprint

# Connect to MongoDB Atlas
client = pymongo.MongoClient('mongodb+srv://vvai_admin:VVAI_admin12345@vectorvault.tbmppar.mongodb.net/?retryWrites=true&w=majority&appName=VectorVault')
db = client['vectorvault-mongo']

def check_indexes():
    """
    Check available indexes in the documents collection.
    """
    print("Checking available indexes...")
    try:
        indexes = list(db.documents.list_indexes())
        print(f"Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx['name']}: {idx['key']}")
        return indexes
    except Exception as e:
        print(f"Error checking indexes: {str(e)}")
        return []

def get_sample_document_embedding():
    """
    Get an embedding from an existing document in the database to use for testing.
    
    Returns:
        An embedding vector from an existing document
    """
    # Get the first document
    sample_doc = db.documents.find_one({}, {"embedding": 1})
    
    if not sample_doc or "embedding" not in sample_doc:
        print("No documents with embeddings found in the database")
        return None
        
    print(f"Using embedding from document ID: {sample_doc['_id']}")
    return sample_doc["embedding"]

def vector_search(embedding, limit=5):
    """
    Perform vector similarity search using MongoDB.
    
    Args:
        embedding: The embedding vector to search with
        limit: Number of results to return (default: 5)
        
    Returns:
        List of matching documents with similarity scores
    """
    # Build MongoDB search pipeline
    pipeline = [
        {
            "$search": {
                "index": "vector_index",
                "knnBeta": {
                    "vector": embedding,
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
    try:
        results = list(db.documents.aggregate(pipeline))
        return results
    except Exception as e:
        print(f"Error executing vector search: {str(e)}")
        return []

def find_documents_by_text_sample(limit=5):
    """
    An alternative to vector search - find documents by text query.
    """
    try:
        # Get a few documents using a simple find
        print(f"Performing regular MongoDB find operation (limit: {limit})...")
        results = list(db.documents.find({}, {"text": 1, "metadata": 1}).limit(limit))
        return results
    except Exception as e:
        print(f"Error finding documents: {str(e)}")
        return []

def main():
    try:
        # Check available indexes first
        indexes = check_indexes()
        
        # Get a sample embedding from the database
        print("\nGetting a sample embedding from the database...")
        embedding = get_sample_document_embedding()
        
        if not embedding:
            print("Cannot perform vector search: no embedding found")
            return
            
        # Run the vector search
        limit = 5
        print(f"\nPerforming vector search to find {limit} similar documents...")
        results = vector_search(embedding, limit)
        
        if results:
            print(f"\nFound {len(results)} results via vector search:")
            for i, doc in enumerate(results):
                print(f"\n--- Result {i+1} (Score: {doc.get('score', 0):.4f}) ---")
                
                # Get metadata (if available)
                metadata = doc.get("metadata", {})
                source = metadata.get("source", "Unknown source")
                page = metadata.get("page", "Unknown page")
                
                # Print the text (truncated if too long)
                text = doc.get("text", "")
                max_display_length = 300
                if len(text) > max_display_length:
                    display_text = text[:max_display_length] + "..."
                else:
                    display_text = text
                    
                print(f"Source: {source} (Page: {page})")
                print(f"Text: {display_text}")
        else:
            print("\nVector search returned no results. Trying regular document find...")
            regular_results = find_documents_by_text_sample(limit)
            
            if regular_results:
                print(f"\nFound {len(regular_results)} documents using regular find:")
                for i, doc in enumerate(regular_results):
                    print(f"\n--- Regular Result {i+1} ---")
                    
                    # Get metadata (if available)
                    metadata = doc.get("metadata", {})
                    source = metadata.get("source", "Unknown source")
                    page = metadata.get("page", "Unknown page")
                    
                    # Print the text (truncated if too long)
                    text = doc.get("text", "")
                    max_display_length = 300
                    if len(text) > max_display_length:
                        display_text = text[:max_display_length] + "..."
                    else:
                        display_text = text
                        
                    print(f"Source: {source} (Page: {page})")
                    print(f"Text: {display_text}")
            else:
                print("No documents found using either method.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 