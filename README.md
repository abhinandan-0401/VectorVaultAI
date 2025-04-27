# VectorVault

> Knowledge, Instantly Retrieved

VectorVault is a semantic document search engine that uses OpenAI embeddings and FAISS vector database to provide powerful search capabilities with RAG (Retrieval Augmented Generation).

<div align="center">
  <img src="ui/app_logo.png" alt="VectorVault Logo" width="300"/>
</div>

## Features

- 🔍 **Semantic Search**: Find documents based on meaning, not just keywords
- 📑 **PDF Processing**: Upload and process PDF files up to 100MB with automatic chunking
- 🤖 **VaultGPT**: AI-powered chat interface that uses RAG to answer questions based on your documents 
- 🧠 **OpenAI Integration**: Leverages text-embedding-3-small for embeddings and GPT-4o for RAG
- 💾 **Persistent Storage**: Google Cloud Storage for vector indices, metadata, and PDF files
- 🌐 **REST API**: Simple HTTP endpoints for integration
- 🖥️ **Streamlit UI**: User-friendly interface with dark mode support
- 🐳 **Docker Ready**: Containerized deployment for both development and production

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
  - [Configuration](#configuration)
- [Running the Application](#running-the-application)
  - [Standard Setup](#standard-setup)
  - [Using Docker](#using-docker)
  - [Using Docker Compose](#using-docker-compose)
- [Deployment Options](#deployment-options)
  - [Folder-Based Deployment](#folder-based-deployment)
  - [Google Cloud Run](#google-cloud-run)
- [Usage](#usage)
  - [Uploading PDF Documents](#uploading-pdf-documents)
  - [Searching Documents](#searching-documents)
  - [Using VaultGPT](#using-vaultgpt)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [OpenAI API key](https://platform.openai.com/)
- Git (for cloning the repository)
- Docker (optional, for containerized deployment)
- Google Cloud SDK (optional, for GCP deployment)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/vectorvault.git
   cd vectorvault
   ```

2. Set up a virtual environment:
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r api/requirements.txt  # For API
   pip install -r ui/requirements.txt   # For UI
   ```

### Configuration

Create a `.env` file with your OpenAI API key and other settings:

```
OPENAI_API_KEY=your-openai-api-key-here
EMBEDDING_MODEL=text-embedding-3-small
LLM=gpt-4o
GCS_BUCKET_NAME=your-GCS-bucket-name  # Required for PDF processing and storage
```

## Running the Application

### Standard Setup

1. Start the Flask API backend:
   ```bash
   cd api
   python app.py
   ```
   This starts the API server on `http://localhost:5000`.

2. Start the Streamlit UI in a separate terminal:
   ```bash
   cd ui
   streamlit run streamlit_app.py
   ```
   Access the UI at `http://localhost:8501`.

### Using Docker

Build and run the API:
```bash
docker build -t vector-vault-api -f api/Dockerfile api/
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key -e GCS_BUCKET_NAME=your-GCS-bucket-name vector-vault-api
```

Build and run the UI:
```bash
docker build -t vector-vault-ui -f ui/Dockerfile ui/
docker run -p 8501:8501 -e API_URL=http://localhost:5000 vector-vault-ui
```

### Using Docker Compose

For testing both services together locally:

```bash
# Update the API key in docker-compose.yml first
docker-compose up
```

## Deployment Options

### Folder-Based Deployment

We've organized the application into separate folders for easier deployment:

- `api/` - Contains the Flask backend
- `ui/` - Contains the Streamlit frontend

Run the setup script to copy necessary files:
```bash
# PowerShell on Windows
.\setup_folders.ps1

# Bash on Linux/macOS
bash setup_folders.sh
```

For detailed deployment instructions, see [FOLDER_DEPLOYMENT.md](FOLDER_DEPLOYMENT.md).

### Google Cloud Run

Deploy to Google Cloud Run using the folder-based approach:

1. Create a GCS bucket for storing data:
   ```bash
   gcloud storage buckets create gs://your-GCS-bucket-name --location=$REGION --project=$PROJECT_ID
   ```

2. Deploy the API:
   ```bash
   cd api
   gcloud builds submit --tag gcr.io/$PROJECT_ID/vectorvault-advanced-api .
   gcloud run deploy vectorvault-advanced-api \
     --image gcr.io/$PROJECT_ID/vectorvault-advanced-api \
     --platform managed \
     --region $REGION \
     --allow-unauthenticated \
     --set-env-vars="OPENAI_API_KEY=your-key,GCS_BUCKET_NAME=your-GCS-bucket-name"
   cd ..
   ```

3. Get the API URL and deploy the UI:
   ```bash
   API_URL=$(gcloud run services describe vectorvault-advanced-api --region=$REGION --platform managed --format="value(status.url)")
   
   cd ui
   gcloud builds submit --tag gcr.io/$PROJECT_ID/vectorvault-advanced-ui .
   gcloud run deploy vectorvault-advanced-ui \
     --image gcr.io/$PROJECT_ID/vectorvault-advanced-ui \
     --platform managed \
     --region $REGION \
     --allow-unauthenticated \
     --set-env-vars="API_URL=$API_URL"
   cd ..
   ```

For detailed GCP deployment instructions, see [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md).

## Usage

### Uploading PDF Documents

1. Open the Streamlit UI 
2. Navigate to the "PDF Upload" tab
3. Select a PDF file (up to 100MB)
4. Add optional metadata like source, author, category, and year
5. Click "Process PDF Document"

The system will:
- Split the PDF into semantic chunks
- Generate embeddings for each chunk
- Store both the PDF and its metadata in Google Cloud Storage
- Index the chunks for semantic search

### Searching Documents

1. Navigate to the "Search" tab
2. Enter your search query
3. Set the number of results to return
4. Toggle "Group results by source" if desired
5. Click "Search"

Results are ranked by semantic similarity, showing the most relevant content first.

### Using VaultGPT

1. Navigate to the "VaultGPT" tab
2. Enter your question in the text area
3. Set the number of documents to retrieve as context
4. Click "Ask VaultGPT"

VaultGPT will:
- Retrieve the most relevant document chunks
- Use them as context for generating an AI response
- Display the answer with citations to the source documents

## API Documentation

### Health Check
- `GET /health` - Check system status and view supported features

### Document Management
- `POST /documents/pdf` - Upload and process a PDF document (up to 100MB)

### Search
- `GET /search?q=your+query+here&n=5` - Search for documents
  - `q` or `query`: The search query (required)
  - `n`: Number of results to return (optional, defaults to 5)
  - `group`: Group results by source (optional, defaults to false)

### VaultGPT
- `POST /vaultgpt` - Query the RAG system
  - Request body: `{"query": "your question", "top_n": 5}`

## Project Structure

```
vectorvault/
├── api/                     # API component for deployment
│   ├── app.py               # Flask API backend
│   ├── pdf_processor.py     # PDF processing utility
│   ├── rag_processor.py     # RAG implementation
│   ├── Dockerfile           # API container definition
│   ├── requirements.txt     # API dependencies
│   └── app_logo.png         # Application logo
├── ui/                      # UI component for deployment
│   ├── streamlit_app.py     # Streamlit frontend
│   ├── Dockerfile           # UI container definition
│   ├── requirements.txt     # UI dependencies
│   └── app_logo.png         # Application logo
├── docker-compose.yml       # Docker Compose configuration
├── setup_folders.ps1        # PowerShell setup script
├── setup_folders.sh         # Bash setup script
├── FOLDER_DEPLOYMENT.md     # Folder-based deployment guide
├── GCP_DEPLOYMENT.md        # Google Cloud Platform deployment guide
├── README.md                # This documentation
└── LICENSE                  # MIT License
```

## Testing

To run tests (if tests are available):

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest
```

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Open a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <img src="ui/app_logo.png" alt="VectorVault Logo" width="100"/>
  <p><em>VectorVault - Knowledge, Instantly Retrieved</em><br>
  Powered by OpenAI and FAISS</p>
</div> 