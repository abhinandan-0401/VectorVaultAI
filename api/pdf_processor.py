"""
PDF Processing utilities for VectorVault
"""

import os
import uuid
import logging
from typing import Dict, List, Tuple, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from google.cloud import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles PDF document processing, chunking, and embedding generation."""
    
    def __init__(self, openai_api_key: str, embedding_model: str, gcs_bucket_name: str):
        """
        Initialize the PDF processor.
        
        Args:
            openai_api_key: OpenAI API key
            embedding_model: Name of the embedding model to use
            gcs_bucket_name: GCS bucket name for storage
        """
        self.openai_api_key = openai_api_key
        self.embedding_model = embedding_model
        self.gcs_bucket_name = gcs_bucket_name
        
        # Initialize GCS client
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(gcs_bucket_name)
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_api_key
        )
        
        # Initialize text splitter with smart chunking strategy
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def upload_pdf_to_gcs(self, file_content: bytes, original_filename: str) -> str:
        """
        Upload PDF file to Google Cloud Storage.
        
        Args:
            file_content: PDF file content in bytes
            original_filename: Original filename
            
        Returns:
            GCS URI of the uploaded file
        """
        # Generate unique filename
        file_uuid = str(uuid.uuid4())
        safe_filename = original_filename.replace(" ", "_").lower()
        gcs_filename = f"pdfs/{file_uuid}/{safe_filename}"
        
        # Upload to GCS
        blob = self.bucket.blob(gcs_filename)
        blob.upload_from_string(file_content, content_type="application/pdf")
        
        gcs_uri = f"gs://{self.gcs_bucket_name}/{gcs_filename}"
        logger.info(f"Uploaded PDF to GCS: {gcs_uri}")
        
        return gcs_uri
    
    def download_pdf_from_gcs(self, gcs_uri: str) -> str:
        """
        Download PDF from GCS to a temporary file.
        
        Args:
            gcs_uri: GCS URI of the PDF file
            
        Returns:
            Path to the local temporary file
        """
        # Parse GCS URI
        if gcs_uri.startswith("gs://"):
            gcs_uri = gcs_uri[5:]  # Remove 'gs://' prefix
        
        bucket_name, blob_name = gcs_uri.split("/", 1)
        
        # Download to temp file
        temp_file_path = f"/tmp/{os.path.basename(blob_name)}"
        blob = self.storage_client.bucket(bucket_name).blob(blob_name)
        blob.download_to_filename(temp_file_path)
        
        return temp_file_path
    
    def process_pdf(self, file_content: bytes, original_filename: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process a PDF file, create chunks, generate embeddings and metadata.
        
        Args:
            file_content: PDF file content in bytes
            original_filename: Original filename
            
        Returns:
            Tuple of (chunks with embeddings, chunks with metadata)
        """
        # Upload to GCS
        gcs_uri = self.upload_pdf_to_gcs(file_content, original_filename)
        
        # Save to temp file for processing
        temp_file_path = f"/tmp/{original_filename}"
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        
        # Use LangChain's PyPDFLoader to load and parse the PDF
        loader = PyPDFLoader(temp_file_path)
        documents = loader.load()
        
        # Split the documents into chunks
        chunks = self.text_splitter.split_documents(documents)
        
        # Create embeddings and metadata
        embedded_chunks = []
        chunk_metadata = []
        
        for i, chunk in enumerate(chunks):
            # Extract page number from chunk metadata
            page_num = chunk.metadata.get('page', 0) + 1  # LangChain uses 0-indexed pages
            
            # Generate embedding
            embedding = self.embeddings.embed_query(chunk.page_content)
            
            # Create metadata
            metadata = {
                "id": f"{uuid.uuid4()}",
                "text": chunk.page_content,
                "metadata": {
                    "source": original_filename,
                    "page": page_num,
                    "chunk_index": i,
                    "gcs_uri": gcs_uri,
                }
            }
            
            embedded_chunks.append({
                "id": metadata["id"],
                "embedding": embedding,
                "text": chunk.page_content,
            })
            
            chunk_metadata.append(metadata)
        
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        logger.info(f"Processed PDF {original_filename} into {len(chunks)} chunks")
        return embedded_chunks, chunk_metadata 