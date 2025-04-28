"""Authentication components for VectorVault Streamlit UI"""
import streamlit as st
import requests
import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

def get_api_endpoint(endpoint: str, api_url: str) -> str:
    """Get full API endpoint URL"""
    # Remove leading slash if present
    if endpoint.startswith('/'):
        endpoint = endpoint[1:]
    
    # If API_URL already ends with a slash, don't add another
    if api_url.endswith('/'):
        return f"{api_url}{endpoint}"
    else:
        return f"{api_url}/{endpoint}"

def login_form(api_url: str) -> bool:
    """Display login form and handle authentication"""
    st.subheader("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
                return False
            
            try:
                # Call login API
                response = requests.post(
                    get_api_endpoint("auth/login", api_url),
                    json={"username": username, "password": password}
                )
                
                if response.status_code == 200:
                    # Login successful
                    data = response.json()
                    
                    # Store token and user info in session state
                    st.session_state.token = data["token"]
                    st.session_state.user = data["user"]
                    st.session_state.authenticated = True
                    
                    # Use toast notification instead of inline success message
                    st.toast("Login successful!", icon="✅")
                    return True
                else:
                    # Login failed
                    error_msg = response.json().get("error", "Invalid username or password")
                    st.error(f"Login failed: {error_msg}")
                    return False
                    
            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                st.error(f"An error occurred during login: {str(e)}")
                return False
        
        return False

def register_form(api_url: str) -> bool:
    """Display registration form and handle user creation"""
    st.subheader("Register")
    
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        submit = st.form_submit_button("Register", use_container_width=True)
        
        if submit:
            # Validate input
            if not username or not email or not password:
                st.error("Please fill all required fields")
                return False
                
            if password != confirm_password:
                st.error("Passwords do not match")
                return False
            
            try:
                # Call register API
                response = requests.post(
                    get_api_endpoint("auth/register", api_url),
                    json={"username": username, "email": email, "password": password}
                )
                
                if response.status_code == 201:
                    # Registration successful
                    # Use toast notification instead of inline success message
                    st.toast("Registration successful! You can now login.", icon="✅")
                    return True
                else:
                    # Registration failed
                    error_msg = response.json().get("error", "Registration failed")
                    st.error(f"Registration failed: {error_msg}")
                    return False
                    
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                st.error(f"An error occurred during registration: {str(e)}")
                return False
        
        return False

def auth_page(api_url: str) -> bool:
    """Display authentication page with login and register tabs"""
    # Check if already authenticated
    if st.session_state.get("authenticated", False):
        return True
    
    st.title("VectorVault Pilot")
    
    # Create tabs for login and register
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        if login_form(api_url):
            return True
    
    with tab2:
        register_form(api_url)
    
    return False

def logout_button(api_url: str):
    """Display logout button in sidebar"""
    if st.sidebar.button("Logout"):
        # Call logout API if token exists
        if "token" in st.session_state:
            try:
                response = requests.post(
                    get_api_endpoint("auth/logout", api_url),
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                logger.info(f"Logout API response: {response.status_code}")
            except Exception as e:
                logger.error(f"Logout error: {str(e)}")
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Force refresh
        st.rerun()

def user_info_sidebar(api_url: str):
    """Display user info in sidebar"""
    if "user" in st.session_state:
        user = st.session_state.user
        st.sidebar.subheader(f"👤 {user['username']}")
        st.sidebar.caption(f"Role: {user['role']}")
        logout_button(api_url)

def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API calls"""
    headers = {}
    if "token" in st.session_state:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return headers