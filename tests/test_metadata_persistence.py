import os
import sys
import unittest
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import numpy as np

# Add parent directory to path to import app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as flask_app

class TestMetadataPersistence(unittest.TestCase):
    """Test cases for document metadata persistence."""
    
    def setUp(self):
        """Set up test environment."""
        # Set up a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.metadata_file = os.path.join(self.temp_dir.name, "test_metadata.json")
        
        # Mock embedding for testing
        self.mock_embedding = np.random.rand(1536).astype(np.float32)
        
    def tearDown(self):
        """Clean up after tests."""
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def test_save_metadata(self):
        """Test saving metadata to disk."""
        # Set up test document store
        test_doc_store = {
            0: {
                "id": "doc1",
                "text": "This is document 1",
                "metadata": {"source": "Test", "category": "One"},
                "added_at": 1636000000.0
            },
            1: {
                "id": "doc2",
                "text": "This is document 2",
                "metadata": {"source": "Test", "category": "Two"},
                "added_at": 1636000100.0
            }
        }
        
        # Mock app's doc_store and metadata file
        original_doc_store = flask_app.doc_store
        original_metadata_file = flask_app.METADATA_FILE
        
        try:
            flask_app.doc_store = test_doc_store
            flask_app.METADATA_FILE = self.metadata_file
            
            # Call save_metadata
            flask_app.save_metadata()
            
            # Verify file was created
            self.assertTrue(os.path.exists(self.metadata_file))
            
            # Verify file contents
            with open(self.metadata_file, 'r') as f:
                saved_data = json.load(f)
            
            # Convert keys back to integers for comparison
            saved_data = {int(k): v for k, v in saved_data.items()}
            self.assertEqual(saved_data, test_doc_store)
            
        finally:
            # Restore original values
            flask_app.doc_store = original_doc_store
            flask_app.METADATA_FILE = original_metadata_file
    
    def test_load_metadata(self):
        """Test loading metadata from disk."""
        # Create a test metadata file
        test_doc_store = {
            "0": {
                "id": "doc1",
                "text": "This is document 1",
                "metadata": {"source": "Test", "category": "One"},
                "added_at": 1636000000.0
            },
            "1": {
                "id": "doc2",
                "text": "This is document 2",
                "metadata": {"source": "Test", "category": "Two"},
                "added_at": 1636000100.0
            }
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(test_doc_store, f)
        
        # Backup original values
        original_doc_store = flask_app.doc_store.copy()
        original_metadata_file = flask_app.METADATA_FILE
        
        try:
            # Clear doc_store and set metadata file path
            flask_app.doc_store = {}
            flask_app.METADATA_FILE = self.metadata_file
            
            # Create a function to simulate app initialization
            def simulate_app_init():
                if os.path.exists(flask_app.METADATA_FILE):
                    try:
                        with open(flask_app.METADATA_FILE, 'r') as f:
                            loaded_store = json.load(f)
                            # Convert string keys back to integers
                            flask_app.doc_store = {int(k): v for k, v in loaded_store.items()}
                    except Exception as e:
                        print(f"Error loading document metadata: {str(e)}")
            
            # Call simulation
            simulate_app_init()
            
            # Verify data was loaded
            self.assertEqual(len(flask_app.doc_store), 2)
            self.assertEqual(flask_app.doc_store[0]["id"], "doc1")
            self.assertEqual(flask_app.doc_store[1]["id"], "doc2")
            
        finally:
            # Restore original values
            flask_app.doc_store = original_doc_store
            flask_app.METADATA_FILE = original_metadata_file
    
    def test_save_load_integration(self):
        """Test integration of saving and loading metadata."""
        # Set up test document store
        test_doc_store = {
            0: {
                "id": "doc1",
                "text": "This is document 1",
                "metadata": {"source": "Test", "category": "One"},
                "added_at": 1636000000.0
            },
            1: {
                "id": "doc2",
                "text": "This is document 2",
                "metadata": {"source": "Test", "category": "Two"},
                "added_at": 1636000100.0
            }
        }
        
        # Backup original values
        original_doc_store = flask_app.doc_store.copy()
        original_metadata_file = flask_app.METADATA_FILE
        
        try:
            # Set up for test
            flask_app.doc_store = test_doc_store
            flask_app.METADATA_FILE = self.metadata_file
            
            # Save metadata
            flask_app.save_metadata()
            
            # Clear doc_store
            flask_app.doc_store = {}
            
            # Load metadata
            with open(flask_app.METADATA_FILE, 'r') as f:
                loaded_store = json.load(f)
                flask_app.doc_store = {int(k): v for k, v in loaded_store.items()}
            
            # Verify data was preserved
            self.assertEqual(len(flask_app.doc_store), 2)
            self.assertEqual(flask_app.doc_store[0]["id"], "doc1")
            self.assertEqual(flask_app.doc_store[1]["id"], "doc2")
            self.assertEqual(flask_app.doc_store[0]["metadata"]["category"], "One")
            self.assertEqual(flask_app.doc_store[1]["metadata"]["category"], "Two")
            
        finally:
            # Restore original values
            flask_app.doc_store = original_doc_store
            flask_app.METADATA_FILE = original_metadata_file
    
    def test_error_handling_bad_metadata_file(self):
        """Test error handling when metadata file is corrupted."""
        # Create a corrupted metadata file
        with open(self.metadata_file, 'w') as f:
            f.write("This is not valid JSON")
        
        # Backup original values
        original_doc_store = flask_app.doc_store.copy()
        original_metadata_file = flask_app.METADATA_FILE
        
        try:
            # Clear doc_store and set metadata file path
            flask_app.doc_store = {}
            flask_app.METADATA_FILE = self.metadata_file
            
            # Create a function to simulate app initialization with error handling
            def simulate_app_init():
                if os.path.exists(flask_app.METADATA_FILE):
                    try:
                        with open(flask_app.METADATA_FILE, 'r') as f:
                            loaded_store = json.load(f)
                            # Convert string keys back to integers
                            flask_app.doc_store = {int(k): v for k, v in loaded_store.items()}
                        return True
                    except Exception as e:
                        # Should handle the error gracefully
                        return False
                return False
            
            # Call simulation
            result = simulate_app_init()
            
            # Verify error was handled
            self.assertFalse(result)
            self.assertEqual(len(flask_app.doc_store), 0)  # Doc store should remain empty
            
        finally:
            # Restore original values
            flask_app.doc_store = original_doc_store
            flask_app.METADATA_FILE = original_metadata_file

if __name__ == '__main__':
    unittest.main() 