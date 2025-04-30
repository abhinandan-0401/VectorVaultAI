import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
import tempfile
from datetime import datetime

import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, g
from google.cloud import storage
from openai import OpenAI
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity

# Import custom modules
from mongodb import initialize_mongodb
from auth import init_auth, role_required, register_user, authenticate_user, get_current_user, get_current_user_id
from conversations import ConversationManager
from pdf_processor import PDFProcessor
from rag_processor import RAGProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration constants
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small"
LLM = os.getenv("LLM") or "gpt-4o"
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
ALLOWED_EXTENSIONS = {'pdf'}  # Only allow PDF uploads

# Initialize the OpenAI client
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable not set")
    raise ValueError("OPENAI_API_KEY environment variable must be set")

client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket = None
if GCS_BUCKET_NAME:
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    logger.info(f"Connected to GCS bucket: {GCS_BUCKET_NAME}")
else:
    logger.warning("GCS_BUCKET_NAME not set. PDF upload will not be available.")

# Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # Limit uploads to 100MB

# Initialize MongoDB
db = initialize_mongodb()

# Initialize Auth
init_auth(app, db)

# Initialize conversation manager
conversation_manager = ConversationManager(db)

# Initialize processors
pdf_processor = None
rag_processor = None

if GCS_BUCKET_NAME:
    pdf_processor = PDFProcessor(
        openai_api_key=OPENAI_API_KEY,
        embedding_model=EMBEDDING_MODEL,
        gcs_bucket_name=GCS_BUCKET_NAME,
        db=db
    )

rag_processor = RAGProcessor(
    openai_api_key=OPENAI_API_KEY,
    llm_model=LLM,
    db=db
)

def get_embedding(text: str) -> np.ndarray:
    """
    Generate an embedding vector for the given text using OpenAI API.
    
    Args:
        text: The text to generate an embedding for
        
    Returns:
        A numpy array containing the embedding vector
        
    Raises:
        ValueError: If embedding generation fails
    """
    try:
        response = client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise ValueError(f"Failed to generate embedding: {str(e)}")

def validate_document(doc_data: Dict[str, Any]) -> List[str]:
    """
    Validate a document before adding it to the index.
    
    Args:
        doc_data: Document data dictionary
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    text = doc_data.get("text") or doc_data.get("content")
    
    if not text:
        errors.append("Missing 'text' or 'content' field")
    elif len(text) < 10:
        errors.append("Document text is too short (min 10 characters)")
    
    metadata = doc_data.get("metadata")
    if metadata and not isinstance(metadata, dict):
        errors.append("Metadata must be a JSON object")
    
    return errors

def allowed_file(filename: str) -> bool:
    """
    Check if a file has an allowed extension.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if file has allowed extension, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/logo')
def get_logo():
    """Serve the app logo."""
    return send_file('app_logo.png', mimetype='image/png')

