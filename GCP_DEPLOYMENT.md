# Deploying to Google Cloud Platform

This guide explains how to deploy the VectorVault application to Google Cloud Platform using Cloud Run and Cloud Storage.

## Application Architecture

The application consists of:
1. **Flask backend API** - Handles document indexing, storage, and search
2. **Streamlit web interface** - User-friendly frontend for interacting with the system
3. **Cloud Storage** - Persists the FAISS index and document metadata

In our deployment, both Flask and Streamlit run in the same container, managed by supervisord.

## Prerequisites

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured
2. [Docker](https://docs.docker.com/get-docker/) installed locally
3. A Google Cloud Platform account with billing enabled
4. OpenAI API key for generating embeddings

## Setup Google Cloud Resources

### Create a Cloud Storage Bucket

1. Create a storage bucket for persisting your FAISS index and document metadata:

```bash
# Replace YOUR_BUCKET_NAME with a globally unique bucket name
gsutil mb gs://YOUR_BUCKET_NAME
```

### Set Environment Variables

Create a `.env` file locally for development:

```
OPENAI_API_KEY=your_openai_api_key
GCS_BUCKET_NAME=your_bucket_name
```

## Deploy to Cloud Run

### Build and Deploy

1. Build your Docker container and deploy to Cloud Run:

```bash
# Build the container image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault

# Deploy to Cloud Run
gcloud run deploy vector-vault \
  --image gcr.io/YOUR_PROJECT_ID/vector-vault \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars="OPENAI_API_KEY=your_openai_api_key,GCS_BUCKET_NAME=your_bucket_name"
```

Replace `YOUR_PROJECT_ID`, `your_openai_api_key`, and `your_bucket_name` with your actual values.

**Note:** The memory and CPU settings may need to be adjusted based on your workload. The default settings might not be sufficient for running both Flask and Streamlit.

## Setting Up Service Account Permissions

Your Cloud Run service needs permissions to access the Cloud Storage bucket:

1. Give the Cloud Run service account the Storage Object Admin role:

```bash
# Identify your Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe vector-vault --platform managed --format="value(spec.template.spec.serviceAccountName)")

# Grant Storage Object Admin role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"
```

## Accessing the Application

After deployment, Cloud Run will provide you with a URL to access your application. This URL will serve both:

- The Flask API endpoints (e.g., `https://your-service-url.run.app/search`)
- The Streamlit web interface (e.g., `https://your-service-url.run.app`)

The Streamlit UI will automatically connect to the Flask API running in the same container.

## Local Development with GCP Storage

To develop locally while using GCP Cloud Storage:

1. Authenticate with GCP:

```bash
gcloud auth application-default login
```

2. Set environment variables in your `.env` file:

```
OPENAI_API_KEY=your_openai_api_key
GCS_BUCKET_NAME=your_bucket_name
```

3. Run the application using Docker:

```bash
# Build local Docker image
docker build -t vector-vault .

# Run Docker container
docker run -p 8080:8080 -p 8501:8501 \
  --env-file .env \
  vector-vault
```

Or run Flask and Streamlit separately:

```bash
# Terminal 1 - Run Flask API
python app.py

# Terminal 2 - Run Streamlit
streamlit run streamlit_app.py
```

## Data Persistence

The application will:
- Load the FAISS index and document metadata from Cloud Storage on startup
- Save updates to Cloud Storage whenever documents are added

## Updating the Deployment

To update your Cloud Run service after code changes:

```bash
# Build new container image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault

# Update the service
gcloud run services update vector-vault \
  --image gcr.io/YOUR_PROJECT_ID/vector-vault \
  --platform managed
```

## Troubleshooting

If you encounter issues with your deployment:

1. Check Cloud Run logs in the GCP Console
2. Verify environment variables are set correctly
3. Ensure the service account has proper storage permissions
4. Test locally using the Docker container with GCS credentials 