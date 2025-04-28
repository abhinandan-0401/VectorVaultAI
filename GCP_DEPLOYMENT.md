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

## MongoDB Atlas Configuration

1. Create a MongoDB Atlas account at [https://www.mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster (M0 free tier is sufficient for testing)
3. Configure database access:
   - Create a database user with read/write permissions
   - Store credentials securely
4. Configure network access:
   - Add your IP address for development
   - For production, allow access from anywhere (0.0.0.0/0) or specific GCP IP ranges

5. Get your connection string:
   ```
   mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority
   ```

### Creating the Vector Search Index

After deploying your application for the first time, you need to create a vector search index in MongoDB Atlas:

1. Log in to your MongoDB Atlas account
2. Navigate to your cluster
3. Click on "Search" in the left navigation menu
4. Click "Create Search Index"
5. Select your database and the "documents" collection
6. Choose "JSON Editor" for the configuration method
7. Enter the following index definition:
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
8. Set the index name to "vector_index" (this is important - it must match the name in the code)
9. Click "Create Search Index"

The index will take a few minutes to build, especially if you already have documents in your collection.

### Environment Variables for Authentication

Add these environment variables to your Cloud Run services:


#### MongoDB Configuration
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority
MONGODB_DATABASE=vectorvault

#### JWT Authentication
JWT_SECRET_KEY=your-secret-key-here  # Generate a secure random key
JWT_ACCESS_TOKEN_EXPIRES=86400  # 24 hours in seconds

#### Admin User Setup (First Run Only)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-initial-password
ADMIN_EMAIL=admin@example.com

### Update Cloud Run Deployment

Update memory allocation for the API service to handle vector search:

gcloud run deploy vectorvault-advanced-api \
  --image gcr.io/$PROJECT_ID/vectorvault-advanced-api \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 4Gi \  # Increased from 2Gi
  --cpu 2 \        # Increased from 1
  --set-env-vars="OPENAI_API_KEY=your-key,GCS_BUCKET_NAME=your-GCS-bucket-name,MONGODB_URI=your-mongodb-uri,MONGODB_DATABASE=vectorvault,JWT_SECRET_KEY=your-secret-key"
 
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