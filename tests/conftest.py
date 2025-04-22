"""
Pytest configuration file with fixtures for VectorVault tests.
"""

import os
import sys
import pytest
import tempfile
import numpy as np
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to import app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as flask_app

@pytest.fixture
def app():
    """Configure Flask app for testing."""
    flask_app.app.config['TESTING'] = True
    return flask_app.app

@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()

@pytest.fixture
def mock_embedding():
    """Create a mock embedding vector."""
    return np.random.rand(1536).astype(np.float32)

@pytest.fixture
def temp_directory():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.TemporaryDirectory()
    yield temp_dir.name
    temp_dir.cleanup()

@pytest.fixture
def sample_document():
    """Create a sample valid document."""
    return {
        "text": "This is a test document about MongoDB with sufficient length.",
        "metadata": {
            "source": "Test",
            "category": "Database"
        }
    }

@pytest.fixture
def sample_document_batch():
    """Create a sample batch of documents."""
    return [
        {
            "text": "MongoDB is a document database with the scalability and flexibility that you want.",
            "metadata": {"source": "Test", "category": "Database"}
        },
        {
            "text": "MongoDB Atlas is a cloud service for MongoDB.",
            "metadata": {"source": "Test", "category": "Cloud"}
        },
        {
            "content": "MongoDB Compass is the GUI for MongoDB.",
            "metadata": {"source": "Test", "category": "Tool"}
        }
    ]

@pytest.fixture
def mock_app_environment(temp_directory):
    """Set up a controlled app environment for testing."""
    # Save original values
    original_index_file = flask_app.INDEX_FILE
    original_metadata_file = flask_app.METADATA_FILE
    original_doc_store = flask_app.doc_store.copy()
    
    # Set test values
    flask_app.INDEX_FILE = os.path.join(temp_directory, "test_faiss_index.index")
    flask_app.METADATA_FILE = os.path.join(temp_directory, "test_document_metadata.json")
    flask_app.doc_store = {}
    
    # Initialize a fresh index
    flask_app.index = flask_app.faiss.IndexFlatL2(flask_app.EMBEDDING_DIM)
    
    yield
    
    # Restore original values
    flask_app.INDEX_FILE = original_index_file
    flask_app.METADATA_FILE = original_metadata_file
    flask_app.doc_store = original_doc_store 