# Folder-based Deployment for VectorVault

This guide explains how to deploy the VectorVault application using a folder-based structure on Google Cloud Platform.

## Architecture

The application is separated into two folders:
1. **api/** - Contains the Flask API backend for document processing and vector search
2. **ui/** - Contains the Streamlit UI frontend

Each component is deployed as a separate Cloud Run service, with the UI connecting to the API. The system uses:
- **MongoDB Atlas** for vector storage and semantic search
- **Google Cloud Storage** for storing PDF files
- **OpenAI API** for generating text embeddings and powering RAG functionality

## Prerequisites

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
2. [Docker](https://docs.docker.com/get-docker/) installed
3. A Google Cloud Platform account with billing enabled
4. OpenAI API key for generating embeddings

## File Organization

### API Folder
- `app.py` - Flask application
- `requirements.txt` - API dependencies
- `Dockerfile` - Container definition for API
- `app_logo.png` - Logo for API

### UI Folder
- `streamlit_app.py` - Streamlit application
- `requirements.txt` - UI dependencies
- `Dockerfile` - Container definition for UI
- `app_logo.png` - Logo for UI

## Deployment Steps

### 1. Setup the Folder Structure (if not already done)

Use the provided setup scripts to copy necessary files to the folder structure:

```bash
# PowerShell on Windows
.\setup_folders.ps1

# Bash on Linux/macOS
bash setup_folders.sh
```

### 2. Set Project ID and Region

```bash
# List available projects
gcloud projects list

# Set the active project
gcloud config set project YOUR_PROJECT_ID

# List available regions
gcloud compute regions list

# Set your preferred region (choose one close to your users)
# Common regions: us-central1, us-east1, europe-west1, asia-east1, asia-south1
gcloud config set run/region YOUR_REGION
```

**Note:** Remember your chosen region as you'll need it for subsequent commands.

### 3. Enable Required Services

```bash
# Enable required services
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

### 4. Create Cloud Storage Bucket

```bash
# Replace YOUR_BUCKET_NAME with a globally unique bucket name
gsutil mb -l YOUR_REGION gs://YOUR_BUCKET_NAME
```

### 5. Set Up MongoDB Atlas

1. Create a MongoDB Atlas account at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster (M0 free tier is sufficient for testing)
3. Configure database access:
   - Create a database user with read/write permissions
   - Store credentials securely
4. Configure network access:
   - Add your development IP address
   - For production, allow access from anywhere (0.0.0.0/0) or specific GCP IP ranges
5. Get your connection string:
   ```
   mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority
   ```

6. After initial deployment, create a vector search index:
   - Log in to MongoDB Atlas dashboard
   - Navigate to your cluster
   - Click on "Search" in the left navigation
   - Click "Create Search Index"
   - Select your database and the "documents" collection
   - Choose "JSON Editor" for configuration method
   - Enter the following index definition:
     ```json
     {
       "mappings": {
         "dynamic": true,
         "fields": {
           "embedding": {
             "type": "knnVector",
             "dimensions": 1536,
             "similarity": "cosine"
           }
         }
       }
     }
     ```
   - Set the index name to "vector_index"
   - Click "Create Search Index"

### 6. Deploy the API Service

```bash
# Navigate to the API directory
cd api

# Submit the build (using default Dockerfile name)
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-api .

# Deploy to Cloud Run
gcloud run deploy vector-vault-api \
  --image gcr.io/YOUR_PROJECT_ID/vector-vault-api \
  --platform managed \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars="OPENAI_API_KEY=your-openai-api-key,GCS_BUCKET_NAME=your-bucket-name"

# Go back to the root folder
cd ..
```

### 7. Set Storage Permissions for API Service

```bash
# Get the service account
API_SERVICE_ACCOUNT=$(gcloud run services describe vector-vault-api --platform managed --region YOUR_REGION --format="value(spec.template.spec.serviceAccountName)")

# Grant Storage Object Admin role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"
```

### 8. Deploy the UI Service

#### For Linux/macOS

```bash
# Get the API URL to set as an environment variable
API_URL=$(gcloud run services describe vector-vault-api --platform managed --region YOUR_REGION --format="value(status.url)")

# Navigate to the UI directory
cd ui

# Submit the build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-ui .

# Deploy to Cloud Run
gcloud run deploy vector-vault-ui \
  --image gcr.io/YOUR_PROJECT_ID/vector-vault-ui \
  --platform managed \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars="API_URL=$API_URL"

# Go back to the root folder
cd ..
```

#### For Windows PowerShell

```powershell
# Get the API URL and store it in a PowerShell variable
$API_URL = (gcloud run services describe vector-vault-api --platform managed --region YOUR_REGION --format="value(status.url)")

# Navigate to the UI directory
cd ui

# Submit the build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-ui .

# Deploy to Cloud Run
gcloud run deploy vector-vault-ui --image gcr.io/YOUR_PROJECT_ID/vector-vault-ui --platform managed --region YOUR_REGION --allow-unauthenticated --memory 512Mi --set-env-vars="API_URL=$API_URL"

# Go back to the root folder
cd ..
```

#### For Windows Command Prompt

```cmd
REM Get the API URL
FOR /F "tokens=*" %%g IN ('gcloud run services describe vector-vault-api --platform managed --region YOUR_REGION --format="value(status.url)"') do (SET API_URL=%%g)

REM Navigate to the UI directory
cd ui

REM Submit the build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-ui .

REM Deploy to Cloud Run
gcloud run deploy vector-vault-ui --image gcr.io/YOUR_PROJECT_ID/vector-vault-ui --platform managed --region YOUR_REGION --allow-unauthenticated --memory 512Mi --set-env-vars="API_URL=%API_URL%"

REM Go back to the root folder
cd ..
```

### 9. Access the Deployed Application

```bash
# Get the UI URL
STREAMLIT_URL=$(gcloud run services describe vector-vault-ui --platform managed --region YOUR_REGION --format="value(status.url)")
echo "Access your application at: $STREAMLIT_URL"
```

## Using Secrets for API Keys (Recommended)

For better security, use Secret Manager instead of environment variables:

```bash
# Create a secret for the OpenAI API key
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-

# Grant the API service access to the secret
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:$API_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# Update the API deployment to use the secret
gcloud run deploy vector-vault-api \
  --image gcr.io/YOUR_PROJECT_ID/vector-vault-api \
  --platform managed \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars="GCS_BUCKET_NAME=your-bucket-name" \
  --update-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

## Local Testing

You can test the individual components locally before deployment.

### Test the API Locally

```bash
cd api

# Build the Docker image
docker build -t vector-vault-api .

# Run the container
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-openai-api-key \
  -e GCS_BUCKET_NAME=your-bucket-name \
  vector-vault-api

cd ..
```

### Test the UI Locally

```bash
cd ui

# Build the Docker image
docker build -t vector-vault-ui .

# Run the container (connecting to the local API)
docker run -p 8501:8501 \
  -e API_URL=http://localhost:8080 \
  vector-vault-ui

cd ..
```

## Test with Docker Compose

For testing both services together locally, use the provided `docker-compose.yml` file:

```bash
# Update your API key in docker-compose.yml first
# Then run both services
docker-compose up
```

## Updating the Deployment

To update either service after making changes:

### Update the API

```bash
cd api
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-api .
gcloud run deploy vector-vault-api --image gcr.io/YOUR_PROJECT_ID/vector-vault-api --region YOUR_REGION
cd ..
```

### Update the UI

```bash
cd ui
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-ui .
gcloud run deploy vector-vault-ui --image gcr.io/YOUR_PROJECT_ID/vector-vault-ui --region YOUR_REGION
cd ..
```

## Troubleshooting

### API Connection Issues

If the UI can't connect to the API, check:

1. The `API_URL` environment variable is set correctly in the UI service
2. Both services are deployed in the same region
3. The API service is allowing unauthenticated access

### OpenAI API Key Issues

If you see an error like `The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable`:

1. Verify the OPENAI_API_KEY environment variable is set correctly
2. For production, use Secret Manager instead of environment variables
3. Check logs: `gcloud run services logs read vector-vault-api --region YOUR_REGION`

## API Environment Variables

When deploying the API, you need to set these key environment variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
EMBEDDING_MODEL=text-embedding-3-small  # Default model
LLM=gpt-4o  # Default LLM for RAG

# MongoDB Configuration
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority
MONGODB_DATABASE=vectorvault  # Or your preferred database name

# GCS Configuration
GCS_BUCKET_NAME=your-bucket-name  # For PDF storage

# JWT Authentication
JWT_SECRET_KEY=your-secure-secret-key
JWT_ACCESS_TOKEN_EXPIRES=86400  # 24 hours in seconds
``` 