# Authentication routes
@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json(force=True)
        
        # Validate input
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        
        if not username or not password or not email:
            return jsonify({"error": "Username, password, and email are required"}), 400
        
        # Only admins can assign roles
        role = "reader"  # Default role
        
        # Check if user is admin and wants to assign a role
        user_id = get_current_user_id()
        if user_id:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            if user and user.get("role") == "admin" and "role" in data:
                role = data.get("role")
        
        # Register user
        user, error = register_user(db, username, password, email, role)
        
        if error:
            return jsonify({"error": error}), 400
        
        return jsonify({"message": "User registered successfully", "user": user}), 201
    
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json(force=True)
        
        # Validate input
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        # Authenticate user
        token, user, error = authenticate_user(db, username, password)
        
        if error:
            return jsonify({"error": error}), 401
        
        return jsonify({
            "token": token,
            "user": user
        }), 200
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route('/auth/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get the current user's information"""
    try:
        user = get_current_user(db)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user), 200
    
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({"error": f"Failed to get user: {str(e)}"}), 500

@app.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Revoke the current token"""
    try:
        jti = get_jwt()["jti"]
        db.revoked_tokens.insert_one({
            "jti": jti,
            "created_at": datetime.utcnow()
        })
        
        return jsonify({"message": "Successfully logged out"}), 200
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({"error": f"Failed to logout: {str(e)}"}), 500

# User management routes (admin only)
@app.route('/admin/users', methods=['GET'])
@role_required(["admin"])
def get_users():
    """Get all users (admin only)"""
    try:
        users = list(db.users.find({}, {
            "password": 0  # Exclude password
        }))
        
        # Convert ObjectId to string
        for user in users:
            user["id"] = str(user.pop("_id"))
            if "created_at" in user:
                user["created_at"] = user["created_at"].isoformat()
            if "last_login" in user and user["last_login"]:
                user["last_login"] = user["last_login"].isoformat()
        
        return jsonify(users), 200
    
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        return jsonify({"error": f"Failed to get users: {str(e)}"}), 500

@app.route('/admin/users', methods=['POST'])
@role_required(["admin"])
def create_user():
    """Create a new user (admin only)"""
    try:
        data = request.get_json(force=True)
        
        # Validate input
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        role = data.get("role", "reader")
        
        if not username or not password or not email:
            return jsonify({"error": "Username, password, and email are required"}), 400
        
        # Create user
        user, error = register_user(db, username, password, email, role)
        
        if error:
            return jsonify({"error": error}), 400
        
        return jsonify({"message": "User created successfully", "user": user}), 201
    
    except Exception as e:
        logger.error(f"Create user error: {str(e)}")
        return jsonify({"error": f"Failed to create user: {str(e)}"}), 500

@app.route('/admin/users/<user_id>', methods=['PUT'])
@role_required(["admin"])
def update_user(user_id):
    """Update a user (admin only)"""
    try:
        data = request.get_json(force=True)
        
        # Fields that can be updated
        update_fields = {}
        
        if "email" in data:
            update_fields["email"] = data["email"]
        
        if "role" in data:
            update_fields["role"] = data["role"]
        
        if "password" in data:
            import bcrypt
            update_fields["password"] = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt())
        
        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400
        
        # Update the user
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "User not found or no changes made"}), 404
        
        return jsonify({"message": "User updated successfully"}), 200
    
    except Exception as e:
        logger.error(f"Update user error: {str(e)}")
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500

@app.route('/admin/users/<user_id>', methods=['DELETE'])
@role_required(["admin"])
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        # Don't allow deleting yourself
        current_user_id = get_current_user_id()
        if current_user_id == user_id:
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        # Delete the user
        result = db.users.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({"message": "User deleted successfully"}), 200
    
    except Exception as e:
        logger.error(f"Delete user error: {str(e)}")
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500

