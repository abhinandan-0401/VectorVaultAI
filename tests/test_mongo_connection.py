import pymongo
import sys

# Replace with your actual connection string
connection_string = "mongodb+srv://username:password@vectorvault.tbmppar.mongodb.net/?retryWrites=true&w=majority&appName=VectorVault"
database_name = "vectorvault"  # Replace with your database name

def test_connection(uri, db_name):
    try:
        # Create a client
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Force a connection to verify the URI
        client.server_info()
        
        print("✅ Connection successful!")
        
        # Check if we can access the database
        db = client[db_name]
        collections = db.list_collection_names()
        
        print(f"✅ Successfully accessed database '{db_name}'")
        print(f"Collections in database: {collections if collections else 'No collections yet'}")
        
        # Create a test collection (optional)
        if "connection_test" not in collections:
            db.create_collection("connection_test")
            print("✅ Successfully created a test collection")
            
            # Clean up by removing the test collection
            db.drop_collection("connection_test")
            print("✅ Successfully removed the test collection")
        
        return True
    except pymongo.errors.ConnectionFailure as e:
        print(f"❌ Connection failed: {e}")
        return False
    except pymongo.errors.OperationFailure as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()
            print("Connection closed")

if __name__ == "__main__":
    # If connection string is provided as argument, use it
    if len(sys.argv) > 1:
        connection_string = sys.argv[1]
    
    if len(sys.argv) > 2:
        database_name = sys.argv[2]
    
    success = test_connection(connection_string, database_name)
    if not success:
        print("❌ Connection failed")
        sys.exit(1)