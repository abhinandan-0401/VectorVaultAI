#!/usr/bin/env python3
"""
VectorVault UI - Streamlit interface for semantic document search
"""

# IMPORTANT: This must be the first Streamlit command
import streamlit as st
st.set_page_config(
    page_title="VectorVault",
    page_icon="🧠",
    layout="wide",
)

import json
import logging
import os
import time
from io import StringIO, BytesIO
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import auth components - AFTER st.set_page_config
import auth_components

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
    return auth_components.get_api_endpoint(endpoint, API_URL)

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
    .source-header {
        font-weight: bold;
        color: #4B9FE1;
        font-size: 1.2rem;
    }
    .message-container {
        display: flex;
        margin-bottom: 10px;
    }
    .user-message {
        background-color: #e8eaf6;
        padding: 10px 15px;
        border-radius: 15px 15px 15px 5px;
        margin-left: auto;
        margin-right: 10px;
        max-width: 80%;
        color: #333333;
    }
    .ai-message {
        background-color: #2E7D32;
        padding: 10px 15px;
        border-radius: 15px 15px 5px 15px;
        margin-right: auto;
        margin-left: 10px;
        max-width: 80%;
        color: #FFFFFF;
    }
    .source-citation {
        font-size: 0.8rem;
        color: #B2DFDB;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

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

def search_tab(auth_headers):
    """Render the search tab."""
    st.header("Search Documents")

    query = st.text_input("Enter your search query:", 
                         placeholder="What would you like to know?", 
                         key="search_query")
    
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        top_n = st.number_input("Results:", min_value=1, max_value=20, value=5, step=1)
    with col2:
        group_results = st.checkbox("Group results by source", value=True)
    with col3:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    if search_button and query:
        try:
            with st.spinner("Searching..."):
                logger.info(f"Searching for: {query}")
                response = requests.get(
                    get_api_endpoint("search"), 
                    params={"q": query, "n": top_n, "group": str(group_results).lower()},
                    headers=auth_headers
                )
                
            if response.status_code == 200:
                result_data = response.json()
                
                if group_results and "groups" in result_data:
                    groups = result_data.get("groups", [])
                    st.write(f"Found {result_data.get('total_results', 0)} results in {len(groups)} sources:")
                    
                    if groups:
                        for group in groups:
                            source = group.get("source", "Unknown")
                            documents = group.get("documents", [])
                            avg_score = group.get("avg_score", 0)
                            
                            with st.expander(f"📁 {source} ({len(documents)} documents, Relevance: {avg_score:.2f})", expanded=True):
                                st.markdown(f"<p class='source-header'>{source}</p>", unsafe_allow_html=True)
                                
                                for i, doc in enumerate(documents):
                                    with st.expander(f"Document {i+1}: {doc['text'][:60]}...", expanded=i==0):
                                        st.markdown(f"**ID:** `{doc['id']}`")
                                        st.markdown(f"**Score:** {doc.get('score', 0):.4f}")
                                        
                                        # Display page number if available
                                        if "page" in doc.get("metadata", {}):
                                            st.markdown(f"**Page:** {doc['metadata']['page']}")
                                        
                                        st.markdown("**Content:**")
                                        st.markdown(f"{doc['text']}")
                                        
                                        if doc.get('metadata') and any(k != "source" and k != "page" for k in doc['metadata']):
                                            st.markdown("**Additional Metadata:**")
                                            display_metadata = {k: v for k, v in doc['metadata'].items() if k != "source" and k != "page"}
                                            st.json(display_metadata)
                    else:
                        st.info("No results found. Try a different query.")
                        logger.info(f"No results found for query: {query}")
                else:
                    # Standard results display (not grouped)
                    results = result_data.get("results", [])
                    st.write(f"Found {len(results)} results:")
                    
                    if results:
                        for i, result in enumerate(results):
                            with st.expander(f"Result {i+1}: {result['text'][:60]}...", expanded=i==0):
                                st.markdown(f"**ID:** `{result['id']}`")
                                st.markdown(f"**Score:** {result.get('score', 1.0 - result.get('distance', 0)):.4f}")
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

def pdf_upload_tab(health_data, auth_headers):
    """Render the PDF upload tab."""
    st.header("Upload PDF Document")
    
    # Check if PDF processing is supported
    features = health_data.get("features", [])
    if "pdf_processing" not in features:
        st.warning("PDF processing is not enabled on the API server. Please check your server configuration.")
        st.info("To enable PDF processing, ensure your server has the required dependencies and GCS_BUCKET_NAME is set.")
        return
    
    # File uploader with size limit note
    st.info("Maximum file size: 100 MB")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    # Metadata
    with st.expander("Add Metadata (Optional)", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            source = st.text_input("Source:", placeholder="e.g., Company Report, Textbook, etc.", key="pdf_source")
            author = st.text_input("Author:", placeholder="e.g., John Doe, Unknown, etc.")
        
        with col2:
            category = st.text_input("Category:", placeholder="e.g., Technical, Financial, etc.", key="pdf_category")
            year = st.text_input("Year:", placeholder="e.g., 2023")
    
    # Process upload button
    process_button = st.button("🔍 Process PDF Document", use_container_width=True, disabled=uploaded_file is None)
    
    if process_button and uploaded_file is not None:
        try:
            # Check file size (100 MB limit)
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > 100:
                st.error(f"File size ({file_size_mb:.2f} MB) exceeds the 100 MB limit.")
                return
                
            # Prepare metadata
            metadata = {
                "source": source if source else uploaded_file.name,
                "category": category if category else "Uncategorized"
            }
            
            if author:
                metadata["author"] = author
            if year:
                metadata["year"] = year
            
            # Create form data
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            data = {"metadata": json.dumps(metadata)}
            
            with st.spinner("Processing PDF document..."):
                logger.info(f"Processing PDF document: {uploaded_file.name} ({file_size_mb:.2f} MB)")
                
                # Make the API request with increased timeout for large files
                response = requests.post(
                    get_api_endpoint("documents/pdf"),
                    files=files,
                    data=data,
                    headers=auth_headers,
                    timeout=600  # 10 minute timeout for large files
                )
                
            if response.status_code == 201:
                result = response.json()
                st.markdown("<div class='success-box'>PDF document processed successfully!</div>", unsafe_allow_html=True)
                st.info(f"Document: {result.get('document_name', uploaded_file.name)}")
                st.info(f"Chunks processed: {result.get('chunks_count', 'Unknown')}")
                
                # Success message
                st.success("Your PDF has been processed and is now searchable.")
                logger.info(f"PDF document processed successfully: {uploaded_file.name}")
            else:
                st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                logger.error(f"PDF processing error: {response.json().get('error')}")
        except requests.exceptions.Timeout:
            st.error("Request timed out. The PDF may be too large or complex to process.")
            logger.error(f"PDF processing timeout for file: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"PDF processing exception: {str(e)}")

def vaultgpt_tab(health_data, auth_headers):
    """Render the VaultGPT tab for RAG operations."""
    st.header("VaultGPT")
    
    # Check if VaultGPT is supported
    features = health_data.get("features", [])
    if "vaultgpt" not in features:
        st.warning("VaultGPT is not enabled on the API server. Please check your server configuration.")
        st.info("To enable VaultGPT, ensure your server has the required dependencies installed.")
        return
    
    # Initialize conversation state
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    
    # Initialize chat history in session state if not already present
    if "vaultgpt_history" not in st.session_state:
        st.session_state.vaultgpt_history = []
    
    # Get user's conversations if logged in
    try:
        response = requests.get(
            get_api_endpoint("conversations"),
            headers=auth_headers
        )
        
        if response.status_code == 200:
            conversations = response.json()
            
            # Only show selector if we have conversations
            if conversations:
                # Create options list with "New conversation" at the top
                conversation_options = ["New conversation"]
                conversation_options.extend([f"{conv.get('title', 'Untitled')} ({conv.get('created_at', '')[:10]})" for conv in conversations])
                
                selected_option = st.selectbox(
                    "Select a conversation:",
                    conversation_options
                )
                
                # Handle conversation selection
                if selected_option != "New conversation":
                    # Get the selected conversation index
                    idx = conversation_options.index(selected_option) - 1  # Adjust for "New conversation"
                    conv_id = conversations[idx].get("_id")
                    
                    # Load conversation if it's different from current one
                    if st.session_state.conversation_id != conv_id:
                        st.session_state.conversation_id = conv_id
                        
                        # Fetch full conversation
                        conv_response = requests.get(
                            get_api_endpoint(f"conversations/{conv_id}"),
                            headers=auth_headers
                        )
                        
                        if conv_response.status_code == 200:
                            full_conversation = conv_response.json()
                            st.session_state.vaultgpt_history = full_conversation.get("messages", [])
                else:
                    # Start new conversation
                    st.session_state.conversation_id = None
                    st.session_state.vaultgpt_history = []
        
    except Exception as e:
        logger.error(f"Error loading conversations: {str(e)}")
    
    # Display chat history
    for message in st.session_state.vaultgpt_history:
        if message["role"] == "user":
            st.markdown(f"<div class='message-container'><div class='user-message'>{message['content']}</div></div>", unsafe_allow_html=True)
        else:
            # AI message with sources
            ai_message = f"<div class='message-container'><div class='ai-message'>{message['content']}"
            
            # Add sources if present
            if "sources" in message and message["sources"]:
                ai_message += "<div class='source-citation'>Sources: "
                sources = []
                for src in message["sources"]:
                    source = src.get("source", "Unknown")
                    page = src.get("page", "")
                    page_info = f", p.{page}" if page else ""
                    sources.append(f"{source}{page_info}")
                
                ai_message += "; ".join(sources)
                ai_message += "</div>"
            
            ai_message += "</div></div>"
            st.markdown(ai_message, unsafe_allow_html=True)
    
    # User input
    with st.form("vaultgpt_form", clear_on_submit=True):
        user_input = st.text_area("Ask VaultGPT:", placeholder="What would you like to know?", key="vaultgpt_input")
        col1, col2 = st.columns([1, 5])
        
        with col1:
            top_n = st.number_input("Documents to retrieve:", min_value=1, max_value=10, value=3, step=1)
        
        submit_button = st.form_submit_button("🤖 Ask VaultGPT", use_container_width=True)
    
    # Clear chat button
    if st.button("🗑️ Start New Chat", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.vaultgpt_history = []
        st.rerun()
    
    if submit_button and user_input:
        # Add user message to history
        st.session_state.vaultgpt_history.append({
            "role": "user",
            "content": user_input
        })
        
        try:
            # Prepare payload
            payload = {
                "query": user_input,
                "top_n": top_n
            }
            
            # Include conversation ID if we have one
            if st.session_state.conversation_id:
                payload["conversation_id"] = st.session_state.conversation_id
            
            with st.spinner("Thinking..."):
                logger.info(f"VaultGPT query: {user_input}")
                
                # Make the API request
                response = requests.post(
                    get_api_endpoint("vaultgpt"),
                    json=payload,
                    headers=auth_headers
                )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", "I couldn't generate a response.")
                documents = result.get("documents", [])
                
                # Save conversation ID if this is a new conversation
                if "conversation_id" in result and not st.session_state.conversation_id:
                    st.session_state.conversation_id = result["conversation_id"]
                
                # Extract sources for display
                sources = []
                for doc in documents:
                    source = {
                        "source": doc.get("metadata", {}).get("source", "Unknown"),
                        "page": doc.get("metadata", {}).get("page", "")
                    }
                    sources.append(source)
                
                # Add AI response to history
                st.session_state.vaultgpt_history.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
                
                # Display the updated chat immediately instead of forcing a rerun
                # This was causing the chat to reset
                st.markdown(f"<div class='message-container'><div class='ai-message'>{answer}")
                
                # Add source citations if present
                if sources:
                    st.markdown("<div class='source-citation'>Sources: " + 
                               "; ".join([f"{src.get('source', 'Unknown')}" + 
                                         (f", p.{src.get('page', '')}" if src.get('page', '') else "") 
                                         for src in sources]) + 
                               "</div>", unsafe_allow_html=True)
                
                st.markdown("</div></div>", unsafe_allow_html=True)
            else:
                st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                logger.error(f"VaultGPT error: {response.json().get('error')}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"VaultGPT exception: {str(e)}")

def user_management_tab(auth_headers):
    """Tab for managing users (admin only)"""
    st.header("User Management")
    
    try:
        # Get users from API
        response = requests.get(
            get_api_endpoint("admin/users"),
            headers=auth_headers
        )
        
        if response.status_code == 200:
            users = response.json()
            
            # Display users in a table
            if users:
                # Create DataFrame
                user_data = []
                for user in users:
                    user_data.append({
                        "ID": user.get("id"),
                        "Username": user.get("username"),
                        "Email": user.get("email"),
                        "Role": user.get("role"),
                        "Created": user.get("created_at", "")[:10],
                        "Last Login": user.get("last_login", "")[:10] if user.get("last_login") else "Never"
                    })
                
                user_df = pd.DataFrame(user_data)
                st.dataframe(user_df, use_container_width=True)
                
                # Create new user
                with st.expander("Create New User"):
                    with st.form("create_user_form"):
                        st.subheader("Add New User")
                        username = st.text_input("Username")
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        role = st.selectbox("Role", ["reader", "editor", "admin"])
                        submit = st.form_submit_button("Create User")
                        
                        if submit:
                            if not username or not email or not password:
                                st.error("Please fill all required fields")
                            else:
                                try:
                                    # Call API to create user
                                    create_response = requests.post(
                                        get_api_endpoint("admin/users"),
                                        json={
                                            "username": username,
                                            "email": email,
                                            "password": password,
                                            "role": role
                                        },
                                        headers=auth_headers
                                    )
                                    
                                    if create_response.status_code == 201:
                                        st.success("User created successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to create user: {create_response.json().get('error', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"Error creating user: {str(e)}")
                
                # Modify existing user
                with st.expander("Edit User"):
                    # Select user
                    selected_username = st.selectbox(
                        "Select user to edit",
                        [user["Username"] for user in user_data]
                    )
                    
                    # Find selected user
                    selected_user = next((u for u in user_data if u["Username"] == selected_username), None)
                    
                    if selected_user:
                        with st.form("edit_user_form"):
                            st.subheader(f"Edit User: {selected_username}")
                            user_id = selected_user["ID"]
                            
                            email = st.text_input("Email", value=selected_user["Email"])
                            role = st.selectbox("Role", ["reader", "editor", "admin"], 
                                              index=["reader", "editor", "admin"].index(selected_user["Role"]))
                            password = st.text_input("New Password (leave blank to keep current)", type="password")
                            
                            submit = st.form_submit_button("Update User")
                            
                            if submit:
                                # Prepare payload
                                payload = {
                                    "email": email,
                                    "role": role
                                }
                                
                                # Add password if provided
                                if password:
                                    payload["password"] = password
                                
                                try:
                                    # Call API to update user
                                    update_response = requests.put(
                                        get_api_endpoint(f"admin/users/{user_id}"),
                                        json=payload,
                                        headers=auth_headers
                                    )
                                    
                                    if update_response.status_code == 200:
                                        st.success("User updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to update user: {update_response.json().get('error', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"Error updating user: {str(e)}")
            else:
                st.info("No users found")
        else:
            st.error(f"Failed to load users: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error loading users: {str(e)}")

def display_sidebar_info():
    """Display additional information in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.subheader("About VectorVault")
        st.write("A document search engine using vector embeddings for semantic search and RAG capabilities.")
        
        # Only display "How it works" section without showing features in sidebar
        st.markdown("---")
        st.caption("VectorVault - Knowledge, Instantly Retrieved")
        st.caption("Powered by OpenAI and MongoDB Atlas")

def main():
    """Main application function."""
    display_header()
    
    # Check authentication first, before any other operations
    if not auth_components.auth_page(API_URL):
        return  # Stop execution if not authenticated
        
    # Display user info in sidebar
    auth_components.user_info_sidebar(API_URL)
    
    # Get authentication headers for API calls
    auth_headers = auth_components.get_auth_headers()
    
    # Continue with API health check using auth headers
    try:
        health_response = requests.get(
            get_api_endpoint("health"),
            headers=auth_headers
        )
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            with st.sidebar:
                st.subheader("System Status")
                st.success(f"✅ API Connected")
                st.info(f"📚 Documents: {health_data.get('unique_documents', 0)} PDFs")
                st.info(f"🧩 Chunks: {health_data.get('chunks_count', 0)} text segments")
                st.info(f"🧠 Model: {health_data.get('embedding_model', 'text-embedding-3-small')}")
                if health_data.get('storage'):
                    st.info(f"💾 Storage: {health_data.get('storage', {}).get('type', 'Local')}")
                
                # Display user info in sidebar AFTER system status
                if "user" in st.session_state:
                    st.markdown("---")
                    st.subheader("User Profile")
                    user = st.session_state.user
                    st.info(f"👤 Username: {user['username']}")
                    st.info(f"🔑 Role: {user['role']}")
                    if st.button("Logout", use_container_width=True):
                        # Call logout API
                        try:
                            requests.post(
                                get_api_endpoint("auth/logout"),
                                headers=auth_headers
                            )
                        except:
                            pass  # Ignore errors on logout
                        
                        # Clear session state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        
                        # Show toast notification
                        st.toast("Logged out successfully!", icon="✅")
                        
                        # Force refresh
                        st.rerun()
            api_available = True
        else:
            st.sidebar.error("❌ API Unavailable")
            logger.error(f"API health check failed: {health_response.status_code}")
            api_available = False
            health_data = {}
    except Exception as e:
        st.sidebar.error(f"❌ Cannot connect to API: {str(e)}")
        st.sidebar.info(f"Make sure the API is running at {API_URL}")
        logger.error(f"API connection error: {str(e)}")
        api_available = False
        health_data = {}
    
    # Show warning if API not available
    if not api_available:
        st.warning("⚠️ API is not available. Some features may not work correctly.")
    
    # Get user role
    user_role = st.session_state.user.get("role", "reader")
    
    # Create tabs based on user role and available features
    tabs = []
    features = health_data.get("features", [])
    
    # Add Search tab (available to all roles)
    tabs.append("Search")
    
    # Add PDF Upload tab (only for admin and editor)
    if user_role in ["admin", "editor"] and "pdf_processing" in features:
        tabs.append("PDF Upload")
    
    # Add VaultGPT tab (available to all roles)
    if "vaultgpt" in features:
        tabs.append("VaultGPT")
    
    # Add User Management tab (admin only)
    if user_role == "admin":
        tabs.append("User Management")
    
    # Create tabs
    tab_containers = st.tabs(tabs)
    
    # Tab indexing
    tab_index = 0
    
    # Search tab
    with tab_containers[tab_index]:
        search_tab(auth_headers)  # Pass auth headers to the function
    tab_index += 1
    
    # PDF Upload tab if available
    if user_role in ["admin", "editor"] and "pdf_processing" in features:
        with tab_containers[tab_index]:
            pdf_upload_tab(health_data, auth_headers)  # Pass auth headers
        tab_index += 1
    
    # VaultGPT tab if available
    if "vaultgpt" in features:
        with tab_containers[tab_index]:
            vaultgpt_tab(health_data, auth_headers)  # Pass auth headers
        tab_index += 1
    
    # User Management tab (admin only)
    if user_role == "admin":
        with tab_containers[tab_index]:
            user_management_tab(auth_headers)  # Pass auth headers
    
    display_sidebar_info()

if __name__ == "__main__":
    main()