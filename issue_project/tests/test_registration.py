"""
Unit and Integration Tests for User Registration System
These tests are designed to expose the intentional bug in the system.
"""
import unittest
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app, db
from src.database import UserDatabase


class TestUserRegistration(unittest.TestCase):
    """Test cases for user registration endpoint"""
    
    def setUp(self):
        """Set up test client and database"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Use a test database
        db.db_file = 'data/test_users.json'
        db.clear()
    
    def tearDown(self):
        """Clean up after tests"""
        db.clear()
    
    def test_successful_registration(self):
        """Test successful user registration with valid data"""
        response = self.client.post('/api/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], 'test@example.com')
        self.assertEqual(data['user']['username'], 'testuser')
    
    def test_uppercase_email_normalization(self):
        """Test that emails with uppercase letters are normalized to lowercase"""
        response = self.client.post('/api/register',
            json={
                'username': 'alice',
                'email': 'Alice@Gmail.com',
                'password': 'secure123'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        # Email should be stored in lowercase
        self.assertEqual(data['user']['email'], 'alice@gmail.com')
    
    def test_missing_email_field(self):
        """
        🐛 BUG TEST: This test should FAIL
        When email field is missing from request, server returns 500 instead of 400
        """
        response = self.client.post('/api/register',
            json={
                'username': 'testuser',
                # email is missing intentionally
                'password': 'password123'
            },
            content_type='application/json'
        )
        
        # Expected: 400 Bad Request with helpful error message
        # Actual: 500 Internal Server Error due to AttributeError
        self.assertEqual(response.status_code, 400, 
            "Should return 400 for missing email, not 500")
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('邮箱', data['error'].lower())
    
    def test_null_email_value(self):
        """
        🐛 BUG TEST: This test should FAIL
        When email is explicitly null, server crashes with AttributeError
        """
        response = self.client.post('/api/register',
            json={
                'username': 'testuser',
                'email': None,  # Explicitly null
                'password': 'password123'
            },
            content_type='application/json'
        )
        
        # Expected: 400 Bad Request with validation error
        # Actual: 500 Internal Server Error (email.lower() fails on None)
        self.assertEqual(response.status_code, 400,
            "Should return 400 for null email, not 500")
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_empty_string_email(self):
        """Test registration with empty string email"""
        response = self.client.post('/api/register',
            json={
                'username': 'testuser',
                'email': '',
                'password': 'password123'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('邮箱', data['error'])
    
    def test_duplicate_email(self):
        """Test that duplicate emails are rejected"""
        # Register first user
        self.client.post('/api/register',
            json={
                'username': 'user1',
                'email': 'test@example.com',
                'password': 'password123'
            }
        )
        
        # Try to register with same email
        response = self.client.post('/api/register',
            json={
                'username': 'user2',
                'email': 'test@example.com',
                'password': 'password456'
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('已被注册', data['error'])
    
    def test_invalid_email_format(self):
        """Test that invalid email formats are rejected"""
        response = self.client.post('/api/register',
            json={
                'username': 'testuser',
                'email': 'not-an-email',
                'password': 'password123'
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_short_password(self):
        """Test that short passwords are rejected"""
        response = self.client.post('/api/register',
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': '123'
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('密码', data['error'])


class TestDatabaseOperations(unittest.TestCase):
    """Test cases for database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.db = UserDatabase('data/test_db.json')
        self.db.clear()
    
    def tearDown(self):
        """Clean up test database"""
        self.db.clear()
    
    def test_add_user(self):
        """Test adding a user to database"""
        user = self.db.add_user('test@example.com', 'password123', 'testuser')
        
        self.assertEqual(user['email'], 'test@example.com')
        self.assertEqual(user['username'], 'testuser')
        self.assertEqual(len(self.db.users), 1)
    
    def test_email_exists(self):
        """Test checking if email exists"""
        self.db.add_user('test@example.com', 'password123', 'testuser')
        
        self.assertTrue(self.db.email_exists('test@example.com'))
        self.assertFalse(self.db.email_exists('other@example.com'))
    
    def test_get_user_by_email(self):
        """Test retrieving user by email"""
        self.db.add_user('test@example.com', 'password123', 'testuser')
        
        user = self.db.get_user_by_email('test@example.com')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'testuser')
        
        user = self.db.get_user_by_email('nonexistent@example.com')
        self.assertIsNone(user)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
