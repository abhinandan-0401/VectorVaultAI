# Testing Your GCP Deployment

This document provides a guide to testing your GCP-ready application locally before deployment.

## Prerequisites

Before testing, make sure you have:

1. Python 3.10+ installed
2. Docker installed (for Docker-based tests)
3. An OpenAI API key (can be a test key for mocked tests)
4. The required Python packages: `pip install -r requirements.txt`

## 1. Unit Testing GCS Integration

The `test_gcs_integration.py` script tests Google Cloud Storage integration without requiring actual GCS credentials:

```bash
# Run the GCS integration tests
python test_gcs_integration.py
```

This test uses mocks to verify the GCS integration code will work correctly when deployed.

## 2. API Endpoint Testing

The `test_api_endpoints.py` script tests the Flask API endpoints:

```bash
# Run the API endpoint tests
python test_api_endpoints.py
```

This validates that all your API endpoints work as expected with the new GCS integration.

## 3. Docker Deployment Testing

The `test_docker_deployment.sh` script builds and tests the entire application in a Docker container:

```bash
# Make the script executable
chmod +x test_docker_deployment.sh

# Run the Docker deployment test
./test_docker_deployment.sh
```

This script:
1. Builds the Docker image with your code
2. Runs the container with test environment variables
3. Tests both API endpoints and Streamlit UI
4. Provides detailed feedback on test results

## Testing With Real GCS Credentials (Optional)

If you want to test with an actual GCS bucket:

1. Create a test bucket in your GCP project
2. Set up authentication:
   ```bash
   gcloud auth application-default login
   ```
3. Set environment variables for testing:
   ```bash
   export GCS_BUCKET_NAME=your-test-bucket
   export OPENAI_API_KEY=your-openai-key
   ```
4. Run the application:
   ```bash
   python app.py
   ```

## Manual Testing Checklist

Once your app is running (either via Docker or locally), manually verify:

- [ ] Health endpoint returns storage info: http://localhost:8080/api/health
- [ ] Streamlit UI loads correctly: http://localhost:8080
- [ ] Adding a document works and persists to storage
- [ ] Searching for documents returns expected results
- [ ] Batch document upload works correctly

## Troubleshooting

If you encounter issues:

1. Check the logs: `docker logs vectorvault-test`
2. Verify environment variables are set correctly
3. Ensure GCP credentials are available (if testing with real GCS)
4. Confirm nginx configuration is correct if UI or API routing fails

## Next Steps

After all tests pass, you're ready to deploy to GCP Cloud Run following the 
instructions in `GCP_DEPLOYMENT.md`. 