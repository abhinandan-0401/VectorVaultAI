import os
import json
import requests
import time
import sys

def load_sample_data():
    """Load sample data from files into the VectorVault API."""
    API_URL = "http://localhost:5000"
    
    # Check if API is running
    try:
        health = requests.get(f"{API_URL}/health")
        if health.status_code != 200:
            print("❌ API is not running or not responding correctly.")
            print("Please start the Flask API with: python app.py")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running?")
        print("Please start the Flask API with: python app.py")
        return False
    
    # Load CSV sample data
    csv_file = os.path.join("sample_data", "mongodb_docs.csv")
    if os.path.exists(csv_file):
        print(f"📄 Loading sample data from {csv_file}...")
        import pandas as pd
        
        df = pd.read_csv(csv_file)
        documents = []
        
        for _, row in df.iterrows():
            doc = {"text": row["text"]}
            metadata = {}
            for col in df.columns:
                if col != "text" and not pd.isna(row[col]):
                    metadata[col] = row[col]
            if metadata:
                doc["metadata"] = metadata
            documents.append(doc)
        
        response = requests.post(f"{API_URL}/documents/batch", json=documents)
        if response.status_code in [200, 201, 207]:
            print(f"✅ Successfully loaded {len(documents)} documents from CSV.")
        else:
            print(f"❌ Failed to load CSV data: {response.text}")
    
    # Load JSON sample data
    json_file = os.path.join("sample_data", "mongodb_features.json")
    if os.path.exists(json_file):
        print(f"📄 Loading sample data from {json_file}...")
        
        with open(json_file, 'r') as f:
            documents = json.load(f)
        
        response = requests.post(f"{API_URL}/documents/batch", json=documents)
        if response.status_code in [200, 201, 207]:
            print(f"✅ Successfully loaded {len(documents)} documents from JSON.")
        else:
            print(f"❌ Failed to load JSON data: {response.text}")
    
    print("✅ Sample data loading complete!")
    return True

if __name__ == "__main__":
    load_sample_data() 