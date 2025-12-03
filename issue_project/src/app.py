"""
Flask application for user registration system
🐛 BUG: This file contains an intentional bug for demonstration
"""
from flask import Flask, request, jsonify, render_template
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import UserDatabase
from src.validators import validate_email, validate_password, validate_username

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# Initialize database
db = UserDatabase()


@app.route('/')
def index():
    """Render the registration page"""
    return render_template('register.html')


@app.route('/api/register', methods=['POST'])
def register():
    """
    User registration endpoint
    
    🐛 INTENTIONAL BUG LOCATION:
    When email is None or not provided in request JSON,
    the .lower() call will raise AttributeError
    """
    try:
        data = request.get_json()
        
        # Extract data from request
        email = data.get('email')
        password = data.get('password')
        username = data.get('username')
        
        # 🐛 BUG: Missing null check before calling .lower()
        # If email is None, this will raise: AttributeError: 'NoneType' object has no attribute 'lower'
        email_normalized = email.lower()  # Line 47 - BUG LOCATION
        
        # Validate inputs
        valid, error = validate_email(email_normalized)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400
        
        valid, error = validate_password(password)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400
        
        valid, error = validate_username(username)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400
        
        # Check if email already exists
        if db.email_exists(email_normalized):
            return jsonify({
                'success': False, 
                'error': '该邮箱已被注册'
            }), 400
        
        # Add user to database
        user = db.add_user(email_normalized, password, username)
        
        logger.info(f"User registered successfully: {email_normalized}")
        
        return jsonify({
            'success': True,
            'message': '注册成功！',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'username': user['username']
            }
        }), 201
        
    except AttributeError as e:
        # This catches the bug when email is None
        logger.error(f"AttributeError during registration: {e}")
        return jsonify({
            'success': False,
            'error': '注册失败，请稍后重试'
        }), 500
    
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        return jsonify({
            'success': False,
            'error': '注册失败，请稍后重试'
        }), 500


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (for testing purposes)"""
    return jsonify({'users': db.users}), 200


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
