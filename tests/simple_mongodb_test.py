import pymongo

# Connect to MongoDB
client = pymongo.MongoClient('mongodb+srv://vvai_admin:VVAI_admin12345@vectorvault.tbmppar.mongodb.net/?retryWrites=true&w=majority&appName=VectorVault')
db = client['vectorvault-mongo']

def main():
    try:
        # Print database name
        print(f"Connected to database: {db.name}")
        
        # List collections
        collections = db.list_collection_names()
        print(f"Collections: {collections}")
        
        # Count documents in the 'documents' collection
        doc_count = db.documents.count_documents({})
        print(f"Document count in 'documents' collection: {doc_count}")
        
        # Get a sample document
        if doc_count > 0:
            sample_doc = db.documents.find_one({})
            
            # Print document ID
            print(f"\nSample document ID: {sample_doc.get('_id')}")
            
            # Print metadata if available
            if 'metadata' in sample_doc:
                print(f"Metadata: {sample_doc.get('metadata')}")
            
            # Print text (truncated if too long)
            if 'text' in sample_doc:
                text = sample_doc.get('text', '')
                max_display_length = 300
                if len(text) > max_display_length:
                    display_text = text[:max_display_length] + "..."
                else:
                    display_text = text
                print(f"Text: {display_text}")
            
            # Check if document has an embedding vector
            if 'embedding' in sample_doc:
                embedding = sample_doc.get('embedding')
                print(f"Embedding exists: {True}")
                print(f"Embedding length: {len(embedding)}")
                print(f"Embedding type: {type(embedding)}")
        else:
            print("No documents found in the 'documents' collection")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 