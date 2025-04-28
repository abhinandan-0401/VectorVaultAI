import os
import logging
from datetime import datetime, timedelta
from functools import wraps
import bcrypt
from flask import request, jsonify, g
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt_identity, 
    jwt_required, get_jwt
)
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# Role-based access control
ROLES = {
    "admin": ["admin", "editor", "reader"],
    "editor": ["editor", "reader"],
    "reader": ["reader"]
}

jwt = JWTManager()

def init_auth(app, db):
    """Initialize authentication with the Flask app"""
    jwt.init_app(app)
    
    # JWT configuration
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    if not app.config["JWT_SECRET_KEY"]:
        app.config["JWT_SECRET_KEY"] = "dev-secret-key-not-for-production"
        logger.warning("JWT_SECRET_KEY not set, using insecure default!")
        
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
    
    # Create default admin user if specified and doesn't exist
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL")
    
    if admin_username and admin_password and admin_email:
        if not db.users.find_one({"username": admin_username}):
            logger.info(f"Creating default admin user: {admin_username}")
            hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
            db.users.insert_one({
                "username": admin_username,
                "password": hashed_password,
                "email": admin_email,
                "role": "admin",
                "created_at": datetime.utcnow(),
                "last_login": None
            })
    
    # Register callback to check if the JWT is revoked
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token = db.revoked_tokens.find_one({"jti": jti})
        return token is not None

    @app.before_request
    def set_db_on_g():
        g.db = db

def role_required(roles):
    """Decorator to require specific roles for access"""
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user_id = get_jwt_identity()
            claims = get_jwt()
            user_role = claims.get("role", "reader")  # Default to reader
            
            if user_role in roles:
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "Insufficient permissions"}), 403
        return decorator
    return wrapper

def get_current_user_id():
    """Get the current user ID or None if not authenticated"""
    try:
        return get_jwt_identity()
    except:
        return None

def register_user(db, username, password, email, role="reader"):
    """Register a new user"""
    try:
        # Check if username already exists
        if db.users.find_one({"username": username}):
            return None, "Username already exists"
        
        # Check if email already exists
        if db.users.find_one({"email": email}):
            return None, "Email already exists"
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user = {
            "username": username,
            "password": hashed_password,
            "email": email,
            "role": role,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        result = db.users.insert_one(user)
        user_id = str(result.inserted_id)
        
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "role": role
        }
        
        return user_data, None
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return None, str(e)

def authenticate_user(db, username, password):
    """Authenticate a user"""
    try:
        user = db.users.find_one({"username": username})
        
        if not user:
            return None, None, "Invalid username or password"
        
        if not bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            return None, None, "Invalid username or password"
            
        # Update last login
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Create access token
        access_token = create_access_token(
            identity=str(user["_id"]),
            additional_claims={"role": user["role"]}
        )
        
        user_data = {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
        
        return access_token, user_data, None
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        return None, None, str(e)

def get_current_user(db):
    """Get the current authenticated user"""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return None
        
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None
        
        return {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None