# User Registration System

A modern user registration system with beautiful frontend UI and RESTful API backend. **This project intentionally contains a simple bug for demonstration and learning purposes.**

## 🎯 Project Overview

This project demonstrates a typical user registration feature, including:
- 🎨 Modern responsive UI design (blue-white color scheme)
- 🔐 User input validation (frontend + backend dual validation)
- 💾 Simple JSON file data storage
- ⚠️ **Intentionally planted bug**: Email null value handling defect

## 📁 Project Structure

```
issue_project/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Flask app main file (contains bug)
│   ├── database.py          # User database operations
│   └── validators.py        # Input validation utilities
├── tests/
│   ├── __init__.py
│   └── test_registration.py # Test cases (2 will fail)
├── static/
│   ├── css/
│   │   └── style.css        # Stylesheet
│   └── js/
│       └── register.js      # Frontend interaction logic
├── templates/
│   └── register.html        # Registration page template
├── data/
│   └── users.json           # User data storage (generated at runtime)
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── KNOWN_ISSUE.md          # Detailed issue description
```

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Run Tests (View the Bug)

```powershell
python -m pytest tests/ -v
```

Or use unittest:

```powershell
python -m unittest tests.test_registration -v
```

**Expected Result**: 2 tests will fail (`test_missing_email_field` and `test_null_email_value`), exposing the bug.

### 3. Run Application

```powershell
python src/app.py
```

The application will start at http://localhost:5000

### 4. Test Registration Feature

Visit http://localhost:5000 and try:
- ✅ Normal registration: Fill in all fields
- ❌ Trigger bug: Use browser dev tools to modify the request, set email to null

## 🐛 Issue Description

### Issue Type
**Null Value Not Handled**

### Trigger Conditions
The API returns a 500 error when the `email` field in the request is:
1. Missing from JSON (`'email'` key missing)
2. Value is `null`

### Expected vs Actual Behavior

| Scenario | Expected Behavior | Actual Behavior |
|----------|------------------|-----------------|
| email field missing | Return 400, "Email cannot be empty" | Return 500, Internal Server Error |
| email = null | Return 400, "Email cannot be empty" | Return 500, AttributeError exception |
| email = "" | Return 400, "Email cannot be empty" | ✅ Handled correctly |

### Root Cause
**File**: `src/app.py`  
**Function**: `register()`  
**Line**: 47

```python
email = data.get('email')  # May return None
email_normalized = email.lower()  # 🐛 Raises AttributeError when email is None
```

### Technical Details
- `dict.get('key')` returns `None` when key doesn't exist
- Calling `.lower()` on `None` raises: `AttributeError: 'NoneType' object has no attribute 'lower'`
- Exception is caught and returns generic 500 error, poor user experience

## 🧪 Test Cases

Project contains 8 test cases:

✅ **Passing Tests** (6):
- `test_successful_registration` - Normal registration flow
- `test_uppercase_email_normalization` - Uppercase email to lowercase
- `test_empty_string_email` - Empty string email
- `test_duplicate_email` - Duplicate email detection
- `test_invalid_email_format` - Invalid email format
- `test_short_password` - Password length validation

❌ **Failing Tests** (2, exposing the bug):
- `test_missing_email_field` - Missing email field
- `test_null_email_value` - Email value is null

## 🎨 UI/UX Features

- ✨ Card-style design, centered layout
- 🌈 Soft blue-white color theme
- 🔄 Loading animations and interactive feedback
- ⚡ Real-time input validation
- 📱 Responsive design (mobile-friendly)
- ♿ Accessibility support

## 🔧 Tech Stack

- **Backend**: Python 3.8+, Flask 2.3+
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Storage**: JSON files
- **Testing**: unittest

## 📊 API Endpoints

### POST /api/register
Register a new user

**Request Body**:
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123"
}
```

**Success Response** (201):
```json
{
  "success": true,
  "message": "Registration successful!",
  "user": {
    "id": 1,
    "email": "test@example.com",
    "username": "testuser"
  }
}
```

**Error Response** (400/500):
```json
{
  "success": false,
  "error": "Error message"
}
```

## 🔍 Debugging Tips

For detailed issue analysis and fix approaches, see [KNOWN_ISSUE.md](KNOWN_ISSUE.md)

## ⚠️ Important Notes

1. **This is a demonstration project** with an intentionally planted bug
2. Passwords are stored in plaintext; use bcrypt or similar in production
3. Uses JSON file storage; use a database in production
4. No session management or authentication implemented
5. Missing CSRF protection

## 📝 License

MIT License - For learning and demonstration purposes only

---

**Created for Bug Demonstration & Learning Purposes** 🐛
