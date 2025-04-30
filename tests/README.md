# VectorVault Tests

This directory contains tests for the VectorVault application.

## Test Organization

- **test_api_endpoints.py**: Tests for the core API endpoints
- **test_batch_processing.py**: Tests for batch document processing
- **test_document_validation.py**: Tests for document validation
- **test_embedding.py**: Tests for embedding generation
- **test_metadata_persistence.py**: Tests for metadata persistence

## Running Tests

### Running All Tests

```bash
python -m unittest discover -s tests
```

### Running Specific Tests

```bash
python -m unittest tests.test_api_endpoints
python -m unittest tests.test_embedding
``` 