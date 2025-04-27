#!/usr/bin/env python3
"""
VectorVault API - A document search engine using vector embeddings
"""

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
import tempfile

import faiss
import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from google.cloud import storage
from openai import OpenAI
from werkzeug.utils import secure_filename

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
EMBEDDING_DIM = 1536  # for OpenAI text-embedding-3-small
INDEX_FILE = "faiss_index.index"
METADATA_FILE = "document_metadata.json"
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
    logger.warning("GCS_BUCKET_NAME not set. Using local file storage only.")

# Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # Limit uploads to 100MB

# Document storage (FAISS only stores vectors, we need to keep metadata separately)
doc_store: Dict[int, Dict[str, Any]] = {}

# Initialize processors
pdf_processor = None
rag_processor = None


def load_index() -> None:
    """
    Load or initialize FAISS index and document metadata from GCS or local storage.
    
    Sets global variables 'index' and 'doc_store'.
    """
    global index, doc_store, pdf_processor, rag_processor
    
    # Try to load from GCS first if configured
    if bucket:
        index_blob = bucket.blob(INDEX_FILE)
        metadata_blob = bucket.blob(METADATA_FILE)
        
        # Check if index exists in GCS
        if index_blob.exists():
            try:
                # Download index from GCS to local temp file
                index_blob.download_to_filename(INDEX_FILE)
                logger.info(f"Downloaded FAISS index from GCS bucket {GCS_BUCKET_NAME}")
                
                # Load index from local file
                index = faiss.read_index(INDEX_FILE)
                logger.info(f"FAISS index loaded with {index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Error loading FAISS index from GCS: {str(e)}. Creating new index.")
                index = faiss.IndexFlatL2(EMBEDDING_DIM)
        else:
            logger.info(f"No FAISS index found in GCS bucket {GCS_BUCKET_NAME}. Creating new index.")
            index = faiss.IndexFlatL2(EMBEDDING_DIM)
        
        # Check if metadata exists in GCS
        if metadata_blob.exists():
            try:
                # Download metadata from GCS to local temp file
                metadata_blob.download_to_filename(METADATA_FILE)
                logger.info(f"Downloaded document metadata from GCS bucket {GCS_BUCKET_NAME}")
                
                # Load metadata from local file
                with open(METADATA_FILE, 'r') as f:
                    doc_store = json.load(f)
                    # Convert string keys back to integers
                    doc_store = {int(k): v for k, v in doc_store.items()}
                logger.info(f"Loaded {len(doc_store)} documents from metadata file.")
            except Exception as e:
                logger.error(f"Error loading document metadata from GCS: {str(e)}. Starting with empty store.")
        else:
            logger.info(f"No document metadata found in GCS bucket {GCS_BUCKET_NAME}. Starting with empty store.")
    else:
        # Fall back to local files if GCS not configured
        if os.path.exists(INDEX_FILE):
            try:
                index = faiss.read_index(INDEX_FILE)
                logger.info(f"FAISS index loaded from local disk with {index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Error loading local FAISS index: {str(e)}. Creating new index.")
                index = faiss.IndexFlatL2(EMBEDDING_DIM)
        else:
            index = faiss.IndexFlatL2(EMBEDDING_DIM)
            logger.info("Initialized new FAISS index.")

        # Load document metadata if exists locally
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r') as f:
                    doc_store = json.load(f)
                    # Convert string keys back to integers
                    doc_store = {int(k): v for k, v in doc_store.items()}
                logger.info(f"Loaded {len(doc_store)} documents from local metadata file.")
            except Exception as e:
                logger.error(f"Error loading local document metadata: {str(e)}. Starting with empty store.")
    
    # Initialize the PDF processor if GCS is configured
    if GCS_BUCKET_NAME:
        pdf_processor = PDFProcessor(
            openai_api_key=OPENAI_API_KEY,
            embedding_model=EMBEDDING_MODEL,
            gcs_bucket_name=GCS_BUCKET_NAME
        )
    
    # Initialize the RAG processor
    rag_processor = RAGProcessor(
        openai_api_key=OPENAI_API_KEY,
        llm_model=LLM,
        index=index,
        doc_store=doc_store
    )


# Initialize index and doc_store
load_index()


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


def save_data() -> None:
    """
    Save document metadata and index to disk and GCS if configured.
    """
    try:
        # Save metadata locally first
        with open(METADATA_FILE, 'w') as f:
            json.dump(doc_store, f)
        logger.info(f"Saved {len(doc_store)} documents to local metadata file.")
        
        # Save index locally
        faiss.write_index(index, INDEX_FILE)
        logger.info(f"Saved FAISS index with {index.ntotal} vectors to local file.")
        
        # Upload to GCS if configured
        if bucket:
            # Upload metadata
            metadata_blob = bucket.blob(METADATA_FILE)
            metadata_blob.upload_from_filename(METADATA_FILE)
            logger.info(f"Uploaded document metadata to GCS bucket {GCS_BUCKET_NAME}")
            
            # Upload index
            index_blob = bucket.blob(INDEX_FILE)
            index_blob.upload_from_filename(INDEX_FILE)
            logger.info(f"Uploaded FAISS index to GCS bucket {GCS_BUCKET_NAME}")
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")


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


