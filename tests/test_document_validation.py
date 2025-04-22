import os
import sys
import unittest

# Add parent directory to path to import app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import validate_document

class TestDocumentValidation(unittest.TestCase):
    """Test cases for document validation functionality."""
    
    def test_valid_document(self):
        """Test validation with a valid document."""
        # Valid document with text field
        doc = {
            "text": "This is a valid document with sufficient length.",
            "metadata": {
                "source": "Test",
                "category": "Validation"
            }
        }
        errors = validate_document(doc)
        self.assertEqual(errors, [])
        
    def test_valid_document_with_content(self):
        """Test validation with a valid document using 'content' field."""
        # Valid document with content field
        doc = {
            "content": "This is a valid document with sufficient length.",
            "metadata": {
                "source": "Test",
                "category": "Validation"
            }
        }
        errors = validate_document(doc)
        self.assertEqual(errors, [])
        
    def test_missing_text_and_content(self):
        """Test validation when both text and content fields are missing."""
        # Invalid document with no text or content
        doc = {
            "metadata": {
                "source": "Test",
                "category": "Validation"
            }
        }
        errors = validate_document(doc)
        self.assertIn("Missing 'text' or 'content' field", errors)
        
    def test_too_short_text(self):
        """Test validation with text that is too short."""
        # Invalid document with short text
        doc = {
            "text": "Too short",
            "metadata": {
                "source": "Test"
            }
        }
        errors = validate_document(doc)
        self.assertIn("Document text is too short", errors)
        
    def test_invalid_metadata_type(self):
        """Test validation with invalid metadata type."""
        # Invalid document with non-dict metadata
        doc = {
            "text": "This is a valid document with sufficient length.",
            "metadata": "This should be a dictionary, not a string"
        }
        errors = validate_document(doc)
        self.assertIn("Metadata must be a JSON object", errors)
        
    def test_multiple_validation_errors(self):
        """Test validation with multiple errors."""
        # Document with multiple issues
        doc = {
            "text": "Short",
            "metadata": "Invalid metadata"
        }
        errors = validate_document(doc)
        self.assertEqual(len(errors), 2)
        self.assertIn("Document text is too short", errors)
        self.assertIn("Metadata must be a JSON object", errors)

if __name__ == '__main__':
    unittest.main() 