from pymongo import MongoClient
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_mongodb_client():
    """Get MongoDB client using environment variables"""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI environment variable not set")
    
    try:
        client = MongoClient(mongodb_uri)
        # Force a connection to verify
        client.admin.command('ping')
        logger.info("Connected to MongoDB Atlas successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise

def setup_collections(db):
    """Setup necessary collections and indexes"""
    try:
        # Documents collection (for vector search)
        if "documents" not in db.list_collection_names():
            db.create_collection("documents")
            logger.info("Created 'documents' collection")
            
        # Create indexes for documents collection
        db.documents.create_index([("metadata.source", 1)])
        db.documents.create_index([("metadata.document_id", 1)])
        db.documents.create_index([("user_id", 1)])
        logger.info("Created standard indexes for 'documents' collection")
        
        # Create vector search index
        try:
            vector_index_exists = False
            # Check if vector index already exists
            indexes = db.command({"listSearchIndexes": "documents"}).get("indexes", [])
            for index in indexes:
                if index.get("name") == "vector_index":
                    vector_index_exists = True
                    break
                    
            if not vector_index_exists:
                db.command({
                    "createSearchIndex": "documents",
                    "definition": {
                        "name": "vector_index",
                        "mappings": {
                            "dynamic": True,
                            "fields": {
                                "embedding": {
                                    "type": "knnVector",
                                    "dimensions": 1536,
                                    "similarity": "cosine"
                                }
                            }
                        }
                    }
                })
                logger.info("Created vector search index for 'documents' collection")
        except Exception as e:
            logger.error(f"Error creating vector search index: {str(e)}")
            logger.info("Note: Vector search requires MongoDB Atlas with Atlas Search enabled.")
            # Continue anyway, as this might be due to lack of Atlas Search support
        
        # PDF documents collection (metadata about whole PDFs)
        if "pdf_documents" not in db.list_collection_names():
            db.create_collection("pdf_documents")
            logger.info("Created 'pdf_documents' collection")
        db.pdf_documents.create_index([("document_id", 1)], unique=True)
        db.pdf_documents.create_index([("user_id", 1)])
        logger.info("Created indexes for 'pdf_documents' collection")
        
        # Users collection
        if "users" not in db.list_collection_names():
            db.create_collection("users")
            logger.info("Created 'users' collection")
        db.users.create_index([("username", 1)], unique=True)
        db.users.create_index([("email", 1)], unique=True)
        logger.info("Created indexes for 'users' collection")
        
        # Conversations collection
        if "conversations" not in db.list_collection_names():
            db.create_collection("conversations")
            logger.info("Created 'conversations' collection")
        db.conversations.create_index([("user_id", 1)])
        logger.info("Created indexes for 'conversations' collection")
        
        # Revoked tokens collection
        if "revoked_tokens" not in db.list_collection_names():
            db.create_collection("revoked_tokens")
            logger.info("Created 'revoked_tokens' collection")
        db.revoked_tokens.create_index([("jti", 1)], unique=True)
        db.revoked_tokens.create_index([("created_at", 1)], expireAfterSeconds=86400)  # 24 hours
        logger.info("Created indexes for 'revoked_tokens' collection")
        
        return True
    except Exception as e:
        logger.error(f"Error setting up MongoDB collections: {str(e)}")
        raise

def initialize_mongodb():
    """Initialize MongoDB connection and setup collections"""
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DATABASE", "vectorvault-mongo")
    
    logger.info(f"Connecting to MongoDB database: {database_name}")
    logger.info(f"Using MongoDB URI: {mongodb_uri.split('@')[1] if '@' in mongodb_uri else 'URI hidden for security'}")
    
    client = MongoClient(mongodb_uri)
    db = client[database_name]
    
    # List all databases in this cluster
    try:
        available_dbs = client.list_database_names()
        logger.info(f"Available databases: {available_dbs}")
    except Exception as e:
        logger.error(f"Could not list databases: {str(e)}")
    setup_collections(db)
    return db