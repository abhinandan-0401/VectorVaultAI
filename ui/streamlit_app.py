#!/usr/bin/env python3
"""
VectorVault UI - Streamlit interface for semantic document search
"""

import json
import logging
import os
import time
from io import StringIO
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
import streamlit as st

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:5000")
logger.info(f"Using API URL: {API_URL}")


def get_api_endpoint(endpoint: str) -> str:
    """
    Create a properly formatted API endpoint URL.
    
    Args:
        endpoint: The API endpoint path
        
    Returns:
        Full URL for the API endpoint
    """
    # Remove leading slash if present
    if endpoint.startswith('/'):
        endpoint = endpoint[1:]
    
    # If API_URL already ends with '/api', don't append the endpoint with '/api'
    if API_URL.endswith('/api'):
        base_url = API_URL
    else:
        base_url = API_URL
        
    return f"{base_url}/{endpoint}"


# Page config
st.set_page_config(
    page_title="VectorVault",
    page_icon="🧠",
    layout="wide",
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4B9FE1;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888888;
        font-style: italic;
        margin-top: 0px;
    }
    .success-box {
        padding: 1rem;
        background-color: #D5F5E3;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        padding: 1rem;
        background-color: #D6EAF8;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .query-input {
        border: 2px solid #4B9FE1;
        border-radius: 0.5rem;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def display_header():
    """Displays the application header with logo."""
    # Sidebar logo
    with st.sidebar:
        st.image("app_logo.png", width=250)

    # App header with logo
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("app_logo.png", width=100)
    with col2:
        st.markdown("<h1 class='main-header'>VectorVault</h1>", unsafe_allow_html=True)
        st.markdown("<p class='sub-header'>Knowledge, Instantly Retrieved</p>", unsafe_allow_html=True)


def check_api_health():
    """
    Check API health and display status in sidebar.
    
    Returns:
        bool: True if API is available, False otherwise
    """
    try:
        health_response = requests.get(get_api_endpoint("health"))
        if health_response.status_code == 200:
            health_data = health_response.json()
            with st.sidebar:
                st.subheader("System Status")
                st.success(f"✅ API Connected")
                st.info(f"📚 Documents: {health_data.get('documents_indexed', 0)}")
                st.info(f"🧠 Model: {health_data.get('embedding_model', 'text-embedding-3-small')}")
                if health_data.get('storage'):
                    st.info(f"💾 Storage: {health_data.get('storage', {}).get('type', 'Local')}")
            return True
        else:
            st.sidebar.error("❌ API Unavailable")
            logger.error(f"API health check failed: {health_response.status_code}")
            return False
    except Exception as e:
        st.sidebar.error(f"❌ Cannot connect to API: {str(e)}")
        st.sidebar.info(f"Make sure the API is running at {API_URL}")
        st.sidebar.info(f"API URL: {API_URL}")
        logger.error(f"API connection error: {str(e)}")
        return False


def search_tab():
    """Render the search tab."""
    st.header("Search Documents")

    query = st.text_input("Enter your search query:", 
                         placeholder="What would you like to know?", 
                         key="search_query")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        top_n = st.number_input("Results:", min_value=1, max_value=20, value=5, step=1)
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    if search_button and query:
        try:
            with st.spinner("Searching..."):
                logger.info(f"Searching for: {query}")
                response = requests.get(
                    get_api_endpoint("search"), 
                    params={"q": query, "n": top_n}
                )
                
            if response.status_code == 200:
                results = response.json().get("results", [])
                st.write(f"Found {len(results)} results:")
                
                if results:
                    for i, result in enumerate(results):
                        with st.expander(f"Result {i+1}: {result['text'][:60]}...", expanded=i==0):
                            st.markdown(f"**ID:** `{result['id']}`")
                            st.markdown(f"**Score:** {1.0 - result['distance']:.4f}")
                            st.markdown("**Document:**")
                            st.markdown(f"{result['text']}")
                            
                            if result.get('metadata'):
                                st.markdown("**Metadata:**")
                                st.json(result['metadata'])
                else:
                    st.info("No results found. Try a different query.")
                    logger.info(f"No results found for query: {query}")
            else:
                st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                logger.error(f"Search error: {response.json().get('error')}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"Search exception: {str(e)}")


def upload_tab():
    """Render the document upload tab."""
    st.header("Upload Document")
    
    # Document input
    text_input = st.text_area("Enter document text:", height=200, 
                             placeholder="Paste or type the document text here...")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Optional metadata
        st.subheader("Metadata (Optional)")
        source = st.text_input("Source:", placeholder="e.g., Wikipedia, Report, etc.")
        category = st.text_input("Category:", placeholder="e.g., Science, Finance, etc.")
        date = st.date_input("Date:", value=None)
    
    with col2:
        st.subheader("Custom Metadata (Optional)")
        custom_key = st.text_input("Key:", placeholder="Custom metadata key")
        custom_value = st.text_input("Value:", placeholder="Custom metadata value")
        
        add_custom = st.button("+ Add Custom Field")
        if "custom_metadata" not in st.session_state:
            st.session_state.custom_metadata = {}
            
        if add_custom and custom_key and custom_value:
            st.session_state.custom_metadata[custom_key] = custom_value
            st.success(f"Added: {custom_key} = {custom_value}")
            
        if st.session_state.custom_metadata:
            st.json(st.session_state.custom_metadata)
            if st.button("Clear Custom Metadata"):
                st.session_state.custom_metadata = {}
                st.experimental_rerun()
    
    submit_button = st.button("📤 Upload Document", use_container_width=True)
    
    if submit_button and text_input:
        # Prepare metadata
        metadata = st.session_state.custom_metadata.copy() if "custom_metadata" in st.session_state else {}
        
        if source:
            metadata["source"] = source
        if category:
            metadata["category"] = category
        if date:
            metadata["date"] = date.isoformat()
        
        # Prepare payload
        payload = {
            "text": text_input,
            "metadata": metadata
        }
        
        try:
            with st.spinner("Uploading document..."):
                logger.info("Uploading document")
                response = requests.post(
                    get_api_endpoint("documents"), 
                    json=payload
                )
            
            if response.status_code == 201:
                result = response.json()
                st.markdown("<div class='success-box'>Document uploaded successfully!</div>", unsafe_allow_html=True)
                st.info(f"Document ID: {result.get('id', 'Unknown')}")
                logger.info(f"Document uploaded successfully with ID: {result.get('id')}")
            else:
                st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                logger.error(f"Document upload error: {response.json().get('error')}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"Document upload exception: {str(e)}")


def batch_upload_tab():
    """Render the batch upload tab."""
    st.header("Batch Upload")
    
    st.info("Upload multiple documents at once using CSV or JSON format.")
    
    file_format = st.radio("File Format:", ["CSV", "JSON"])
    
    if file_format == "CSV":
        handle_csv_upload()
    else:  # JSON format
        handle_json_upload()


def handle_csv_upload():
    """Handle CSV batch upload."""
    st.markdown("""
    CSV should have these columns:
    - `text` (required): The document content
    - `source` (optional): Document source
    - `category` (optional): Document category
    - Any other columns will be included as metadata
    """)
    
    sample_csv = """text,source,category
"MongoDB is a document database with the scalability and flexibility that you want with the querying and indexing that you need.",Documentation,Database
"MongoDB Atlas is the multi-cloud developer data platform that provides the database and services you need to accelerate to the cloud.",Product,Cloud"""
    
    st.code(sample_csv, language="csv")
    
    uploaded_file = st.file_uploader("Upload CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            if "text" not in df.columns and "content" not in df.columns:
                st.error("CSV must contain a 'text' or 'content' column")
                logger.error("CSV upload missing required text/content column")
            else:
                st.write(f"Found {len(df)} documents in CSV")
                st.dataframe(df.head(5))
                
                if st.button("📤 Upload Batch", use_container_width=True):
                    process_batch_upload_from_dataframe(df)
        except Exception as e:
            st.error(f"Error processing CSV: {str(e)}")
            logger.error(f"CSV processing error: {str(e)}")


def handle_json_upload():
    """Handle JSON batch upload."""
    st.markdown("""
    JSON should be an array of objects with:
    - `text` or `content` (required): The document content
    - `metadata` (optional): An object with metadata fields
    """)
    
    sample_json = """[
  {
    "text": "MongoDB is a document database with scalability and flexibility.",
    "metadata": {
      "source": "Documentation",
      "category": "Database"
    }
  },
  {
    "content": "MongoDB Atlas is the multi-cloud developer data platform.",
    "metadata": {
      "source": "Product",
      "category": "Cloud"
    }
  }
]"""
    
    st.code(sample_json, language="json")
    
    uploaded_file = st.file_uploader("Upload JSON file", type="json")
    json_text = st.text_area("Or paste JSON here:", height=200, placeholder="Paste JSON array here...")
    
    json_data = None
    
    if uploaded_file is not None:
        try:
            json_data = json.load(uploaded_file)
            logger.info(f"Loaded JSON file with {len(json_data)} items")
        except Exception as e:
            st.error(f"Error parsing JSON file: {str(e)}")
            logger.error(f"JSON file parsing error: {str(e)}")
    elif json_text:
        try:
            json_data = json.loads(json_text)
            logger.info(f"Parsed JSON text with {len(json_data)} items")
        except Exception as e:
            st.error(f"Error parsing JSON text: {str(e)}")
            logger.error(f"JSON text parsing error: {str(e)}")
            
    if json_data:
        if not isinstance(json_data, list):
            st.error("JSON must be an array of document objects")
            logger.error("Invalid JSON format: not an array")
        else:
            st.write(f"Found {len(json_data)} documents in JSON")
            
            if st.button("📤 Upload Batch", use_container_width=True):
                process_batch_upload(json_data)


def process_batch_upload_from_dataframe(df: pd.DataFrame):
    """
    Process batch upload from pandas DataFrame.
    
    Args:
        df: DataFrame containing documents to upload
    """
    documents = []
    text_col = "text" if "text" in df.columns else "content"
    
    for _, row in df.iterrows():
        doc = {text_col: row[text_col]}
        
        # Add all other columns as metadata
        metadata = {}
        for col in df.columns:
            if col != text_col and not pd.isna(row[col]):
                metadata[col] = row[col]
        
        if metadata:
            doc["metadata"] = metadata
        
        documents.append(doc)
    
    process_batch_upload(documents)


def process_batch_upload(documents: List[Dict[str, Any]]):
    """
    Process batch upload of documents.
    
    Args:
        documents: List of document objects to upload
    """
    try:
        with st.spinner(f"Uploading {len(documents)} documents..."):
            logger.info(f"Batch uploading {len(documents)} documents")
            response = requests.post(
                get_api_endpoint("documents/batch"), 
                json=documents
            )
            
        if response.status_code in [200, 207]:
            result = response.json()
            st.markdown("<div class='success-box'>Batch upload completed!</div>", unsafe_allow_html=True)
            st.write(result.get("message", ""))
            
            # Show detailed results
            results = result.get("results", [])
            success = len([r for r in results if r.get("status") == "success"])
            errors = len([r for r in results if r.get("status") == "error"])
            
            st.write(f"✅ {success} documents added successfully")
            logger.info(f"Batch upload: {success} succeeded, {errors} failed")
            
            if errors > 0:
                st.write(f"❌ {errors} documents failed")
                
                # Display errors
                error_list = [r for r in results if r.get("status") == "error"]
                if error_list:
                    with st.expander("View Errors"):
                        for i, err in enumerate(error_list[:10]):  # Show first 10 errors
                            st.write(f"Error {i+1}: {err.get('errors') or err.get('message', 'Unknown error')}")
                        
                        if len(error_list) > 10:
                            st.write(f"... and {len(error_list) - 10} more errors")
        else:
            st.error(f"Error: {response.json().get('error', 'Unknown error')}")
            logger.error(f"Batch upload error: {response.json().get('error')}")
    except Exception as e:
        st.error(f"Error: {str(e)}")
        logger.error(f"Batch upload exception: {str(e)}")


def display_sidebar_info():
    """Display additional information in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.subheader("About VectorVault")
        st.write("A simple document search engine using vector embeddings for semantic search.")
        
        st.markdown("---")
        st.subheader("How it works")
        st.markdown("""
        1. **Upload** documents individually or in batch
        2. Documents are converted to vector embeddings
        3. **Search** using natural language
        4. Results are ranked by semantic similarity
        """)
        
        st.markdown("---")
        st.caption("VectorVault - Knowledge, Instantly Retrieved")
        st.caption("Powered by OpenAI and FAISS")


def main():
    """Main application function."""
    display_header()
    api_available = check_api_health()
    
    if not api_available:
        st.warning("⚠️ API is not available. Some features may not work correctly.")
    
    # Tabs for different functions
    tab1, tab2, tab3 = st.tabs(["Search", "Upload Documents", "Batch Upload"])
    
    with tab1:
        search_tab()
    
    with tab2:
        upload_tab()
    
    with tab3:
        batch_upload_tab()
    
    display_sidebar_info()


if __name__ == "__main__":
    main() 