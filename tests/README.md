# VectorVault Tests

This directory contains tests for the VectorVault application. These tests ensure that the core functionality works as expected.

## Test Structure

The tests are organized into several files:

- `test_embedding.py` - Tests for the embedding generation functionality
- `test_document_validation.py` - Tests for document validation functions
- `test_api_endpoints.py` - Tests for the Flask API endpoints
- `test_metadata_persistence.py` - Tests for document metadata persistence
- `test_batch_processing.py` - Tests for batch document processing
- `conftest.py` - Pytest fixtures and configuration

## Running Tests

You can run the tests using pytest:

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_api_endpoints.py

# Run a specific test
pytest tests/test_api_endpoints.py::TestAPIEndpoints::test_health_check
```

## Mocking

The tests use the Python `unittest.mock` library to simulate responses from external services like the OpenAI API. This allows us to test the application without making actual API calls.

## Test Data

The tests create temporary test files and directories where needed, which are automatically cleaned up after tests run.

## Test Coverage

To check test coverage, you can use pytest-cov:

```bash
# Install pytest-cov if not already installed
pip install pytest-cov

# Run tests with coverage report
pytest --cov=app tests/
```

## Writing New Tests

When adding new functionality to VectorVault, please also add corresponding tests. Follow these guidelines:

1. Place tests in the appropriate file based on functionality
2. Mock external services where possible
3. Use the fixtures in `conftest.py` to avoid duplicating setup code
4. Clean up any resources created during tests
5. Write docstrings for test functions to explain what they're testing 