# Conversation routes
@app.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get all conversations for the current user"""
    try:
        user_id = get_current_user_id()
        conversations = conversation_manager.get_user_conversations(user_id)
        
        return jsonify(conversations), 200
    
    except Exception as e:
        logger.error(f"Get conversation error: {str(e)}")
        return jsonify({"error": f"Failed to get conversation: {str(e)}"}), 500

@app.route('/conversations/<conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """Get a specific conversation by ID"""
    try:
        user_id = get_current_user_id()
        conversation = conversation_manager.get_conversation(conversation_id, user_id)
        
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        return jsonify(conversation), 200
    
    except Exception as e:
        logger.error(f"Get conversation error: {str(e)}")
        return jsonify({"error": f"Failed to get conversation: {str(e)}"}), 500

@app.route('/conversations/<conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        user_id = get_current_user_id()
        success = conversation_manager.delete_conversation(conversation_id, user_id)
        
        if not success:
            return jsonify({"error": "Conversation not found or could not be deleted"}), 404
        
        return jsonify({"message": "Conversation deleted successfully"}), 200
    
    except Exception as e:
        logger.error(f"Delete conversation error: {str(e)}")
        return jsonify({"error": f"Failed to delete conversation: {str(e)}"}), 500

# Document management routes
@app.route('/documents', methods=['POST'])
@role_required(["admin", "editor"])
def add_document():
    """
    Add a document to MongoDB.
    
    Request Body:
        JSON object with:
        - text or content: Document text
        - metadata (optional): Document metadata
        - id (optional): Custom document ID
        
    Returns:
        JSON response with document ID
    """
    try:
        data = request.get_json(force=True)
        
        # Validate input
        validation_errors = validate_document(data)
        if validation_errors:
            return jsonify({"errors": validation_errors}), 400
            
        text = data.get("text") or data.get("content")
        metadata = data.get("metadata", {})
        doc_id = data.get("id", str(uuid.uuid4()))
        user_id = get_current_user_id()

        # Create embedding
        embedding = get_embedding(text)
        
        # Store document in MongoDB
        document = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata,
            "user_id": user_id,
            "created_at": datetime.utcnow()
        }
        
        result = db.documents.insert_one(document)
        inserted_id = str(result.inserted_id)
        
        logger.info(f"Document added with ID: {inserted_id}")
        return jsonify({"message": "Document added", "id": inserted_id}), 201
    
    except ValueError as ve:
        logger.warning(f"Validation error: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error adding document: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/documents/pdf', methods=['POST'])
@role_required(["admin", "editor"])
def add_pdf_document():
    """
    Add a PDF document, process chunks, and store in MongoDB.
    
    Request Body:
        Multipart form data with:
        - file: PDF file
        - metadata (optional): JSON string with document metadata
        
    Returns:
        JSON response with processing results
    """
    # Check if PDF processor is initialized
    if not pdf_processor:
        if not GCS_BUCKET_NAME:
            return jsonify({"error": "GCS_BUCKET_NAME environment variable must be set for PDF processing"}), 500
        else:
            return jsonify({"error": "PDF processor is not initialized"}), 500
    
    try:
        # Check if the POST request has the file part
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        # If user does not select file, browser may submit an empty part without filename
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if file and allowed_file(file.filename):
            # Get metadata if provided
            additional_metadata = {}
            if 'metadata' in request.form:
                try:
                    additional_metadata = json.loads(request.form['metadata'])
                except:
                    logger.warning("Failed to parse metadata JSON, using empty metadata")
            
            # Get current user ID
            user_id = get_current_user_id()
            
            # Process the PDF
            file_content = file.read()
            filename = secure_filename(file.filename)
            
            # Process the PDF to get chunks and embeddings
            chunks_count, document_id = pdf_processor.process_pdf(
                file_content, 
                filename, 
                user_id=user_id
            )
            
            # Update PDF document metadata
            if additional_metadata:
                db.pdf_documents.update_one(
                    {"document_id": document_id},
                    {"$set": {"metadata": additional_metadata}}
                )
            
            logger.info(f"PDF document {filename} processed and added with {chunks_count} chunks")
            return jsonify({
                "message": f"PDF document processed with {chunks_count} chunks",
                "document_name": filename,
                "document_id": document_id,
                "chunks_count": chunks_count
            }), 201
        else:
            return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
    
    except Exception as e:
        logger.error(f"Error processing PDF document: {str(e)}")
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500

@app.route('/documents/batch', methods=['POST'])
@role_required(["admin", "editor"])
def add_documents_batch():
    """
    Add multiple documents in batch to MongoDB.
    
    Request Body:
        JSON array of document objects
        
    Returns:
        JSON response with processing results
    """
    try:
        data = request.get_json(force=True)
        
        if not isinstance(data, list):
            return jsonify({"error": "Expected a JSON array of documents"}), 400
        
        if len(data) > 100:
            return jsonify({"error": "Batch size limited to 100 documents"}), 400
            
        results = []
        success_count = 0
        user_id = get_current_user_id()
        
        # Process each document
        for doc in data:
            # Validate document
            validation_errors = validate_document(doc)
            
            if validation_errors:
                results.append({
                    "status": "error",
                    "errors": validation_errors
                })
                continue
                
            text = doc.get("text") or doc.get("content")
            metadata = doc.get("metadata", {})
            
            try:
                # Generate embedding
                embedding = get_embedding(text)
                
                # Store document in MongoDB
                document = {
                    "text": text,
                    "embedding": embedding,
                    "metadata": metadata,
                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                }
                
                result = db.documents.insert_one(document)
                doc_id = str(result.inserted_id)
                
                results.append({
                    "status": "success",
                    "id": doc_id
                })
                
                success_count += 1
            except Exception as e:
                logger.error(f"Error processing document in batch: {str(e)}")
                results.append({
                    "status": "error",
                    "message": str(e)
                })
        
        logger.info(f"Batch processed: {len(data)} documents, {success_count} added successfully.")
        return jsonify({
            "message": f"Processed {len(data)} documents. {success_count} added successfully.",
            "results": results
        }), 207  # 207 Multi-Status
        
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/search', methods=['GET'])
@role_required(["admin", "editor", "reader"])
def search_documents():
    """
    Search for documents by semantic similarity using MongoDB Vector Search.
    
    Query Parameters:
        q or query: Search query
        n (optional): Number of results to return (default: 5)
        group (optional): Group results by source (default: false)
        
    Returns:
        JSON response with search results
    """
    try:
        query = request.args.get("q") or request.args.get("query")
        top_n = request.args.get("n")
        group = request.args.get("group", "false").lower() == "true"
        
        if not query:
            return jsonify({"error": "Missing 'q' or 'query' parameter"}), 400
            
        # Validate and convert top_n
        try:
            top_n = int(top_n) if top_n else 5
            if top_n < 1 or top_n > 100:
                return jsonify({"error": "Parameter 'n' must be between 1 and 100"}), 400
        except ValueError:
            return jsonify({"error": "Parameter 'n' must be an integer"}), 400

        # Get user ID for optional filtering
        user_id = get_current_user_id()

        # Search using RAG processor's search function
        logger.info(f"Searching for: {query}")
        results = rag_processor.search(query, user_id=None, top_n=top_n)  
        # Note: We're not filtering by user_id to show all docs

        # Process results for output
        for result in results:
            # Clean metadata (remove sensitive data like GCS URIs)
            if "metadata" in result:
                display_metadata = {}
                for k, v in result["metadata"].items():
                    if k != "gcs_uri":  # Skip sensitive GCS URI data
                        display_metadata[k] = v
                result["metadata"] = display_metadata

        # Group results by source if requested
        if group and results:
            # Group documents by source
            grouped_results = {}
            for result in results:
                source = result["metadata"].get("source", "Unknown")
                
                if source not in grouped_results:
                    grouped_results[source] = {
                        "source": source,
                        "documents": [],
                        "count": 0,
                        "avg_score": 0
                    }
                
                grouped_results[source]["documents"].append(result)
                grouped_results[source]["count"] += 1
            
            # Calculate average score for each group
            for source in grouped_results:
                docs = grouped_results[source]["documents"]
                grouped_results[source]["avg_score"] = sum(doc["score"] for doc in docs) / len(docs)
            
            # Convert to list and sort by average score
            groups = list(grouped_results.values())
            groups.sort(key=lambda x: x["avg_score"], reverse=True)
            
            response_data = {
                "query": query,
                "groups": groups,
                "total_results": len(results),
                "total_groups": len(groups)
            }
        else:
            response_data = {
                "query": query,
                "results": results,
                "total_results": len(results)
            }

        logger.info(f"Search for '{query}' returned {len(results)} results.")
        return jsonify(response_data), 200
    
    except ValueError as ve:
        logger.warning(f"Search validation error: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/vaultgpt', methods=['POST'])
@role_required(["admin", "editor", "reader"])
def query_vaultgpt():
    """
    Query VaultGPT for a response using RAG with conversation history.
    
    Request Body:
        JSON object with:
        - query: User query
        - conversation_id (optional): ID of ongoing conversation
        - custom_prompt (optional): Custom prompt template
        - top_n (optional): Number of documents to retrieve
        
    Returns:
        JSON response with answer and retrieved documents
    """
    try:
        # Check if RAG processor is initialized
        if not rag_processor:
            return jsonify({"error": "RAG processor is not initialized"}), 500
        
        data = request.get_json(force=True)
        
        # Get query
        query = data.get("query")
        if not query:
            return jsonify({"error": "Missing 'query' field"}), 400
        
        # Get optional parameters
        conversation_id = data.get("conversation_id")
        custom_prompt = data.get("custom_prompt")
        top_n = data.get("top_n", 5)
        user_id = get_current_user_id()
        
        # Validate top_n
        try:
            top_n = int(top_n)
            if top_n < 1 or top_n > 20:
                return jsonify({"error": "Parameter 'top_n' must be between 1 and 20"}), 400
        except ValueError:
            return jsonify({"error": "Parameter 'top_n' must be an integer"}), 400
        
        # Get conversation history if ID provided
        conversation_history = []
        if conversation_id and user_id:
            conversation = conversation_manager.get_conversation(conversation_id, user_id)
            if conversation:
                conversation_history = conversation.get("messages", [])
        
        # Generate RAG response
        logger.info(f"VaultGPT query: {query}")
        response = rag_processor.generate_response(
            query=query,
            conversation_history=conversation_history,
            custom_prompt=custom_prompt,
            top_n=top_n,
            user_id=None  # Not filtering by user_id to get all relevant docs
        )
        
        # If authenticated, save conversation
        if user_id:
            # Create user message
            user_message = {
                "role": "user",
                "content": query,
                "timestamp": datetime.utcnow()
            }
            
            # Create assistant message
            assistant_message = {
                "role": "assistant",
                "content": response.get("answer", ""),
                "sources": [
                    {
                        "doc_id": doc.get("id"),
                        "source": doc.get("metadata", {}).get("source", "Unknown"),
                        "page": doc.get("metadata", {}).get("page", "Unknown")
                    } for doc in response.get("documents", [])
                ],
                "timestamp": datetime.utcnow()
            }
            
            if conversation_id:
                # Update existing conversation
                updated = conversation_manager.add_messages(
                    conversation_id, 
                    user_id, 
                    user_message, 
                    assistant_message
                )
                
                if not updated:
                    logger.warning(f"Failed to update conversation {conversation_id}")
            else:
                # Create new conversation
                new_title = query[:50] + "..." if len(query) > 50 else query
                conversation_id = conversation_manager.create_conversation(
                    user_id, 
                    new_title, 
                    user_message, 
                    assistant_message
                )
            
            # Add conversation_id to response
            if conversation_id:
                response["conversation_id"] = conversation_id
        
        logger.info(f"VaultGPT response generated for query: {query}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error in VaultGPT: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Count documents
        document_count = db.documents.count_documents({})
        
        # Count unique sources
        pipeline = [
            {"$group": {"_id": "$metadata.source"}},
            {"$count": "unique_sources"}
        ]
        unique_sources_result = list(db.documents.aggregate(pipeline))
        unique_sources = unique_sources_result[0]["unique_sources"] if unique_sources_result else 0
        
        # Count PDF documents
        pdf_count = db.pdf_documents.count_documents({})
        
        # Get system info
        storage_info = {
            "type": "MongoDB Atlas + GCS" if GCS_BUCKET_NAME else "MongoDB Atlas",
            "pdf_storage": GCS_BUCKET_NAME if GCS_BUCKET_NAME else "Not configured"
        }
        
        # Get features supported
        features = ["search", "batch_upload", "document_upload", "auth"]
        if pdf_processor:
            features.append("pdf_processing")
        if rag_processor:
            features.append("vaultgpt")
        
        return jsonify({
            "status": "ok",
            "mongodb_connected": True,
            "documents_indexed": document_count,
            "chunks_count": document_count,
            "unique_documents": unique_sources,
            "pdf_documents": pdf_count,
            "embedding_model": EMBEDDING_MODEL,
            "llm_model": LLM,
            "storage": storage_info,
            "app_name": "VectorVault-Pilot",
            "logo_url": request.url_root + "logo",
            "features": features
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)