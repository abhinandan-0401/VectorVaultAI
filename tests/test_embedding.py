import os
import sys
import unittest
import numpy as np
from unittest.mock import patch, MagicMock
import json

# Add parent directory to path to import app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import get_embedding

class TestEmbedding(unittest.TestCase):
    """Test cases for embedding functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock response for the OpenAI client
        self.mock_embedding = np.random.rand(1536).tolist()  # OpenAI embeddings are 1536 dimensions
        
    @patch('app.client.embeddings.create')
    def test_get_embedding(self, mock_create):
        """Test the get_embedding function."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = self.mock_embedding
        mock_create.return_value = mock_response
        
        # Call the function with test data
        test_text = "This is a test document for MongoDB."
        result = get_embedding(test_text)
        
        # Verify the result
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (1536,))
        self.assertEqual(result.dtype, np.float32)
        
        # Verify the mock was called correctly
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        self.assertEqual(kwargs['input'], [test_text])
        
    @patch('app.client.embeddings.create')
    def test_get_embedding_error_handling(self, mock_create):
        """Test error handling in get_embedding function."""
        # Set up the mock to raise an exception
        mock_create.side_effect = Exception("API Error")
        
        # Call the function and check if it raises the expected error
        test_text = "This is a test document for MongoDB."
        with self.assertRaises(ValueError) as context:
            get_embedding(test_text)
        
        # Verify the error message
        self.assertIn("Failed to generate embedding", str(context.exception))

if __name__ == '__main__':
    unittest.main() 