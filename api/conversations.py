import logging
from datetime import datetime
from bson.objectid import ObjectId
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self, db):
        self.db = db
    
    def create_conversation(self, user_id: str, title: str, first_message: Dict[str, Any], 
                           assistant_response: Dict[str, Any]) -> Optional[str]:
        """Create a new conversation with initial messages"""
        try:
            conversation = {
                "user_id": user_id,
                "title": title,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "messages": [
                    first_message,
                    assistant_response
                ]
            }
            
            result = self.db.conversations.insert_one(conversation)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            return None
    
    def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of conversations for a user"""
        try:
            conversations = list(self.db.conversations.find(
                {"user_id": user_id},
                {"title": 1, "created_at": 1, "updated_at": 1}
            ).sort("updated_at", -1))
            
            return [{
                "_id": str(conv["_id"]),
                "title": conv["title"],
                "created_at": conv["created_at"].isoformat(),
                "updated_at": conv["updated_at"].isoformat()
            } for conv in conversations]
        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            return []
    
    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID and user ID"""
        try:
            conv = self.db.conversations.find_one({
                "_id": ObjectId(conversation_id),
                "user_id": user_id
            })
            
            if not conv:
                return None
            
            # Convert ObjectId to string
            conv["_id"] = str(conv["_id"])
            
            # Format dates
            conv["created_at"] = conv["created_at"].isoformat()
            conv["updated_at"] = conv["updated_at"].isoformat()
            
            # Format message timestamps
            for msg in conv["messages"]:
                if "timestamp" in msg:
                    msg["timestamp"] = msg["timestamp"].isoformat()
            
            return conv
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return None
    
    def add_messages(self, conversation_id: str, user_id: str, 
                    user_message: Dict[str, Any], assistant_response: Dict[str, Any]) -> bool:
        """Add a pair of messages to a conversation"""
        try:
            result = self.db.conversations.update_one(
                {
                    "_id": ObjectId(conversation_id),
                    "user_id": user_id
                },
                {
                    "$push": {
                        "messages": {
                            "$each": [user_message, assistant_response]
                        }
                    },
                    "$set": {
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding messages to conversation: {str(e)}")
            return False
    
    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation"""
        try:
            result = self.db.conversations.delete_one({
                "_id": ObjectId(conversation_id),
                "user_id": user_id
            })
            
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            return False