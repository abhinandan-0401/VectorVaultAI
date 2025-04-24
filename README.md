# VectorVault

> Knowledge, Instantly Retrieved

VectorVault is a semantic document search engine that uses OpenAI embeddings and FAISS vector database to provide powerful search capabilities.

<div align="center">
  <img src="ui/app_logo.png" alt="VectorVault Logo" width="300"/>
</div>

## Features

- 🔍 **Semantic Search**: Find documents based on meaning, not just keywords
- 📄 **Document Management**: Add documents individually with rich metadata
- 📚 **Batch Processing**: Upload multiple documents via CSV or JSON files
- 🧠 **AI-Powered**: OpenAI embeddings for state-of-the-art semantic understanding
- 💾 **Persistent Storage**: Local or Google Cloud Storage for vector indices and metadata
- 🌐 **REST API**: Simple HTTP endpoints for integration
- 🖥️ **Streamlit UI**: User-friendly interface with immediate visual feedback
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
  - [Adding Documents](#adding-documents)
  - [Batch Upload](#batch-upload)
  - [Searching Documents](#searching-documents)
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
   pip install -r requirements.txt
   ```

### Configuration

Create a `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your-openai-api-key-here
EMBEDDING_MODEL=text-embedding-3-small
LLM=gpt-4o
GCS_BUCKET_NAME=your-bucket-name  # Optional, for GCS storage
```

## Running the Application

### Standard Setup

1. Start the Flask API backend:
   ```bash
   python app.py
   ```
   This starts the API server on `http://localhost:5000`.

2. Start the Streamlit UI:
   ```bash
   streamlit run streamlit_app.py
   ```
   Access the UI at `http://localhost:8501`.

### Using Docker

Build and run the API:
```bash
docker build -t vector-vault-api -f api/Dockerfile api/
docker run -p 8080:8080 -e OPENAI_API_KEY=your-key vector-vault-api
```

Build and run the UI:
```bash
docker build -t vector-vault-ui -f ui/Dockerfile ui/
docker run -p 8501:8501 -e API_URL=http://localhost:8080 vector-vault-ui
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

1. Deploy the API:
   ```bash
   cd api
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-api .
   gcloud run deploy vector-vault-api --image gcr.io/YOUR_PROJECT_ID/vector-vault-api --platform managed --allow-unauthenticated --set-env-vars="OPENAI_API_KEY=your-key,GCS_BUCKET_NAME=your-bucket"
   cd ..
   ```

2. Get the API URL and deploy the UI:
   ```bash
   $API_URL = (gcloud run services describe vector-vault-api --region=your-region --platform managed --format="value(status.url)")
   
   cd ui
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vector-vault-ui .
   gcloud run deploy vector-vault-ui --image gcr.io/YOUR_PROJECT_ID/vector-vault-ui --platform managed --allow-unauthenticated --set-env-vars="API_URL=$API_URL"
   cd ..
   ```

For detailed GCP deployment instructions, see [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md).

## Usage

### Adding Documents

1. Open the Streamlit UI 
2. Navigate to the "Upload Documents" tab
3. Enter your document text and metadata
4. Click "Upload Document"

### Batch Upload

Upload multiple documents using CSV or JSON format:

#### CSV Format

```csv
text,source,category,author
"MongoDB uses BSON, a binary representation of JSON documents.",MongoDB Docs,Technical,MongoDB Team
```

#### JSON Format

```json
[
  {
    "text": "Your document content here",
    "metadata": {
      "source": "Wikipedia",
      "category": "Science"
    }
  }
]
```

Sample files are available in the `sample_data/` directory.

### Searching Documents

1. Navigate to the "Search" tab
2. Enter your search query
3. Set the number of results to return
4. Click "Search"

Results are ranked by semantic similarity, not just keyword matching.

## API Documentation

### Health Check
- `GET /health` - Check system status

### Document Management
- `POST /documents` - Add a single document
- `POST /documents/batch` - Add multiple documents

### Search
- `GET /search?q=your+query+here&n=5` - Search for documents
  - `q` or `query`: The search query (required)
  - `n`: Number of results to return (optional, defaults to 5)

## Project Structure

```
vectorvault/
├── api/                     # API component for folder-based deployment
│   ├── app.py               # Flask API backend
│   ├── Dockerfile           # API container definition
│   ├── requirements.txt     # API dependencies
│   └── app_logo.png         # Application logo
├── ui/                      # UI component for folder-based deployment
│   ├── streamlit_app.py     # Streamlit frontend
│   ├── Dockerfile           # UI container definition
│   ├── requirements.txt     # UI dependencies
│   └── app_logo.png         # Application logo
├── app.py                   # Flask API (original)
├── streamlit_app.py         # Streamlit UI (original)
├── docker-compose.yml       # Docker Compose configuration
├── setup_folders.ps1        # PowerShell setup script
├── setup_folders.sh         # Bash setup script
├── sample_data/             # Example data for testing
│   ├── mongodb_docs.csv     # Sample CSV data
│   └── mongodb_features.json # Sample JSON data
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