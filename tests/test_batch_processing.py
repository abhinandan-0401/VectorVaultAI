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

class TestBatchProcessing(unittest.TestCase):
    """Test cases for batch processing functionality."""
    
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
    def test_batch_empty_list(self, mock_get_embedding):
        """Test batch processing with an empty list."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Send empty list
        response = self.app.post(
            '/documents/batch',
            data=json.dumps([]),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 207)  # Multi-Status
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 0)
        
        # Verify no documents were added
        self.assertEqual(flask_app.index.ntotal, 0)
        self.assertEqual(len(flask_app.doc_store), 0)
        
        # Verify mock was not called
        mock_get_embedding.assert_not_called()
    
    @patch('app.get_embedding')
    def test_batch_all_valid(self, mock_get_embedding):
        """Test batch processing with all valid documents."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Create batch of valid documents
        batch = [
            {
                "text": "MongoDB is a document database with scalability and flexibility.",
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
        
        # Send batch
        response = self.app.post(
            '/documents/batch',
            data=json.dumps(batch),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 207)  # Multi-Status
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("results", data)
        
        # All documents should be processed successfully
        success_count = sum(1 for r in data["results"] if r.get("status") == "success")
        self.assertEqual(success_count, 3)
        self.assertEqual(len(data["results"]), 3)
        
        # Verify all documents were added
        self.assertEqual(flask_app.index.ntotal, 3)
        self.assertEqual(len(flask_app.doc_store), 3)
        
        # Verify metadata was stored correctly
        categories = [doc["metadata"]["category"] for doc in flask_app.doc_store.values()]
        self.assertIn("Database", categories)
        self.assertIn("Cloud", categories)
        self.assertIn("Tool", categories)
        
        # Verify mock was called for each document
        self.assertEqual(mock_get_embedding.call_count, 3)
    
    @patch('app.get_embedding')
    def test_batch_all_invalid(self, mock_get_embedding):
        """Test batch processing with all invalid documents."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Create batch of invalid documents
        batch = [
            {
                "text": "Short",  # Too short
                "metadata": {"source": "Test"}
            },
            {
                "metadata": {"source": "Test"}  # Missing text
            },
            {
                "text": "Another short",  # Too short
                "metadata": "invalid"  # Invalid metadata type
            }
        ]
        
        # Send batch
        response = self.app.post(
            '/documents/batch',
            data=json.dumps(batch),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 207)  # Multi-Status
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("results", data)
        
        # All documents should fail validation
        error_count = sum(1 for r in data["results"] if r.get("status") == "error")
        self.assertEqual(error_count, 3)
        self.assertEqual(len(data["results"]), 3)
        
        # Verify no documents were added
        self.assertEqual(flask_app.index.ntotal, 0)
        self.assertEqual(len(flask_app.doc_store), 0)
        
        # Verify mock was not called
        mock_get_embedding.assert_not_called()
    
    @patch('app.get_embedding')
    def test_batch_mixed_validity(self, mock_get_embedding):
        """Test batch processing with mix of valid and invalid documents."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Create mixed batch
        batch = [
            {
                "text": "MongoDB is a document database with scalability and flexibility.",
                "metadata": {"source": "Test", "category": "Database"}
            },
            {
                "metadata": {"source": "Test"}  # Missing text
            },
            {
                "text": "MongoDB Compass is the GUI for MongoDB.",
                "metadata": {"source": "Test", "category": "Tool"}
            }
        ]
        
        # Send batch
        response = self.app.post(
            '/documents/batch',
            data=json.dumps(batch),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 207)  # Multi-Status
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("results", data)
        
        # Check success/error counts
        success_count = sum(1 for r in data["results"] if r.get("status") == "success")
        error_count = sum(1 for r in data["results"] if r.get("status") == "error")
        self.assertEqual(success_count, 2)
        self.assertEqual(error_count, 1)
        self.assertEqual(len(data["results"]), 3)
        
        # Verify only valid documents were added
        self.assertEqual(flask_app.index.ntotal, 2)
        self.assertEqual(len(flask_app.doc_store), 2)
        
        # Verify mock was called for valid documents only
        self.assertEqual(mock_get_embedding.call_count, 2)
    
    @patch('app.get_embedding')
    def test_batch_size_limit(self, mock_get_embedding):
        """Test batch size limit enforcement."""
        # Set up the mock
        mock_get_embedding.return_value = self.mock_embedding
        
        # Create oversized batch (101 documents)
        batch = []
        for i in range(101):
            batch.append({
                "text": f"This is test document {i} with sufficient length to be valid.",
                "metadata": {"source": "Test", "number": i}
            })
        
        # Send batch
        response = self.app.post(
            '/documents/batch',
            data=json.dumps(batch),
            content_type='application/json'
        )
        
        # Verify response - should reject for being too large
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertIn("Batch size limited to 100 documents", data["error"])
        
        # Verify no documents were added
        self.assertEqual(flask_app.index.ntotal, 0)
        self.assertEqual(len(flask_app.doc_store), 0)
        
        # Verify mock was not called
        mock_get_embedding.assert_not_called()
    
    def test_batch_non_array_input(self):
        """Test batch processing with non-array input."""
        # Send object instead of array
        response = self.app.post(
            '/documents/batch',
            data=json.dumps({"text": "This is not an array"}),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertIn("Expected a JSON array", data["error"])
        
        # Verify no documents were added
        self.assertEqual(flask_app.index.ntotal, 0)
        self.assertEqual(len(flask_app.doc_store), 0)

if __name__ == '__main__':
    unittest.main() 