@app.route('/documents', methods=['POST'])
def add_document():
    """
    Add a document to the index.
    
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

        # Create embedding and add to index
        embedding = get_embedding(text)
        index.add(np.array([embedding]))
        
        # Store document reference
        idx = index.ntotal - 1
        doc_store[idx] = {
            "id": doc_id,
            "text": text,
            "metadata": metadata,
            "added_at": time.time()
        }

        # Persist data
        save_data()

        logger.info(f"Document added with ID: {doc_id}")
        return jsonify({"message": "Document added", "id": doc_id}), 201
    
    except ValueError as ve:
        logger.warning(f"Validation error: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error adding document: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/documents/pdf', methods=['POST'])
def add_pdf_document():
    """
    Add a PDF document to the index.
    
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
            
            # Process the PDF
            file_content = file.read()
            filename = secure_filename(file.filename)
            
            # Process the PDF to get chunks and embeddings
            embedded_chunks, chunk_metadata = pdf_processor.process_pdf(file_content, filename)
            
            # Add additional metadata if provided
            for chunk in chunk_metadata:
                chunk["metadata"].update(additional_metadata)
            
            # Add chunks to index
            embeddings = np.array([chunk["embedding"] for chunk in embedded_chunks])
            index.add(embeddings)
            
            # Store document references
            start_idx = index.ntotal - len(embedded_chunks)
            for i, chunk in enumerate(chunk_metadata):
                doc_store[start_idx + i] = {
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                    "added_at": time.time()
                }
            
            # Persist data
            save_data()
            
            logger.info(f"PDF document {filename} processed and added with {len(embedded_chunks)} chunks")
            return jsonify({
                "message": f"PDF document processed with {len(embedded_chunks)} chunks",
                "document_name": filename,
                "chunks_count": len(embedded_chunks)
            }), 201
        else:
            return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
    
    except Exception as e:
        logger.error(f"Error processing PDF document: {str(e)}")
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500


@app.route('/documents/batch', methods=['POST'])
def add_documents_batch():
    """
    Add multiple documents in batch.
    
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
        
        # Process each document
        embeddings = []
        valid_docs = []
        
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
            doc_id = doc.get("id", str(uuid.uuid4()))
            
            try:
                # Generate embedding
                embedding = get_embedding(text)
                embeddings.append(embedding)
                valid_docs.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": metadata,
                    "added_at": time.time()
                })
                
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
        
        # Add all valid embeddings at once
        if embeddings:
            index.add(np.array(embeddings))
            
            # Store document references
            start_idx = index.ntotal - len(embeddings)
            for i, doc in enumerate(valid_docs):
                doc_store[start_idx + i] = doc
            
            # Persist data
            save_data()
        
        logger.info(f"Batch processed: {len(data)} documents, {success_count} added successfully.")
        return jsonify({
            "message": f"Processed {len(data)} documents. {success_count} added successfully.",
            "results": results
        }), 207  # 207 Multi-Status
        
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/search', methods=['GET'])
def search_documents():
    """
    Search for documents by semantic similarity.
    
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

        # Embed query
        logger.info(f"Searching for: {query}")
        query_vec = get_embedding(query).reshape(1, -1)
        distances, indices = index.search(query_vec, min(top_n, index.ntotal))

        # Process basic results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx in doc_store:  # Check for -1 (FAISS no-match indicator)
                doc = doc_store[idx]
                
                # Clean metadata (remove sensitive data like GCS URIs)
                display_metadata = {}
                if "metadata" in doc:
                    for k, v in doc["metadata"].items():
                        if k != "gcs_uri":  # Skip sensitive GCS URI data
                            display_metadata[k] = v
                
                results.append({
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": display_metadata,
                    "distance": float(distances[0][i]),
                    "score": 1.0 - float(distances[0][i])  # Convert distance to similarity score
                })

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
def query_vaultgpt():
    """
    Query VaultGPT for a response using RAG (Retrieval Augmented Generation).
    
    Request Body:
        JSON object with:
        - query: User query
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
        custom_prompt = data.get("custom_prompt")
        top_n = data.get("top_n", 5)
        
        # Validate top_n
        try:
            top_n = int(top_n)
            if top_n < 1 or top_n > 20:
                return jsonify({"error": "Parameter 'top_n' must be between 1 and 20"}), 400
        except ValueError:
            return jsonify({"error": "Parameter 'top_n' must be an integer"}), 400
        
        # Generate RAG response
        logger.info(f"VaultGPT query: {query}")
        response = rag_processor.generate_response(
            query=query,
            custom_prompt=custom_prompt,
            top_n=top_n
        )
        
        logger.info(f"VaultGPT response generated for query: {query}")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error in VaultGPT: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        storage_info = {
            "type": "Google Cloud Storage" if GCS_BUCKET_NAME else "Local",
            "location": GCS_BUCKET_NAME if GCS_BUCKET_NAME else "local filesystem"
        }
        
        # Count unique document sources
        unique_sources = set()
        for doc_id, doc in doc_store.items():
            if "metadata" in doc and "source" in doc["metadata"]:
                unique_sources.add(doc["metadata"]["source"])
        
        # Get features supported
        features = ["search", "batch_upload", "document_upload"]
        if pdf_processor:
            features.append("pdf_processing")
        if rag_processor:
            features.append("vaultgpt")
        
        return jsonify({
            "status": "ok",
            "documents_indexed": index.ntotal,
            "chunks_count": index.ntotal,
            "unique_documents": len(unique_sources),
            "documents_metadata": len(doc_store),
            "embedding_model": EMBEDDING_MODEL,
            "llm_model": LLM,
            "storage": storage_info,
            "app_name": "VectorVault",
            "logo_url": request.url_root + "logo",
            "features": features
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)