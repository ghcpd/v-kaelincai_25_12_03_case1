"""
Database module for user storage
Uses in-memory storage for simplicity (can be replaced with real DB)
"""
import json
import os
from typing import Optional, Dict, List


class UserDatabase:
    """Simple in-memory user database with JSON persistence"""
    
    def __init__(self, db_file: str = "data/users.json"):
        self.db_file = db_file
        self.users: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load users from JSON file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.users = []
    
    def _save(self):
        """Save users to JSON file"""
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)
    
    def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return any(user['email'] == email for user in self.users)
    
    def add_user(self, email: str, password: str, username: str) -> Dict:
        """Add a new user to the database"""
        if self.email_exists(email):
            raise ValueError(f"Email {email} already exists")
        
        user = {
            'id': len(self.users) + 1,
            'email': email,
            'password': password,  # In production, this should be hashed!
            'username': username
        }
        self.users.append(user)
        self._save()
        return user
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        for user in self.users:
            if user['email'] == email:
                return user
        return None
    
    def clear(self):
        """Clear all users (for testing)"""
        self.users = []
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
