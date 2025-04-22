#!/usr/bin/env python3
"""
VectorVault Setup Script
------------------------
This script helps set up the VectorVault project by:
1. Checking if the .env file exists
2. Checking if the dependencies are installed
3. Loading sample data if desired
"""

import os
import sys
import json
import subprocess
import importlib.util
from pathlib import Path

def check_env_file():
    """Check if .env file exists and contains API key."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        print("\n❌ .env file not found!")
        
        if env_example.exists():
            print("ℹ️ Creating .env file from .env.example...")
            with open(env_example, 'r') as f:
                env_example_content = f.read()
            
            with open(env_file, 'w') as f:
                f.write(env_example_content)
            
            print("✅ Created .env file. Please edit it to add your OpenAI API key.")
            print("   Then run this script again.")
            return False
        else:
            print("❌ .env.example file not found either!")
            print("Please create a .env file with your OpenAI API key:")
            print("OPENAI_API_KEY = \"your-openai-api-key-here\"")
            print("EMBEDDING_MODEL = \"text-embedding-3-small\"")
            print("LLM = \"gpt-4o\"")
            return False
    
    # Check if API key is set
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    if "your-openai-api-key-here" in env_content or "OPENAI_API_KEY" not in env_content:
        print("\n❌ Please set your OpenAI API key in the .env file!")
        print("Edit the .env file and add your API key, then run this script again.")
        return False
    
    print("\n✅ .env file exists and API key is set.")
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = ["flask", "openai", "faiss-cpu", "python-dotenv", "numpy", "streamlit", "requests", "pandas"]
    missing_packages = []
    
    for package in required_packages:
        spec = importlib.util.find_spec(package.replace("-", "_"))
        if spec is None:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing dependencies: {', '.join(missing_packages)}")
        print("Installing missing dependencies...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("✅ Dependencies installed successfully.")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies.")
            print("Please run: pip install -r requirements.txt")
            return False
    else:
        print("\n✅ All dependencies are installed.")
    
    return True

def load_sample_data():
    """Ask if sample data should be loaded when the app starts."""
    while True:
        response = input("\nWould you like to load sample data when you start the app? (y/n): ").lower()
        if response in ['y', 'yes']:
            print("✅ Set to load sample data.")
            return True
        elif response in ['n', 'no']:
            print("✅ Will not load sample data.")
            return False
        else:
            print("Please answer 'y' or 'n'.")

def create_sample_data_loader():
    """Create a sample data loader script."""
    script_content = """import os
import json
import requests
import time
import sys

def load_sample_data():
    \"\"\"Load sample data from files into the VectorVault API.\"\"\"
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
"""
    
    with open("load_sample_data.py", 'w') as f:
        f.write(script_content)
    
    print("✅ Created load_sample_data.py script.")

def main():
    """Main setup function."""
    print("\n🧠 VectorVault Setup\n" + "="*20)
    
    # Check environment file
    if not check_env_file():
        return
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Ask about sample data
    load_data = load_sample_data()
    if load_data:
        create_sample_data_loader()
    
    # Final instructions
    print("\n✅ Setup complete!")
    print("\nTo start VectorVault:")
    print("1. In one terminal, start the Flask backend:")
    print("   python app.py")
    
    if load_data:
        print("\n2. To load sample data (optional):")
        print("   python load_sample_data.py")
    
    print("\n3. In another terminal, start the Streamlit frontend:")
    print("   streamlit run streamlit_app.py")
    
    print("\nHappy searching! 🚀")

if __name__ == "__main__":
    main() 