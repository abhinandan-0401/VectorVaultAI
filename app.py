import os
import uuid
import json
import time
from openai import OpenAI
import faiss
import numpy as np
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small"
LLM = os.getenv("LLM") or "gpt-4o"

client = OpenAI(api_key=OPENAI_API_KEY)

# Configuration
EMBEDDING_DIM = 1536  # for OpenAI text-embedding-3-small
INDEX_FILE = "faiss_index.index"
METADATA_FILE = "document_metadata.json"  # New file to store document metadata

# Flask app
app = Flask(__name__)

# Document storage (FAISS only stores vectors, now with persistence)
doc_store = {}

# Load or initialize FAISS index
if os.path.exists(INDEX_FILE):
    try:
        index = faiss.read_index(INDEX_FILE)
        print(f"FAISS index loaded from disk with {index.ntotal} vectors.")
    except Exception as e:
        print(f"Error loading FAISS index: {str(e)}. Creating new index.")
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
else:
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    print("Initialized new FAISS index.")

# Load document metadata if exists
if os.path.exists(METADATA_FILE):
    try:
        with open(METADATA_FILE, 'r') as f:
            doc_store = json.load(f)
            # Convert string keys back to integers
            doc_store = {int(k): v for k, v in doc_store.items()}
        print(f"Loaded {len(doc_store)} documents from metadata file.")
    except Exception as e:
        print(f"Error loading document metadata: {str(e)}. Starting with empty store.")

# Embedding generator using OpenAI
def get_embedding(text):
    try:
        response = client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise ValueError(f"Failed to generate embedding: {str(e)}")

# Save document metadata to disk
def save_metadata():
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(doc_store, f)
        print(f"Saved {len(doc_store)} documents to metadata file.")
    except Exception as e:
        print(f"Error saving document metadata: {str(e)}")

# Validate document
def validate_document(doc_data):
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

# Add document endpoint
@app.route('/documents', methods=['POST'])
def add_document():
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
        faiss.write_index(index, INDEX_FILE)
        save_metadata()

        return jsonify({"message": "Document added", "id": doc_id}), 201
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Batch document addition endpoint
@app.route('/documents/batch', methods=['POST'])
def add_documents_batch():
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
            faiss.write_index(index, INDEX_FILE)
            save_metadata()
        
        return jsonify({
            "message": f"Processed {len(data)} documents. {success_count} added successfully.",
            "results": results
        }), 207  # 207 Multi-Status
        
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Search endpoint
@app.route('/search', methods=['GET'])
def search_documents():
    try:
        query = request.args.get("q") or request.args.get("query")
        top_n = request.args.get("n")
        
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
        query_vec = get_embedding(query).reshape(1, -1)
        distances, indices = index.search(query_vec, min(top_n, index.ntotal))

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx in doc_store:  # Check for -1 (FAISS no-match indicator)
                doc = doc_store[idx]
                results.append({
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "distance": float(distances[0][i])
                })

        return jsonify({
            "query": query, 
            "results": results,
            "total_results": len(results)
        }), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Health check
@app.route('/health', methods=['GET'])
def health_check():
    try:
        return jsonify({
            "status": "ok",
            "documents_indexed": index.ntotal,
            "documents_metadata": len(doc_store),
            "embedding_model": EMBEDDING_MODEL,
            "llm_model": LLM
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)