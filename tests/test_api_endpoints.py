import os
import sys
import unittest
import json
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np

# Add parent directory to path to import app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as flask_app

class TestAPIEndpoints(unittest.TestCase):
    """Test cases for API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        # Configure Flask app for testing
        flask_app.app.config['TESTING'] = True
        self.app = flask_app.app.test_client()
        
        # Create a mock embedding
        self.mock_embedding = np.random.rand(1536).astype(np.float32)
        
        # Set up a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_index_file = flask_app.INDEX_FILE
        self.old_metadata_file = flask_app.METADATA_FILE
        flask_app.INDEX_FILE = os.path.join(self.temp_dir.name, "test_faiss_index.index")
        flask_app.METADATA_FILE = os.path.join(self.temp_dir.name, "test_document_metadata.json")
        
        # Initialize a fresh index
        flask_app.index = flask_app.faiss.IndexFlatL2(flask_app.EMBEDDING_DIM)
        flask_app.doc_store = {}
        
    def tearDown(self):
        """Clean up after tests."""
        # Restore original file paths
        flask_app.INDEX_FILE = self.old_index_file
        flask_app.METADATA_FILE = self.old_metadata_file
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    @patch('app.get_embedding')
    def test_add_document(self, mock_get_embedding):
        """Test adding a document via the API."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Test document
        test_doc = {
            "text": "This is a test document about MongoDB.",
            "metadata": {
                "source": "Test",
                "category": "Database"
            }
        }
        
        # Send POST request
        response = self.app.post(
            '/documents',
            data=json.dumps(test_doc),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("id", data)
        
        # Verify document was added
        self.assertEqual(flask_app.index.ntotal, 1)
        self.assertEqual(len(flask_app.doc_store), 1)
        
        # Verify mock was called
        mock_get_embedding.assert_called_once()
    
    @patch('app.get_embedding')
    def test_add_document_with_validation_error(self, mock_get_embedding):
        """Test adding an invalid document."""
        # Test invalid document (too short)
        test_doc = {
            "text": "Short",
            "metadata": {"source": "Test"}
        }
        
        # Send POST request
        response = self.app.post(
            '/documents',
            data=json.dumps(test_doc),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("errors", data)
        
        # Verify document was not added
        self.assertEqual(flask_app.index.ntotal, 0)
        self.assertEqual(len(flask_app.doc_store), 0)
        
        # Verify mock was not called
        mock_get_embedding.assert_not_called()
    
    @patch('app.get_embedding')
    def test_batch_add_documents(self, mock_get_embedding):
        """Test batch adding documents."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Test documents
        test_docs = [
            {
                "text": "MongoDB is a document database.",
                "metadata": {"source": "Test", "category": "Database"}
            },
            {
                "content": "MongoDB Atlas is a cloud service.",
                "metadata": {"source": "Test", "category": "Cloud"}
            },
            {
                "text": "Too short",  # Invalid document
                "metadata": {"source": "Test"}
            }
        ]
        
        # Send POST request
        response = self.app.post(
            '/documents/batch',
            data=json.dumps(test_docs),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 207)  # Multi-Status
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("results", data)
        
        # Expected: 2 successful, 1 failed
        success_count = sum(1 for r in data["results"] if r.get("status") == "success")
        error_count = sum(1 for r in data["results"] if r.get("status") == "error")
        self.assertEqual(success_count, 2)
        self.assertEqual(error_count, 1)
        
        # Verify documents were added
        self.assertEqual(flask_app.index.ntotal, 2)
        self.assertEqual(len(flask_app.doc_store), 2)
        
        # Verify mock was called twice (for the two valid documents)
        self.assertEqual(mock_get_embedding.call_count, 2)
    
    @patch('app.get_embedding')
    def test_search_documents(self, mock_get_embedding):
        """Test searching documents."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Add some test documents first
        doc1 = {
            "text": "MongoDB is a document database with the scalability and flexibility.",
            "metadata": {"source": "Test", "category": "Database"}
        }
        doc2 = {
            "text": "MongoDB Atlas is a cloud service for MongoDB.",
            "metadata": {"source": "Test", "category": "Cloud"}
        }
        
        # Add documents
        self.app.post('/documents', data=json.dumps(doc1), content_type='application/json')
        self.app.post('/documents', data=json.dumps(doc2), content_type='application/json')
        
        # Reset mock for search test
        mock_get_embedding.reset_mock()
        
        # Send search request
        response = self.app.get('/search?q=MongoDB%20Atlas%20cloud&n=2')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("query", data)
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)
        
        # Verify mock was called once for the query
        mock_get_embedding.assert_called_once()
    
    def test_search_missing_query(self):
        """Test search with missing query parameter."""
        # Send search request without query
        response = self.app.get('/search')
        
        # Verify response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
    
    def test_health_check(self):
        """Test health check endpoint."""
        # Send health check request
        response = self.app.get('/health')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("status", data)
        self.assertEqual(data["status"], "ok")
        self.assertIn("documents_indexed", data)
        self.assertIn("documents_metadata", data)

if __name__ == '__main__':
    unittest.main() 