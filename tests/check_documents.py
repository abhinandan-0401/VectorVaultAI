import pymongo

# Connect to MongoDB
client = pymongo.MongoClient('mongodb+srv://vvai_admin:VVAI_admin12345@vectorvault.tbmppar.mongodb.net/?retryWrites=true&w=majority&appName=VectorVault')
db = client['vectorvault-mongo']

# Count documents
doc_count = db.documents.count_documents({})
print(f'Document count: {doc_count}')

# List collection names if available
collections = db.list_collection_names()
print(f'Collections in vector_db: {collections}')

# Show a sample document if any exist
if doc_count > 0:
    sample_doc = db.documents.find_one()
    print(f'Sample document: {sample_doc}')
else:
    print('No documents found in the collection.')